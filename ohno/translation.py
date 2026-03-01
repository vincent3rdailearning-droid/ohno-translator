"""
translation.py — Claude API translation worker with debounce.

Public API:
    TranslationWorker(text, target_lang, tone)  — QThread that calls Claude API
    DebounceManager(delay_ms, parent)           — wraps QTimer + worker lifecycle
    _build_system_prompt(tone, target_lang)     — builds tone-aware system prompt
"""

from __future__ import annotations
import keyring
import anthropic
from PyQt6.QtCore import QThread, QTimer, QObject, pyqtSignal


def _build_system_prompt(tone: str, target_lang: str) -> str:
    """Build a tone-aware system prompt for the Claude translation request.

    Args:
        tone: One of "formal", "casual", or "literal". Unknown values fall back to "casual".
        target_lang: Full language name string (e.g. "English", "Japanese").

    Returns:
        A system prompt string with the target language substituted in.
    """
    if tone == "formal":
        return (
            f"You are a professional translator. Translate the following text into "
            f"{target_lang} using formal, polished language appropriate for business or "
            f"academic contexts. Return only the translated text."
        )
    elif tone == "literal":
        return (
            f"You are a translator. Provide a literal, word-for-word translation of the "
            f"following text into {target_lang}, preserving the original structure as "
            f"closely as possible. Return only the translated text."
        )
    else:
        # "casual" and any unknown tone fall back to casual
        return (
            f"You are a translator. Translate the following text into {target_lang} using "
            f"natural, conversational language as a native speaker would say it. Return "
            f"only the translated text."
        )


class TranslationWorker(QThread):
    """QThread subclass that calls the Claude API to translate text.

    Signals:
        translation_ready(str): Emitted with the translated text on success.
        error_occurred(str):    Emitted with a user-facing message on failure.
    """

    translation_ready = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self, text: str, target_lang: str, tone: str) -> None:
        """Initialise the worker.

        Args:
            text:        Source text to translate.
            target_lang: Full language name (e.g. "English", "Japanese").
            tone:        One of "formal", "casual", or "literal".
        """
        super().__init__()
        self.text = text
        self.target_lang = target_lang
        self.tone = tone
        self._cancelled = False

    def run(self) -> None:
        """Execute the translation request on the worker thread."""
        if not self.text.strip():
            return

        api_key = keyring.get_password("ohno", "api_key")
        if not api_key:
            self.error_occurred.emit("API key not set. Open Settings to add it.")
            return

        system_prompt = _build_system_prompt(self.tone, self.target_lang)

        try:
            client = anthropic.Anthropic(api_key=api_key)
            response = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=1024,
                system=system_prompt,
                messages=[{"role": "user", "content": self.text}],
            )

            if self._cancelled:
                return

            self.translation_ready.emit(response.content[0].text)

        except anthropic.AuthenticationError:
            self.error_occurred.emit("Invalid API key. Check Settings.")
        except anthropic.RateLimitError:
            self.error_occurred.emit("Rate limited. Please wait a moment.")
        except anthropic.APIConnectionError:
            self.error_occurred.emit("Connection timed out. Check internet.")
        except anthropic.APIStatusError as e:
            self.error_occurred.emit(f"Translation failed (error {e.status_code}).")
        except Exception as e:
            self.error_occurred.emit(f"Unexpected error: {e}")

    def cancel(self) -> None:
        """Signal the worker to discard its result when it completes."""
        self._cancelled = True


class DebounceManager(QObject):
    """Owns the debounce timer and TranslationWorker lifecycle.

    Call `request()` on every keystroke; after `delay_ms` milliseconds of
    silence a TranslationWorker is started. If a new request arrives before
    the timer fires, the timer resets. Any in-flight worker is cancelled
    before the new one starts.

    Signals:
        translation_ready(str): Forwarded from the active worker on success.
        error_occurred(str):    Forwarded from the active worker on failure.
        started():              Emitted when a new worker is about to start.
        cancelled():            Emitted when a pending request is superseded.
    """

    translation_ready = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    started = pyqtSignal()
    cancelled = pyqtSignal()

    def __init__(self, delay_ms: int = 500, parent: QObject | None = None) -> None:
        """Initialise the debounce manager.

        Args:
            delay_ms: Milliseconds of idle time before firing a translation request.
            parent:   Optional Qt parent object.
        """
        super().__init__(parent)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(delay_ms)
        self._timer.timeout.connect(self._on_timeout)
        self._pending_text: str = ""
        self._pending_target: str = "English"
        self._pending_tone: str = "formal"
        self._current_worker: TranslationWorker | None = None

    def request(self, text: str, target_lang: str, tone: str) -> None:
        """Schedule a translation request.

        Resets the debounce timer each time it is called. Call this on every
        keystroke or parameter change that should trigger re-translation.

        Args:
            text:        Source text to translate.
            target_lang: Full language name (e.g. "English", "Japanese").
            tone:        One of "formal", "casual", or "literal".
        """
        self._pending_text = text
        self._pending_target = target_lang
        self._pending_tone = tone
        self._timer.start()

    def _on_timeout(self) -> None:
        """Called when the debounce timer fires. Starts a new TranslationWorker."""
        # Cancel any in-flight worker
        if self._current_worker is not None and self._current_worker.isRunning():
            self._current_worker.cancel()
            self._current_worker.quit()
            self._current_worker.wait(200)

        self._current_worker = TranslationWorker(
            self._pending_text,
            self._pending_target,
            self._pending_tone,
        )
        self._current_worker.translation_ready.connect(self.translation_ready)
        self._current_worker.error_occurred.connect(self.error_occurred)
        self._current_worker.finished.connect(self._on_worker_finished)
        self.started.emit()
        self._current_worker.start()

    def _on_worker_finished(self) -> None:
        """Clean up after a worker thread completes."""
        self._current_worker = None

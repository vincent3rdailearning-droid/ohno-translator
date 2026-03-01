"""
translation.py — Google Translate worker with debounce.

Public API:
    TranslationWorker(text, target_lang, tone)  — QThread that calls Google Translate
    DebounceManager(delay_ms, parent)           — wraps QTimer + worker lifecycle
"""

from __future__ import annotations
from deep_translator import GoogleTranslator
from PyQt6.QtCore import QThread, QTimer, QObject, pyqtSignal

from languages import _NAME_TO_CODE


class TranslationWorker(QThread):
    """QThread subclass that calls Google Translate to translate text.

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
            tone:        One of "formal", "casual", or "literal" (ignored for Google Translate).
        """
        super().__init__()
        self.text = text
        self.target_lang = target_lang
        self.tone = tone  # accepted but ignored — Google Translate doesn't support tone
        self._cancelled = False

    def run(self) -> None:
        """Execute the translation request on the worker thread."""
        if not self.text.strip():
            return

        lang_code = _NAME_TO_CODE.get(self.target_lang)
        if not lang_code:
            self.error_occurred.emit(f"Unknown target language: {self.target_lang}")
            return

        try:
            result = GoogleTranslator(source="auto", target=lang_code).translate(self.text)

            if self._cancelled:
                return

            self.translation_ready.emit(result or "")

        except Exception as e:
            if not self._cancelled:
                self.error_occurred.emit(f"Translation failed: {e}")

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

        Resets the debounce timer each time it is called.
        """
        self._pending_text = text
        self._pending_target = target_lang
        self._pending_tone = tone
        self._timer.start()

    def _on_timeout(self) -> None:
        """Called when the debounce timer fires. Starts a new TranslationWorker."""
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

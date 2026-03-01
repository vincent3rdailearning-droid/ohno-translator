# word_lookup.py — Word lookup via Free Dictionary API with translation fallback.

from __future__ import annotations
import threading
import requests
import pyttsx3
from deep_translator import GoogleTranslator
from PyQt6.QtCore import QObject, QTimer, pyqtSignal, Qt
from PyQt6.QtGui import QCursor
from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
)


def _fetch_definition(word: str) -> dict | None:
    """Fetch definition from Free Dictionary API. Returns parsed dict or None."""
    try:
        resp = requests.get(
            f"https://api.dictionaryapi.dev/api/v2/entries/en/{word.lower().strip()}",
            timeout=5,
        )
        if resp.status_code != 200:
            return None
        data = resp.json()
        entry = data[0] if data else {}
        phonetic = entry.get("phonetic", "")
        definition = ""
        part_of_speech = ""
        for meaning in entry.get("meanings", []):
            part_of_speech = meaning.get("partOfSpeech", "")
            defs = meaning.get("definitions", [])
            if defs:
                definition = defs[0].get("definition", "")
                break
        return {
            "phonetic": phonetic or None,
            "definition": definition or None,
            "part_of_speech": part_of_speech or None,
        }
    except Exception:
        return None


def _do_lookup(word: str, source_lang_code: str) -> dict:
    """Run the full lookup (translate if needed + dictionary). Called in a thread."""
    result: dict = {
        "word": word,
        "source_lang": source_lang_code,
        "translation": None,
        "phonetic": None,
        "definition": None,
        "part_of_speech": None,
    }

    if source_lang_code == "en":
        defn = _fetch_definition(word)
        if defn:
            result.update(defn)
        else:
            result["definition"] = "No definition found."
    else:
        translation = None
        try:
            t = GoogleTranslator(
                source=source_lang_code, target="en"
            ).translate(word)
            if t and t.strip():
                translation = t.strip()
        except Exception:
            try:
                t = GoogleTranslator(
                    source="auto", target="en"
                ).translate(word)
                if t and t.strip():
                    translation = t.strip()
            except Exception:
                pass

        if translation:
            result["translation"] = translation

        english_word = translation or word
        defn = _fetch_definition(english_word)
        if defn:
            result.update(defn)
        else:
            result["definition"] = "No definition found."

    return result


class LookupSignals(QObject):
    """Qt signals bridge — safe to emit from any thread."""
    lookup_ready = pyqtSignal(dict)
    lookup_error = pyqtSignal(str)


class LookupManager(QObject):
    """Manages word lookups using plain daemon threads (no QThread GC issues)."""

    lookup_ready = pyqtSignal(dict)
    lookup_error = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._signals = LookupSignals()
        self._signals.lookup_ready.connect(self.lookup_ready)
        self._signals.lookup_error.connect(self.lookup_error)

    def lookup(self, word: str, lang_code: str) -> None:
        """Start a lookup in a background daemon thread."""
        t = threading.Thread(
            target=self._run, args=(word.strip(), lang_code), daemon=True
        )
        t.start()

    def _run(self, word: str, lang_code: str) -> None:
        try:
            result = _do_lookup(word, lang_code)
            self._signals.lookup_ready.emit(result)
        except Exception as e:
            self._signals.lookup_error.emit(str(e))


def _speak_word(word: str) -> None:
    """Pronounce a word using pyttsx3 in a background thread."""
    def _run():
        try:
            engine = pyttsx3.init()
            engine.say(word)
            engine.runAndWait()
            engine.stop()
        except Exception:
            pass
    threading.Thread(target=_run, daemon=True).start()


class LookupPopup(QFrame):
    """Small frameless popup that shows word definition near the cursor."""

    def __init__(self, info: dict, parent=None) -> None:
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFixedWidth(320)
        self.setObjectName("lookupPopup")
        self.setStyleSheet(
            "#lookupPopup {"
            "  background-color: #ffffff;"
            "  border: 1px solid #cbd5e1;"
            "  border-radius: 6px;"
            "}"
            "#lookupPopup QLabel { background: transparent; }"
            "#lookupPopup QPushButton {"
            "  background: transparent; border: none; font-size: 16px;"
            "}"
            "#lookupPopup QPushButton:hover {"
            "  background-color: #e2e8f0; border-radius: 4px;"
            "}"
        )

        self._word = info.get("word", "")
        self._translation = info.get("translation")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)

        # Top row: word (+ translation) + speaker button
        top_row = QHBoxLayout()
        top_row.setSpacing(6)

        word_text = self._word
        if self._translation:
            word_text += f"  \u2192  {self._translation}"
        word_label = QLabel(word_text)
        word_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #1f2937;")
        word_label.setWordWrap(True)
        top_row.addWidget(word_label, stretch=1)

        # Speaker button
        speak_btn = QPushButton("\U0001f50a")  # speaker emoji
        speak_btn.setFixedSize(28, 28)
        speak_btn.setToolTip("Pronounce")
        speak_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        pronounce_word = self._translation or self._word
        speak_btn.clicked.connect(lambda: _speak_word(pronounce_word))
        top_row.addWidget(speak_btn, stretch=0)

        layout.addLayout(top_row)

        # Phonetic
        if info.get("phonetic"):
            ph_label = QLabel(info["phonetic"])
            ph_label.setStyleSheet("font-size: 12px; color: #6b7280; font-style: italic;")
            layout.addWidget(ph_label)

        # Part of speech
        if info.get("part_of_speech"):
            pos_label = QLabel(info["part_of_speech"])
            pos_label.setStyleSheet("font-size: 11px; color: #3b82f6; font-weight: bold;")
            layout.addWidget(pos_label)

        # Definition
        definition = info.get("definition", "No definition found.")
        def_label = QLabel(definition)
        def_label.setStyleSheet("font-size: 12px; color: #374151;")
        def_label.setWordWrap(True)
        layout.addWidget(def_label)

        # Position near cursor
        cursor_pos = QCursor.pos()
        self.move(cursor_pos.x() + 10, cursor_pos.y() + 10)

        # Auto-dismiss after 8 seconds
        QTimer.singleShot(8000, self._safe_close)

    def _safe_close(self) -> None:
        if self.isVisible():
            self.close()

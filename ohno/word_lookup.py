# word_lookup.py — Word lookup via Free Dictionary API with translation fallback.

from __future__ import annotations
import requests
from deep_translator import GoogleTranslator
from PyQt6.QtCore import QThread, QTimer, pyqtSignal, Qt
from PyQt6.QtGui import QCursor
from PyQt6.QtWidgets import QFrame, QVBoxLayout, QLabel


class LookupWorker(QThread):
    """Background thread: look up a word's definition via Free Dictionary API.

    For non-English words, translates to English first via Google Translate,
    then looks up the English translation.
    """

    lookup_ready = pyqtSignal(dict)
    lookup_error = pyqtSignal(str)

    def __init__(self, word: str, source_lang_code: str) -> None:
        super().__init__()
        self.word = word.strip()
        self.source_lang_code = source_lang_code

    def run(self) -> None:
        try:
            english_word = self.word
            translation = None

            # Translate to English first if source isn't English
            if self.source_lang_code != "en":
                translation = GoogleTranslator(
                    source=self.source_lang_code, target="en"
                ).translate(self.word)
                if translation:
                    english_word = translation.strip()

            # Look up in Free Dictionary API
            resp = requests.get(
                f"https://api.dictionaryapi.dev/api/v2/entries/en/{english_word}",
                timeout=5,
            )

            if resp.status_code != 200:
                result = {
                    "word": self.word,
                    "translation": translation,
                    "phonetic": None,
                    "definition": "No definition found.",
                    "part_of_speech": None,
                }
                self.lookup_ready.emit(result)
                return

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

            self.lookup_ready.emit({
                "word": self.word,
                "translation": translation,
                "phonetic": phonetic or None,
                "definition": definition or "No definition found.",
                "part_of_speech": part_of_speech or None,
            })

        except Exception as e:
            self.lookup_error.emit(str(e))


class LookupPopup(QFrame):
    """Small frameless popup that shows word definition near the cursor."""

    def __init__(self, info: dict, parent=None) -> None:
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.Popup
        )
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setFixedWidth(300)
        self.setStyleSheet(
            "LookupPopup {"
            "  background-color: #ffffff;"
            "  border: 1px solid #cbd5e1;"
            "  border-radius: 6px;"
            "  padding: 8px;"
            "}"
            "QLabel { background: transparent; }"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)

        # Word (+ translation if non-English)
        word_text = info["word"]
        if info.get("translation"):
            word_text += f"  \u2192  {info['translation']}"
        word_label = QLabel(word_text)
        word_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #1f2937;")
        word_label.setWordWrap(True)
        layout.addWidget(word_label)

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
        def_label = QLabel(info.get("definition", ""))
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

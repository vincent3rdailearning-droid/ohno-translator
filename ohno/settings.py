# settings.py — Settings QDialog for configuring the translator.

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QComboBox, QLineEdit, QPushButton, QLabel,
)
from PyQt6.QtCore import Qt, pyqtSignal

from languages import LANG_NAMES, display_name_for_code
from config import save as save_config

TONES = [("formal", "Formal"), ("casual", "Casual"), ("literal", "Literal")]


class SettingsDialog(QDialog):
    """Modal settings dialog for the translator app."""

    settings_changed = pyqtSignal(dict)  # emitted with updated config on save

    def __init__(self, cfg: dict, parent=None) -> None:
        super().__init__(parent)
        self._cfg = dict(cfg)
        self.setWindowTitle("OHNO Settings")
        self.setFixedWidth(380)
        self.setWindowFlags(
            self.windowFlags()
            | Qt.WindowType.WindowStaysOnTopHint
        )

        self._apply_stylesheet()
        self._build_ui()

    def _apply_stylesheet(self) -> None:
        self.setStyleSheet("""
            QDialog {
                background-color: #f0f4f8;
                color: #1f2937;
                font-family: system-ui, sans-serif;
            }
            QLabel {
                font-size: 13px;
                color: #374151;
            }
            QComboBox, QLineEdit {
                border: 1px solid #cbd5e1;
                border-radius: 4px;
                padding: 5px 8px;
                background-color: white;
                color: #1f2937;
                font-size: 13px;
                min-height: 24px;
            }
            QComboBox:hover, QLineEdit:hover {
                border-color: #94a3b8;
            }
            QComboBox:focus, QLineEdit:focus {
                border-color: #60a5fa;
            }
            QComboBox::drop-down {
                border: none;
            }
            #saveBtn {
                background-color: #3b82f6;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 20px;
                font-size: 13px;
                font-weight: bold;
            }
            #saveBtn:hover {
                background-color: #2563eb;
            }
            #cancelBtn {
                background-color: white;
                color: #374151;
                border: 1px solid #cbd5e1;
                border-radius: 4px;
                padding: 6px 20px;
                font-size: 13px;
            }
            #cancelBtn:hover {
                background-color: #e2e8f0;
                border-color: #94a3b8;
            }
            #sectionLabel {
                font-size: 14px;
                font-weight: bold;
                color: #1f2937;
                padding-top: 8px;
            }
        """)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # -- Language section --
        lang_label = QLabel("Language")
        lang_label.setObjectName("sectionLabel")
        layout.addWidget(lang_label)

        lang_form = QFormLayout()
        lang_form.setSpacing(8)

        self._source_combo = QComboBox()
        self._source_combo.addItems(LANG_NAMES)
        src_name = display_name_for_code(self._cfg.get("default_source_lang", "zh-TW"))
        idx = self._source_combo.findText(src_name)
        if idx >= 0:
            self._source_combo.setCurrentIndex(idx)
        lang_form.addRow("Source:", self._source_combo)

        self._target_combo = QComboBox()
        self._target_combo.addItems(LANG_NAMES)
        tgt_name = display_name_for_code(self._cfg.get("default_target_lang", "en"))
        idx = self._target_combo.findText(tgt_name)
        if idx >= 0:
            self._target_combo.setCurrentIndex(idx)
        lang_form.addRow("Target:", self._target_combo)

        layout.addLayout(lang_form)

        # -- Tone section --
        tone_label = QLabel("Tone")
        tone_label.setObjectName("sectionLabel")
        layout.addWidget(tone_label)

        tone_form = QFormLayout()
        tone_form.setSpacing(8)

        self._tone_combo = QComboBox()
        current_tone = self._cfg.get("default_tone", "formal")
        for value, display in TONES:
            self._tone_combo.addItem(display, value)
        for i in range(self._tone_combo.count()):
            if self._tone_combo.itemData(i) == current_tone:
                self._tone_combo.setCurrentIndex(i)
                break
        tone_form.addRow("Default:", self._tone_combo)

        layout.addLayout(tone_form)

        # -- Hotkeys section --
        hotkey_label = QLabel("Hotkeys")
        hotkey_label.setObjectName("sectionLabel")
        layout.addWidget(hotkey_label)

        hotkey_form = QFormLayout()
        hotkey_form.setSpacing(8)

        self._hotkey_edit = QLineEdit(self._cfg.get("hotkey", "ctrl+shift+t"))
        self._hotkey_edit.setPlaceholderText("e.g. ctrl+shift+t")
        hotkey_form.addRow("Toggle:", self._hotkey_edit)

        self._clip_hotkey_edit = QLineEdit(self._cfg.get("clipboard_hotkey", "ctrl+shift+v"))
        self._clip_hotkey_edit.setPlaceholderText("e.g. ctrl+shift+v")
        hotkey_form.addRow("Clipboard:", self._clip_hotkey_edit)

        layout.addLayout(hotkey_form)

        # -- Note about hotkeys --
        note = QLabel("Hotkey changes take effect after restarting the app.")
        note.setStyleSheet("font-size: 11px; color: #6b7280; font-style: italic;")
        note.setWordWrap(True)
        layout.addWidget(note)

        layout.addStretch()

        # -- Buttons --
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("cancelBtn")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        save_btn = QPushButton("Save")
        save_btn.setObjectName("saveBtn")
        save_btn.clicked.connect(self._on_save)
        btn_row.addWidget(save_btn)

        layout.addLayout(btn_row)

    def _on_save(self) -> None:
        """Collect values, save to disk, emit signal, and close."""
        from languages import _NAME_TO_CODE

        src_name = self._source_combo.currentText()
        tgt_name = self._target_combo.currentText()

        self._cfg["default_source_lang"] = _NAME_TO_CODE.get(src_name, "zh-TW")
        self._cfg["default_target_lang"] = _NAME_TO_CODE.get(tgt_name, "en")
        self._cfg["default_tone"] = self._tone_combo.currentData()
        self._cfg["hotkey"] = self._hotkey_edit.text().strip() or "ctrl+shift+t"
        self._cfg["clipboard_hotkey"] = self._clip_hotkey_edit.text().strip() or "ctrl+shift+v"

        save_config(self._cfg)
        self.settings_changed.emit(self._cfg)
        self.accept()

# window.py — Frameless popup QWidget with full translation UI.

from PyQt6.QtWidgets import (
    QWidget, QApplication, QVBoxLayout, QHBoxLayout, QTextEdit,
    QLabel, QComboBox, QPushButton, QMenu,
    QSplitter, QSizePolicy, QSizeGrip,
)
from PyQt6.QtCore import Qt, QPoint, QEvent, QTimer, pyqtSignal
from PyQt6.QtGui import QKeyEvent, QMouseEvent

from translation import DebounceManager
from clipboard import set_clipboard_text
from config import load_history, save_history
from languages import LANG_NAMES, display_name_for_code, _NAME_TO_CODE
from word_lookup import LookupManager, LookupPopup
from settings import SettingsDialog

# ---------------------------------------------------------------------------
# Custom text edit with selection detection
# ---------------------------------------------------------------------------

class _SelectableTextEdit(QTextEdit):
    """QTextEdit that emits a signal when text is selected (1-3 words or up to 40 chars)."""

    text_selected = pyqtSignal(str, str)  # (selected_text, lang_code)

    def __init__(self, lang_code_fn, parent=None):
        super().__init__(parent)
        self._lang_code_fn = lang_code_fn
        self.selectionChanged.connect(self._on_selection_changed)
        self._sel_timer = QTimer(self)
        self._sel_timer.setSingleShot(True)
        self._sel_timer.setInterval(200)
        self._sel_timer.timeout.connect(self._emit_if_selected)

    def _on_selection_changed(self) -> None:
        self._sel_timer.start()

    def _emit_if_selected(self) -> None:
        selected = self.textCursor().selectedText().strip()
        if not selected:
            return
        # Allow 1-3 space-separated words OR up to 40 characters (for CJK)
        word_count = len(selected.split())
        if word_count <= 3 and len(selected) <= 40:
            lang_code = self._lang_code_fn()
            self.text_selected.emit(selected, lang_code)


# ---------------------------------------------------------------------------
# Custom title bar (draggable, with pin/minimize/settings/close)
# ---------------------------------------------------------------------------

class _TitleBar(QWidget):
    """Custom title bar widget that handles drag and window controls."""

    def __init__(self, parent_window: "TranslatorWindow") -> None:
        super().__init__(parent_window)
        self._parent_window = parent_window
        self._drag_pos: QPoint | None = None
        self._pinned = True  # starts always-on-top

        self.setFixedHeight(32)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setObjectName("titleBar")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 0, 4, 0)
        layout.setSpacing(4)

        # App label (doubles as drag handle)
        title = QLabel("OHNO")
        title.setObjectName("titleLabel")
        title.setStyleSheet("font-weight: bold; font-size: 13px; color: #374151;")
        layout.addWidget(title)

        layout.addStretch()

        # Pin toggle
        self._pin_btn = QPushButton("\U0001f4cc")  # pin emoji
        self._pin_btn.setObjectName("titleBtn")
        self._pin_btn.setFixedSize(26, 26)
        self._pin_btn.setToolTip("Unpin (disable always-on-top)")
        self._pin_btn.clicked.connect(self._toggle_pin)
        layout.addWidget(self._pin_btn)

        # Minimize button
        minimize_btn = QPushButton("\u2581")  # ▁
        minimize_btn.setObjectName("titleBtn")
        minimize_btn.setFixedSize(26, 26)
        minimize_btn.setToolTip("Minimize")
        minimize_btn.clicked.connect(self._parent_window.showMinimized)
        layout.addWidget(minimize_btn)

        # Settings gear
        settings_btn = QPushButton("\u2699")
        settings_btn.setObjectName("titleBtn")
        settings_btn.setFixedSize(26, 26)
        settings_btn.setToolTip("Settings")
        settings_btn.clicked.connect(self._parent_window.open_settings)
        layout.addWidget(settings_btn)

        # Close button
        close_btn = QPushButton("\u2715")
        close_btn.setObjectName("closeTitleBtn")
        close_btn.setFixedSize(26, 26)
        close_btn.setToolTip("Close")
        close_btn.clicked.connect(self._parent_window.hide)
        layout.addWidget(close_btn)

    def _toggle_pin(self) -> None:
        self._pinned = not self._pinned
        flags = self._parent_window.windowFlags()
        if self._pinned:
            flags |= Qt.WindowType.WindowStaysOnTopHint
            self._pin_btn.setToolTip("Unpin (disable always-on-top)")
        else:
            flags &= ~Qt.WindowType.WindowStaysOnTopHint
            self._pin_btn.setToolTip("Pin (enable always-on-top)")
        was_visible = self._parent_window.isVisible()
        self._parent_window.setWindowFlags(flags)
        if was_visible:
            self._parent_window.show()

    # -- Drag support (title bar only) --

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self._parent_window.frameGeometry().topLeft()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._drag_pos is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self._parent_window.move(event.globalPosition().toPoint() - self._drag_pos)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._drag_pos = None
        super().mouseReleaseEvent(event)


# ---------------------------------------------------------------------------
# Main translator window
# ---------------------------------------------------------------------------

class TranslatorWindow(QWidget):
    """Main translator popup — frameless, draggable, always-on-top."""

    def __init__(self, cfg: dict | None = None, parent=None):
        super().__init__(parent)
        self._cfg = cfg or {}
        self._debounce = DebounceManager(delay_ms=500, parent=self)
        self._lookup_popup: LookupPopup | None = None
        self._lookup_mgr = LookupManager(parent=self)
        self._lookup_mgr.lookup_ready.connect(self._on_lookup_ready)
        self._lookup_mgr.lookup_error.connect(self._on_lookup_error)
        self._showing_popup = False
        self._first_show = True
        self._history: list[dict] = load_history()
        self._setup_window()
        self._setup_translation()

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------

    def _setup_window(self) -> None:
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setMinimumSize(400, 350)
        self.resize(480, 520)
        self.setWindowTitle("OHNO Translator")

        self._apply_stylesheet()

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # -- Title bar --
        self._title_bar = _TitleBar(self)
        root.addWidget(self._title_bar)

        # -- Content area --
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(12, 8, 12, 12)
        content_layout.setSpacing(8)

        # Source panel (dropdown + textarea)
        source_panel = QWidget()
        source_layout = QVBoxLayout(source_panel)
        source_layout.setContentsMargins(0, 0, 0, 0)
        source_layout.setSpacing(4)

        self._source_combo = QComboBox()
        self._source_combo.addItems(LANG_NAMES)
        default_src = display_name_for_code(self._cfg.get("default_source_lang", "zh-TW"))
        idx = self._source_combo.findText(default_src)
        if idx >= 0:
            self._source_combo.setCurrentIndex(idx)
        source_layout.addWidget(self._source_combo)

        self._source = _SelectableTextEdit(self._get_source_lang_code)
        self._source.setPlaceholderText("Type or paste text to translate...")
        self._source.setMinimumHeight(80)
        source_layout.addWidget(self._source)

        # Middle controls row: swap button only (tone removed)
        controls_row = QWidget()
        controls_layout = QHBoxLayout(controls_row)
        controls_layout.setContentsMargins(0, 2, 0, 2)
        controls_layout.setSpacing(8)

        controls_layout.addStretch()

        # Swap button
        swap_btn = QPushButton("\u21c4")
        swap_btn.setToolTip("Swap languages and text")
        swap_btn.setFixedSize(32, 28)
        swap_btn.setObjectName("swapBtn")
        swap_btn.clicked.connect(self._on_swap)
        controls_layout.addWidget(swap_btn)

        # Status label (translating...)
        self._status_label = QLabel("Translating\u2026")
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status_label.setStyleSheet("color: #6b7280; font-size: 12px;")
        self._status_label.setVisible(False)

        # Error banner
        self._error_label = QLabel("")
        self._error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._error_label.setWordWrap(True)
        self._error_label.setStyleSheet(
            "background-color: #fee2e2; color: #991b1b; "
            "border-radius: 4px; padding: 6px; font-size: 12px;"
        )
        self._error_label.setVisible(False)

        # Target panel (dropdown + textarea)
        target_panel = QWidget()
        target_layout = QVBoxLayout(target_panel)
        target_layout.setContentsMargins(0, 0, 0, 0)
        target_layout.setSpacing(4)

        self._target_combo = QComboBox()
        self._target_combo.addItems(LANG_NAMES)
        default_tgt = display_name_for_code(self._cfg.get("default_target_lang", "en"))
        idx = self._target_combo.findText(default_tgt)
        if idx >= 0:
            self._target_combo.setCurrentIndex(idx)
        target_layout.addWidget(self._target_combo)

        self._output = _SelectableTextEdit(self._get_target_lang_code)
        self._output.setPlaceholderText("Translation will appear here\u2026")
        self._output.setReadOnly(True)
        self._output.setMinimumHeight(80)
        target_layout.addWidget(self._output)

        # QSplitter between source and target panels
        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.addWidget(source_panel)
        splitter.addWidget(target_panel)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        splitter.setChildrenCollapsible(False)

        content_layout.addWidget(splitter, stretch=1)
        content_layout.addWidget(controls_row)
        content_layout.addWidget(self._status_label)
        content_layout.addWidget(self._error_label)

        # Bottom buttons row: Copy + Clear
        bottom_row = QWidget()
        bottom_layout = QHBoxLayout(bottom_row)
        bottom_layout.setContentsMargins(0, 4, 0, 0)
        bottom_layout.setSpacing(8)

        history_btn = QPushButton("History")
        history_btn.setObjectName("actionBtn")
        history_btn.setToolTip("Translation history")
        history_btn.clicked.connect(self._on_show_history)
        bottom_layout.addWidget(history_btn)

        bottom_layout.addStretch()

        clear_btn = QPushButton("Clear")
        clear_btn.setObjectName("actionBtn")
        clear_btn.setToolTip("Clear both text areas")
        clear_btn.clicked.connect(self._on_clear)
        bottom_layout.addWidget(clear_btn)

        copy_btn = QPushButton("Copy")
        copy_btn.setObjectName("actionBtn")
        copy_btn.setToolTip("Copy translation to clipboard")
        copy_btn.clicked.connect(self._on_copy)
        bottom_layout.addWidget(copy_btn)

        content_layout.addWidget(bottom_row)

        root.addWidget(content, stretch=1)

        # -- Size grips for resizing (both bottom corners) --
        grip_row = QHBoxLayout()
        grip_row.setContentsMargins(0, 0, 0, 0)
        grip_left = QSizeGrip(self)
        grip_left.setFixedSize(16, 16)
        grip_row.addWidget(grip_left)
        grip_row.addStretch()
        grip_right = QSizeGrip(self)
        grip_right.setFixedSize(16, 16)
        grip_row.addWidget(grip_right)
        root.addLayout(grip_row)

    def _apply_stylesheet(self) -> None:
        self.setStyleSheet("""
            QWidget {
                background-color: #f0f4f8;
                color: #1f2937;
                font-family: system-ui, sans-serif;
            }
            #titleBar {
                background-color: #e2e8f0;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
            }
            #titleBtn {
                background: transparent;
                border: none;
                font-size: 14px;
                border-radius: 4px;
            }
            #titleBtn:hover {
                background-color: #cbd5e1;
            }
            #closeTitleBtn {
                background: transparent;
                border: none;
                font-size: 14px;
                border-radius: 4px;
            }
            #closeTitleBtn:hover {
                background-color: #fca5a5;
                color: #991b1b;
            }
            QComboBox {
                border: 1px solid #cbd5e1;
                border-radius: 4px;
                padding: 4px 8px;
                background-color: white;
                color: #1f2937;
                font-size: 13px;
            }
            QComboBox:hover {
                border-color: #94a3b8;
            }
            QComboBox::drop-down {
                border: none;
            }
            QTextEdit {
                border: 1px solid #cbd5e1;
                border-radius: 6px;
                padding: 6px;
                background-color: white;
                color: #1f2937;
                font-size: 14px;
            }
            QTextEdit:focus {
                border-color: #60a5fa;
            }
            #swapBtn {
                border: 1px solid #cbd5e1;
                border-radius: 4px;
                background-color: white;
                font-size: 16px;
                font-weight: bold;
            }
            #swapBtn:hover {
                background-color: #e2e8f0;
                border-color: #94a3b8;
            }
            #actionBtn {
                border: 1px solid #cbd5e1;
                border-radius: 4px;
                background-color: white;
                padding: 4px 16px;
                font-size: 13px;
            }
            #actionBtn:hover {
                background-color: #e2e8f0;
                border-color: #94a3b8;
            }
            QSizeGrip {
                background: transparent;
            }
        """)

    def _setup_translation(self) -> None:
        self._source.textChanged.connect(self._on_source_changed)
        self._source_combo.currentIndexChanged.connect(self._on_control_changed)
        self._target_combo.currentIndexChanged.connect(self._on_control_changed)
        self._debounce.started.connect(self._on_translation_started)
        self._debounce.translation_ready.connect(self._on_translation_ready)
        self._debounce.error_occurred.connect(self._on_error)

        # Word lookup signals
        self._source.text_selected.connect(self._on_text_selected)
        self._output.text_selected.connect(self._on_text_selected)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_source_lang_code(self) -> str:
        name = self._source_combo.currentText()
        return _NAME_TO_CODE.get(name, "en")

    def _get_target_lang_code(self) -> str:
        name = self._target_combo.currentText()
        return _NAME_TO_CODE.get(name, "en")

    def _trigger_translation(self) -> None:
        text = self._source.toPlainText()
        if not text.strip():
            return
        target_name = self._target_combo.currentText()
        tone = self._cfg.get("default_tone", "casual")
        self._debounce.request(text, target_lang=target_name, tone=tone)

    # ------------------------------------------------------------------
    # Translation slots
    # ------------------------------------------------------------------

    def _on_source_changed(self) -> None:
        text = self._source.toPlainText()
        if not text.strip():
            self._output.clear()
            self._error_label.setVisible(False)
            self._status_label.setVisible(False)
            return
        self._trigger_translation()

    def _on_control_changed(self) -> None:
        """Re-trigger translation when language changes."""
        self._trigger_translation()

    def _on_translation_started(self) -> None:
        self._error_label.setVisible(False)
        self._status_label.setVisible(True)

    def _on_translation_ready(self, text: str) -> None:
        self._status_label.setVisible(False)
        self._output.setPlainText(text)
        self._auto_save_history()

    def _on_error(self, message: str) -> None:
        self._status_label.setVisible(False)
        self._error_label.setText(message)
        self._error_label.setVisible(True)

    # ------------------------------------------------------------------
    # Word lookup
    # ------------------------------------------------------------------

    def _on_text_selected(self, word: str, lang_code: str) -> None:
        """Handle text selection — start a word lookup."""
        # Dismiss any existing popup
        if self._lookup_popup is not None:
            self._lookup_popup.close()
            self._lookup_popup = None

        self._lookup_mgr.lookup(word, lang_code)

    def _on_lookup_ready(self, info: dict) -> None:
        if self._lookup_popup is not None:
            self._lookup_popup.close()
            self._lookup_popup = None
        self._showing_popup = True
        self._lookup_popup = LookupPopup(info)
        self._lookup_popup.show()
        # Re-activate main window so it doesn't lose focus
        self.activateWindow()
        self._showing_popup = False

    def _on_lookup_error(self, message: str) -> None:
        # Silently ignore lookup errors — not critical
        pass

    # ------------------------------------------------------------------
    # Button actions
    # ------------------------------------------------------------------

    def _on_swap(self) -> None:
        """Swap source/target dropdowns and text content."""
        src_idx = self._source_combo.currentIndex()
        tgt_idx = self._target_combo.currentIndex()

        # Block signals to avoid double-triggering translation
        self._source_combo.blockSignals(True)
        self._target_combo.blockSignals(True)
        self._source.blockSignals(True)

        self._source_combo.setCurrentIndex(tgt_idx)
        self._target_combo.setCurrentIndex(src_idx)

        src_text = self._source.toPlainText()
        out_text = self._output.toPlainText()
        self._source.setPlainText(out_text)
        self._output.setPlainText(src_text)

        self._source_combo.blockSignals(False)
        self._target_combo.blockSignals(False)
        self._source.blockSignals(False)

        # Now trigger translation once with the new state
        self._trigger_translation()

    def _on_copy(self) -> None:
        text = self._output.toPlainText()
        if text.strip():
            set_clipboard_text(text)

    def _on_clear(self) -> None:
        self._auto_save_history()
        self._source.clear()
        self._output.clear()

    # ------------------------------------------------------------------
    # History
    # ------------------------------------------------------------------

    def _auto_save_history(self) -> None:
        """Auto-save the current translation pair to history."""
        source_text = self._source.toPlainText().strip()
        target_text = self._output.toPlainText().strip()
        if not source_text or not target_text:
            return

        entry = {
            "source": source_text,
            "target": target_text,
            "src_lang": self._source_combo.currentText(),
            "tgt_lang": self._target_combo.currentText(),
        }

        # Avoid duplicates (same source text)
        self._history = [h for h in self._history if h["source"] != source_text]
        self._history.insert(0, entry)
        self._history = self._history[:10]
        save_history(self._history)

    def _on_show_history(self) -> None:
        """Show a menu of past translations."""
        if not self._history:
            self._status_label.setText("No saved history yet")
            self._status_label.setVisible(True)
            QTimer.singleShot(1500, lambda: self._status_label.setVisible(False))
            return

        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #ffffff;
                border: 1px solid #cbd5e1;
                border-radius: 4px;
                padding: 4px;
                font-size: 13px;
            }
            QMenu::item {
                padding: 6px 12px;
                border-radius: 3px;
            }
            QMenu::item:selected {
                background-color: #e2e8f0;
            }
        """)

        for i, entry in enumerate(self._history):
            # Truncate long text for menu display
            src_preview = entry["source"][:30]
            if len(entry["source"]) > 30:
                src_preview += "\u2026"
            tgt_preview = entry["target"][:30]
            if len(entry["target"]) > 30:
                tgt_preview += "\u2026"
            label = f"{src_preview}  \u2192  {tgt_preview}"
            action = menu.addAction(label)
            action.triggered.connect(lambda checked, e=entry: self._load_history(e))

        # Show menu above the history button
        menu.exec(self.mapToGlobal(QPoint(12, self.height() - 60)))

    def _load_history(self, entry: dict) -> None:
        """Load a history entry back into the text areas."""
        self._source_combo.blockSignals(True)
        self._target_combo.blockSignals(True)
        self._source.blockSignals(True)

        idx = self._source_combo.findText(entry["src_lang"])
        if idx >= 0:
            self._source_combo.setCurrentIndex(idx)
        idx = self._target_combo.findText(entry["tgt_lang"])
        if idx >= 0:
            self._target_combo.setCurrentIndex(idx)

        self._source.setPlainText(entry["source"])
        self._output.setPlainText(entry["target"])

        self._source_combo.blockSignals(False)
        self._target_combo.blockSignals(False)
        self._source.blockSignals(False)

    # ------------------------------------------------------------------
    # Settings
    # ------------------------------------------------------------------

    def open_settings(self) -> None:
        """Open the settings dialog."""
        dlg = SettingsDialog(self._cfg, parent=self)
        dlg.settings_changed.connect(self._apply_settings)
        dlg.exec()

    def _apply_settings(self, new_cfg: dict) -> None:
        """Apply settings from the dialog without restarting."""
        self._cfg = new_cfg

        # Update language dropdowns
        src_name = display_name_for_code(new_cfg.get("default_source_lang", "zh-TW"))
        tgt_name = display_name_for_code(new_cfg.get("default_target_lang", "en"))

        self._source_combo.blockSignals(True)
        self._target_combo.blockSignals(True)

        idx = self._source_combo.findText(src_name)
        if idx >= 0:
            self._source_combo.setCurrentIndex(idx)
        idx = self._target_combo.findText(tgt_name)
        if idx >= 0:
            self._target_combo.setCurrentIndex(idx)

        self._source_combo.blockSignals(False)
        self._target_combo.blockSignals(False)

        # Re-trigger translation with new settings if there's text
        if self._source.toPlainText().strip():
            self._trigger_translation()

    # ------------------------------------------------------------------
    # Toggle visibility (called by hotkey)
    # ------------------------------------------------------------------

    def toggle(self) -> None:
        if self.isVisible():
            self.hide()
        else:
            if self._first_show:
                self._center_on_screen()
                self._first_show = False
            self.show()
            self.activateWindow()
            self.raise_()

    def _center_on_screen(self) -> None:
        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            self.move(
                geo.center().x() - self.width() // 2,
                geo.center().y() - self.height() // 2,
            )

    # ------------------------------------------------------------------
    # Keyboard: Escape to dismiss
    # ------------------------------------------------------------------

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.hide()
        else:
            super().keyPressEvent(event)

    # ------------------------------------------------------------------
    # Click-outside to dismiss (respects pin)
    # ------------------------------------------------------------------

    def changeEvent(self, event) -> None:
        if event.type() == QEvent.Type.WindowDeactivate:
            # Don't hide while showing a lookup popup or when pinned
            if not self._title_bar._pinned and not getattr(self, '_showing_popup', False):
                # Check if a lookup popup is currently visible
                if self._lookup_popup is not None and self._lookup_popup.isVisible():
                    return
                self.hide()
        super().changeEvent(event)

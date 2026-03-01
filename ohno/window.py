# window.py — Frameless popup QWidget with full translation UI.

from PyQt6.QtWidgets import (
    QWidget, QApplication, QVBoxLayout, QHBoxLayout, QTextEdit,
    QLabel, QComboBox, QPushButton, QRadioButton, QButtonGroup,
    QSplitter, QSizePolicy,
)
from PyQt6.QtCore import Qt, QPoint, QEvent
from PyQt6.QtGui import QKeyEvent, QMouseEvent

from translation import DebounceManager
from clipboard import set_clipboard_text
from languages import LANG_NAMES, display_name_for_code


# ---------------------------------------------------------------------------
# Custom title bar (draggable, with pin/settings/close)
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
        self._pin_btn.setToolTip("Toggle always-on-top")
        self._pin_btn.clicked.connect(self._toggle_pin)
        layout.addWidget(self._pin_btn)

        # Settings gear (placeholder)
        settings_btn = QPushButton("\u2699")
        settings_btn.setObjectName("titleBtn")
        settings_btn.setFixedSize(26, 26)
        settings_btn.setToolTip("Settings (coming soon)")
        settings_btn.setEnabled(False)
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

        self._source = QTextEdit()
        self._source.setPlaceholderText("Type or paste text to translate...")
        self._source.setMinimumHeight(80)
        source_layout.addWidget(self._source)

        # Middle controls row: tone selector + swap button
        controls_row = QWidget()
        controls_layout = QHBoxLayout(controls_row)
        controls_layout.setContentsMargins(0, 2, 0, 2)
        controls_layout.setSpacing(8)

        # Tone radio buttons
        tone_label = QLabel("Tone:")
        tone_label.setStyleSheet("font-size: 12px; color: #6b7280;")
        controls_layout.addWidget(tone_label)

        self._tone_group = QButtonGroup(self)
        default_tone = self._cfg.get("default_tone", "formal")
        for tone_value, tone_text in [("formal", "Formal"), ("casual", "Casual"), ("literal", "Literal")]:
            rb = QRadioButton(tone_text)
            rb.setProperty("tone_value", tone_value)
            if tone_value == default_tone:
                rb.setChecked(True)
            self._tone_group.addButton(rb)
            controls_layout.addWidget(rb)

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

        self._output = QTextEdit()
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
            QRadioButton {
                font-size: 12px;
                spacing: 4px;
                background: transparent;
            }
            QRadioButton::indicator {
                width: 14px;
                height: 14px;
                border: 2px solid #94a3b8;
                background: white;
                border-radius: 7px;
            }
            QRadioButton::indicator:checked {
                border: 2px solid #3b82f6;
                background: #3b82f6;
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
        """)

    def _setup_translation(self) -> None:
        self._source.textChanged.connect(self._on_source_changed)
        self._source_combo.currentIndexChanged.connect(self._on_control_changed)
        self._target_combo.currentIndexChanged.connect(self._on_control_changed)
        self._tone_group.buttonClicked.connect(lambda _btn: self._on_control_changed())
        self._debounce.started.connect(self._on_translation_started)
        self._debounce.translation_ready.connect(self._on_translation_ready)
        self._debounce.error_occurred.connect(self._on_error)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_selected_tone(self) -> str:
        checked = self._tone_group.checkedButton()
        if checked:
            return checked.property("tone_value")
        return "formal"

    def _trigger_translation(self) -> None:
        text = self._source.toPlainText()
        if not text.strip():
            return
        target_name = self._target_combo.currentText()
        tone = self._get_selected_tone()
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
        """Re-trigger translation when language or tone changes."""
        self._trigger_translation()

    def _on_translation_started(self) -> None:
        self._error_label.setVisible(False)
        self._status_label.setVisible(True)

    def _on_translation_ready(self, text: str) -> None:
        self._status_label.setVisible(False)
        self._output.setPlainText(text)

    def _on_error(self, message: str) -> None:
        self._status_label.setVisible(False)
        self._error_label.setText(message)
        self._error_label.setVisible(True)

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
        self._source.clear()
        self._output.clear()

    # ------------------------------------------------------------------
    # Toggle visibility (called by hotkey)
    # ------------------------------------------------------------------

    def toggle(self) -> None:
        if self.isVisible():
            self.hide()
        else:
            self._center_on_screen()
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
    # Click-outside to dismiss
    # ------------------------------------------------------------------

    def changeEvent(self, event) -> None:
        if event.type() == QEvent.Type.WindowDeactivate:
            self.hide()
        super().changeEvent(event)

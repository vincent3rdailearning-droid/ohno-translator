# window.py — Frameless popup QWidget with drag support, translation panel, and error banner.

from PyQt6.QtWidgets import QWidget, QApplication, QVBoxLayout, QTextEdit, QLabel
from PyQt6.QtCore import Qt, QPoint, QEvent
from PyQt6.QtGui import QKeyEvent

from translation import DebounceManager


class TranslatorWindow(QWidget):
    """Main translator popup — frameless, draggable, always-on-top."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._drag_pos: QPoint | None = None
        self._debounce = DebounceManager(delay_ms=500, parent=self)
        self._setup_window()
        self._setup_translation()

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------

    def _setup_window(self) -> None:
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool  # Keeps it off the taskbar
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setMinimumSize(400, 350)
        self.resize(480, 420)
        self.setWindowTitle("OHNO Translator")

        self.setStyleSheet("QWidget { background-color: #f0f4f8; border-radius: 8px; }")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # Source text area
        self._source = QTextEdit()
        self._source.setPlaceholderText("Type or paste text to translate...")
        self._source.setMinimumHeight(120)
        layout.addWidget(self._source)

        # Loading status label (shown while API call is in-flight)
        self._status_label = QLabel("Translating\u2026")
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status_label.setStyleSheet("color: #6b7280; font-size: 12px;")
        self._status_label.setVisible(False)
        layout.addWidget(self._status_label)

        # Error banner (dismissible via new request)
        self._error_label = QLabel("")
        self._error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._error_label.setWordWrap(True)
        self._error_label.setStyleSheet(
            "background-color: #fee2e2; color: #991b1b; "
            "border-radius: 4px; padding: 6px; font-size: 12px;"
        )
        self._error_label.setVisible(False)
        layout.addWidget(self._error_label)

        # Output text area (read-only)
        self._output = QTextEdit()
        self._output.setPlaceholderText("Translation will appear here\u2026")
        self._output.setReadOnly(True)
        self._output.setMinimumHeight(120)
        layout.addWidget(self._output)

    def _setup_translation(self) -> None:
        self._source.textChanged.connect(self._on_source_changed)
        self._debounce.started.connect(self._on_translation_started)
        self._debounce.translation_ready.connect(self._on_translation_ready)
        self._debounce.error_occurred.connect(self._on_error)

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
        # target_lang and tone are hardcoded for Phase 2;
        # dropdowns + tone selector arrive in Phase 3.
        self._debounce.request(text, target_lang="English", tone="formal")

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
    # Click-outside to dismiss.
    # WindowDeactivate fires only when another application takes focus,
    # not when child widgets (e.g. QTextEdit) receive focus internally.
    # ------------------------------------------------------------------

    def changeEvent(self, event) -> None:
        if event.type() == QEvent.Type.WindowDeactivate:
            self.hide()
        super().changeEvent(event)

    # ------------------------------------------------------------------
    # Drag support (frameless window needs manual drag)
    # ------------------------------------------------------------------

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._drag_pos is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        self._drag_pos = None
        super().mouseReleaseEvent(event)

# window.py — Frameless popup QWidget with drag support and click-outside dismiss.

from PyQt6.QtWidgets import QWidget, QApplication
from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtGui import QKeyEvent


class TranslatorWindow(QWidget):
    """Main translator popup — frameless, draggable, always-on-top."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._drag_pos: QPoint | None = None
        self._setup_window()

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

        # Placeholder background so the window is visible
        self.setStyleSheet("QWidget { background-color: #f0f4f8; border-radius: 8px; }")

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

    def focusOutEvent(self, event) -> None:
        # Hide when focus moves to another application window
        self.hide()
        super().focusOutEvent(event)

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

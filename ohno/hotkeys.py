# hotkeys.py — Global hotkey listener using keyboard lib.
# Runs in a background thread; emits Qt signals back to the main thread.

import threading
import keyboard
from PyQt6.QtCore import QObject, pyqtSignal


class HotkeyListener(QObject):
    """Listens for global hotkeys in a daemon thread and emits Qt signals."""

    toggle_window = pyqtSignal()   # Ctrl+Shift+T
    clipboard_paste = pyqtSignal() # Ctrl+Shift+V (Phase 5)

    def __init__(self, hotkey: str = "ctrl+shift+t",
                 clipboard_hotkey: str = "ctrl+shift+v",
                 parent=None):
        super().__init__(parent)
        self._hotkey = hotkey
        self._clipboard_hotkey = clipboard_hotkey
        self._thread: threading.Thread | None = None
        self._running = False

    def start(self) -> None:
        """Register hotkeys and start the listener thread."""
        self._running = True
        self._thread = threading.Thread(target=self._listen, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Unregister hotkeys and stop the listener."""
        self._running = False
        try:
            keyboard.unhook_all()
        except Exception:
            pass

    def rebind(self, hotkey: str, clipboard_hotkey: str) -> None:
        """Re-register hotkeys with new key combos (live, no restart needed)."""
        try:
            keyboard.remove_hotkey(self._hotkey)
        except (KeyError, ValueError):
            pass
        try:
            keyboard.remove_hotkey(self._clipboard_hotkey)
        except (KeyError, ValueError):
            pass

        self._hotkey = hotkey
        self._clipboard_hotkey = clipboard_hotkey

        try:
            keyboard.add_hotkey(self._hotkey, self.toggle_window.emit)
            keyboard.add_hotkey(self._clipboard_hotkey, self.clipboard_paste.emit)
        except Exception as e:
            print(f"[hotkeys] rebind error: {e}")

    def _listen(self) -> None:
        try:
            keyboard.add_hotkey(self._hotkey, self.toggle_window.emit)
            keyboard.add_hotkey(self._clipboard_hotkey, self.clipboard_paste.emit)
            keyboard.wait()  # Blocks until stop() calls unhook_all()
        except Exception as e:
            print(f"[hotkeys] Error: {e}")

# main.py — Entry point: QApplication, system tray, hotkey listener, window bootstrap.

import sys
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtCore import Qt

from config import load as load_config
from window import TranslatorWindow
from hotkeys import HotkeyListener


def _icon_path() -> str:
    return str(Path(__file__).parent / "assets" / "icon.png")


def main() -> None:
    # Required for always-on-top + tray on Windows
    QApplication.setQuitOnLastWindowClosed(False)

    app = QApplication(sys.argv)
    app.setApplicationName("OHNO Translator")

    # -- Config ----------------------------------------------------------
    cfg = load_config()

    # -- Main window -----------------------------------------------------
    window = TranslatorWindow()

    # -- System tray -----------------------------------------------------
    icon = QIcon(_icon_path())
    tray = QSystemTrayIcon(icon, parent=app)
    tray.setToolTip("OHNO Translator")

    tray_menu = QMenu()

    open_action = QAction("Open", tray_menu)
    open_action.triggered.connect(window.toggle)
    tray_menu.addAction(open_action)

    tray_menu.addSeparator()

    settings_action = QAction("Settings", tray_menu)
    settings_action.setEnabled(False)  # Placeholder until Phase 6
    tray_menu.addAction(settings_action)

    tray_menu.addSeparator()

    exit_action = QAction("Exit", tray_menu)
    exit_action.triggered.connect(app.quit)
    tray_menu.addAction(exit_action)

    tray.setContextMenu(tray_menu)

    # Left-click tray icon → toggle window
    tray.activated.connect(
        lambda reason: window.toggle()
        if reason == QSystemTrayIcon.ActivationReason.Trigger
        else None
    )

    tray.show()

    # -- Hotkeys ---------------------------------------------------------
    listener = HotkeyListener(
        hotkey=cfg.get("hotkey", "ctrl+shift+t"),
        clipboard_hotkey=cfg.get("clipboard_hotkey", "ctrl+shift+v"),
    )
    listener.toggle_window.connect(window.toggle)
    listener.start()

    # -- Run -------------------------------------------------------------
    exit_code = app.exec()
    listener.stop()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()

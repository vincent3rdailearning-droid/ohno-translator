"""
clipboard.py — Clipboard read/write helpers for OHNO Translator.

Public API:
    get_clipboard_text() -> str | None
    set_clipboard_text(text: str) -> bool
    get_qt_clipboard_text(app: QApplication) -> str | None
    set_qt_clipboard_text(app: QApplication, text: str) -> bool
"""
from __future__ import annotations

import logging

import pyperclip
from PyQt6.QtWidgets import QApplication

_log = logging.getLogger(__name__)


def get_clipboard_text() -> str | None:
    """Read the clipboard using pyperclip.

    Returns the clipboard text if it is non-empty, otherwise None.
    Never raises — all exceptions are caught and logged.
    """
    try:
        text = pyperclip.paste()
        return text if text else None
    except Exception as exc:
        _log.warning("get_clipboard_text: failed to read clipboard: %s", exc)
        return None


def set_clipboard_text(text: str) -> bool:
    """Write text to the clipboard using pyperclip.

    Returns True on success, False on any exception.
    Never raises.
    """
    try:
        pyperclip.copy(text)
        return True
    except Exception as exc:
        _log.warning("set_clipboard_text: failed to write clipboard: %s", exc)
        return False


def get_qt_clipboard_text(app: QApplication) -> str | None:
    """Read the clipboard using Qt's clipboard API.

    Args:
        app: A QApplication instance whose clipboard() is used.

    Returns the clipboard text if it is non-empty, otherwise None.
    Never raises — all exceptions are caught and logged.
    """
    try:
        text = app.clipboard().text()
        return text if text else None
    except Exception as exc:
        _log.warning("get_qt_clipboard_text: failed to read clipboard: %s", exc)
        return None


def set_qt_clipboard_text(app: QApplication, text: str) -> bool:
    """Write text to the clipboard using Qt's clipboard API.

    Args:
        app: A QApplication instance whose clipboard() is used.
        text: The string to place on the clipboard.

    Returns True on success, False on any exception.
    Never raises.
    """
    try:
        app.clipboard().setText(text)
        return True
    except Exception as exc:
        _log.warning("set_qt_clipboard_text: failed to write clipboard: %s", exc)
        return False

# OHNO Translator

A lightweight desktop translator that lives in your system tray. Translate text between 15+ languages using Google Translate, with word lookup and text-to-speech pronunciation.

## Features

- **Instant translation** — type or paste text, translation appears automatically (500ms debounce)
- **Global hotkeys** — `Ctrl+Shift+T` to toggle window, `Ctrl+Shift+V` to paste clipboard and translate
- **Word lookup** — select 1-3 words to see definitions in a popup tooltip
- **Text-to-speech** — hear pronunciation of selected words via system TTS
- **Translation history** — last 10 translations saved and accessible from the History button
- **Light / Dark / System theme** — matches your Windows appearance or set manually
- **Always-on-top** — pin the window above other apps (toggle via title bar)
- **Start with Windows** — optional autostart via Settings

## Hotkeys

| Hotkey | Action |
|--------|--------|
| `Ctrl+Shift+T` | Show / hide translator window |
| `Ctrl+Shift+V` | Paste clipboard text and translate |
| `Escape` | Hide window |

All hotkeys are rebindable in Settings.

## Supported Languages

English, Chinese (Traditional), Chinese (Simplified), Japanese, Korean, Spanish, French, German, Italian, Portuguese, Russian, Arabic, Hindi, Thai, Vietnamese, Indonesian, Malay, Filipino

## Development Setup

```bash
# Clone and set up virtual environment
git clone https://github.com/vincent3rdailearning-droid/ohno-translator.git
cd ohno-translator
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# Run the app
cd ohno
python main.py
```

## Building the Executable

```bash
pip install pyinstaller
pyinstaller OHNO.spec
# Output: dist/OHNO.exe
```

## Configuration

Settings are stored in `%APPDATA%\OHNO\config.json`. Translation history is stored in `%APPDATA%\OHNO\history.json`.

## Tech Stack

- Python 3.11+
- PyQt6 (GUI framework)
- deep-translator (Google Translate)
- keyboard (global hotkeys)
- pyttsx3 (text-to-speech)
- pyperclip (clipboard)

## License

MIT

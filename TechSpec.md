# Tech Spec — OHNO Translator Plugin

**Project**: OHNO Translator
**Version**: 1.0 (MVP)
**Date**: 2026-02-28
**Status**: Pre-development — docs complete, coding not yet started

---

## 1. Tech Stack

| Layer | Choice | Reason |
|-------|--------|--------|
| Language | Python 3.11+ | Cross-compat, rich ecosystem, team familiarity |
| GUI | PyQt6 | Native Windows feel, lightweight, well-documented |
| Translation API | Claude API (`claude-haiku-4-5` default, swappable) | Quality + tone control via system prompts |
| Global Hotkeys | `keyboard` library | Simpler than pynput for Windows; background thread |
| TTS (pronunciation) | `pyttsx3` (Windows SAPI) | Zero extra cost, fully offline, no API key needed |
| Clipboard | `pyperclip` + `QClipboard` | Reliable cross-context access |
| Config Storage | JSON in `%APPDATA%\OHNO\` | Portable, human-readable, no registry complexity |
| API Key Storage | `keyring` (Windows Credential Manager) | Secure, never written to disk in plaintext |
| Packaging | PyInstaller → single `.exe` | One-click install, no Python needed on user machine |
| Anthropic SDK | `anthropic` Python SDK | Official, maintained, handles auth + streaming |

**Python dependencies** (`requirements.txt`):
```
anthropic>=0.40.0
PyQt6>=6.6.0
keyboard>=0.13.5
pyttsx3>=2.90
pyperclip>=1.8.2
keyring>=24.0.0
pyinstaller>=6.0.0
```

---

## 2. Architecture Diagram

```
Windows System
├── System Tray (QSystemTrayIcon)
│    ├── Left-click → toggle popup show/hide
│    └── Right-click menu → Open | Settings | Exit
│
├── Global Hotkey Listener (keyboard lib, background thread)
│    ├── Ctrl+Shift+T → show/hide popup window
│    └── Ctrl+Shift+V → paste clipboard to source textarea
│
└── Popup Window (QWidget, always-on-top, frameless)
     ├── Translation Panel
     │    ├── Source TextArea (QTextEdit, editable)
     │    ├── Language Dropdown — Source (QComboBox)
     │    ├── Tone Selector — Formal | Casual | Literal (QButtonGroup / QRadioButton)
     │    ├── Swap Button (⇄) — swaps source↔target language
     │    ├── Language Dropdown — Target (QComboBox)
     │    ├── Output TextArea (read-only QTextEdit)
     │    └── Copy | Clear buttons
     │
     ├── Word Lookup Engine
     │    ├── mouseReleaseEvent → detect text selection
     │    ├── Send selected word to Claude for definition
     │    ├── Definition Tooltip (QFrame popup near cursor)
     │    └── Pronunciation Button → pyttsx3.speak()
     │
     └── Settings Panel (QDialog, modal)
          ├── Hotkey rebinder (capture keypress → store in config)
          ├── Clipboard hotkey rebinder
          ├── Default language pair (source + target dropdowns)
          ├── Default tone (radio buttons)
          ├── API Key input (QLineEdit, password mode → keyring.set_password())
          ├── Theme: Light / Dark / System (QStyleFactory / QPalette)
          └── Start with Windows (HKCU\Software\Microsoft\Windows\CurrentVersion\Run)

Translation Engine (QThread)
├── QTimer (500ms debounce) — resets on each keystroke
├── Prompt builder (tone-aware system prompt per tone setting)
├── anthropic.Anthropic().messages.create(model, system, messages)
├── Signal: translation_ready → update output QTextEdit
└── Signal: error_occurred → show error banner + retry button

Config Module (config.py)
├── Schema: {hotkey, clipboard_hotkey, default_source_lang, default_target_lang,
│           default_tone, theme, start_with_windows, model}
├── Load: json.load from %APPDATA%\OHNO\config.json (create defaults if missing)
└── Save: json.dump with indent=2
```

---

## 3. Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **Debounce on QTimer (500ms)** | Avoids hammering the Claude API mid-sentence as user types. Timer resets on each keystroke; fires translation only after 500ms of silence. |
| **Translation runs on QThread** | Never blocks the UI thread. PyQt6 signals carry the result back to main thread safely. |
| **Config in AppData JSON** | Portable, easy to read/reset/back up, no registry complexity. Path: `%APPDATA%\OHNO\config.json`. |
| **API key in keyring** | Uses Windows Credential Manager. API key is never written to the JSON config file. Retrieved at runtime via `keyring.get_password("ohno", "api_key")`. |
| **Model default: `claude-haiku-4-5`** | Lowest latency for the translation use case. User can switch to `claude-sonnet-4-6` in settings for higher quality at the cost of speed. |
| **Frameless window** | Custom title bar (draggable QWidget) for a cleaner look. Window controls implemented manually. |
| **Always-on-top toggle** | Default: on. User can toggle off via a pin icon in the title bar if they want the window to go behind other apps. |
| **Single instance** | Only one OHNO popup at a time. If hotkey fires while popup is visible, hide it. Fire again to show. |

---

## 4. Tone-Aware System Prompts

Each tone maps to a distinct system prompt prefix sent to Claude:

| Tone | System Prompt |
|------|---------------|
| **Formal** | "You are a professional translator. Translate the following text into {target_lang} using formal, polished language appropriate for business or academic contexts. Return only the translated text." |
| **Casual** | "You are a translator. Translate the following text into {target_lang} using natural, conversational language as a native speaker would say it. Return only the translated text." |
| **Literal** | "You are a translator. Provide a literal, word-for-word translation of the following text into {target_lang}, preserving the original structure as closely as possible. Return only the translated text." |

**Word lookup prompt**: "Define the word or phrase '{word}' as used in {source_lang}. Provide: 1) pronunciation/romanization if applicable, 2) part of speech, 3) a concise definition (1–2 sentences). Format as plain text."

---

## 5. Project File Structure

```
ohno/
├── main.py              ← entry point: QApplication, tray init, window bootstrap
├── window.py            ← main popup QWidget: layout, controls, drag, resize
├── translation.py       ← QThread subclass + Claude API client + debounce timer
├── word_lookup.py       ← text selection detection, tooltip QFrame, TTS via pyttsx3
├── settings.py          ← settings QDialog: all settings fields + config R/W
├── hotkeys.py           ← keyboard lib listener thread, hotkey dispatch
├── clipboard.py         ← pyperclip + QClipboard read/write helpers
├── config.py            ← config schema, defaults, load/save to %APPDATA%\OHNO\
├── assets/
│    └── icon.png        ← tray icon (16×16 + 32×32 PNG)
└── requirements.txt
```

---

## 6. Supported Languages

Initial language list (Claude supports all; these are in the dropdown):

| Code | Display Name |
|------|-------------|
| `zh-TW` | Chinese (Traditional) |
| `zh-CN` | Chinese (Simplified) |
| `ja` | Japanese |
| `en` | English |
| `ko` | Korean |
| `fr` | French |
| `de` | German |
| `es` | Spanish |

User selects display names. Code is passed in the system prompt as the full language name (e.g., "Traditional Chinese").

---

## 7. Configuration Schema

File: `%APPDATA%\OHNO\config.json`

```json
{
  "hotkey": "ctrl+shift+t",
  "clipboard_hotkey": "ctrl+shift+v",
  "default_source_lang": "zh-TW",
  "default_target_lang": "en",
  "default_tone": "formal",
  "theme": "system",
  "start_with_windows": false,
  "model": "claude-haiku-4-5"
}
```

API key is **not** in this file. It is stored via `keyring.set_password("ohno", "api_key", value)`.

---

## 8. Error Handling

| Error Type | Behavior |
|------------|----------|
| API key missing | Show banner in output area: "API key not set. Open Settings to add it." |
| Claude API error (5xx) | Show "Translation failed. [Retry]" button |
| Rate limit (429) | Show "Rate limited. Please wait a moment." + 10s cooldown |
| Network timeout | Show "Connection timed out. Check internet." |
| hotkey conflict | Log warning; silently ignore (user notified in Settings if hotkey fails to register) |
| pyttsx3 unavailable | Hide pronunciation button; log warning |

---

## 9. Packaging Notes

**PyInstaller command**:
```
pyinstaller --onefile --windowed --icon=assets/icon.ico --name=OHNO main.py
```

- `--windowed`: suppresses console window
- Include `assets/` folder in `.spec` file data list
- Expected `.exe` size: ~30–60MB (PyQt6 bundled)
- Known issue: antivirus false positives with PyInstaller executables. Mitigation: code-sign the exe, document exception instructions in README.

---

## 10. Lessons Learned

*← Populated after development is complete.*

---

## 11. Post-Release Feedback

*← Populated after launch.*

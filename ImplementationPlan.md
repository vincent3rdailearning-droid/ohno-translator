# Implementation Plan — OHNO Translator Plugin

**Project**: OHNO Translator
**Version**: 1.0 (MVP)
**Date**: 2026-02-28
**Status**: In development
**Current Phase**: Phase 3 — UI Polish (next up)

---

## Phase Overview

| Phase | Name | Deliverable | Branch | Status |
|-------|------|-------------|--------|--------|
| 0 | Setup | Repo, venv, deps, project skeleton | `setup` | ✅ Complete |
| 1 | Tray + Window | System tray icon, basic popup, Ctrl+Shift+T hotkey | `feature/tray-window` | ✅ Complete |
| 2 | Translation Core | Claude API, debounce, tone-aware prompts, loading/error states | `feature/translation-core` | ✅ Complete |
| 3 | UI Polish | Language dropdowns, swap button, copy/clear, full layout | `feature/ui-polish` | 🔄 Next |
| 4 | Word Lookup | Highlight → definition tooltip, TTS pronunciation | `feature/word-lookup` | ⬜ Not started |
| 5 | Clipboard Integration | Ctrl+Shift+V hotkey, auto-populate source | `feature/clipboard` | ⬜ Not started |
| 6 | Settings Panel | All settings, API key secure storage, theme, autostart | `feature/settings` | ⬜ Not started |
| 7 | Packaging + Release | PyInstaller .exe, installer, README | `feature/packaging` | ⬜ Not started |

---

## Phase 0 — Setup

**Branch**: `setup`
**Goal**: Working dev environment, all deps installed, project structure created.

### Tasks
- [x] Create `ohno/` project folder with file structure from TechSpec
- [x] `git init` + create GitHub repo + push initial commit
- [x] Create Python 3.14 venv: `python -m venv .venv`
- [x] Install dependencies: `pip install -r requirements.txt`
- [x] Verify imports work: `python -c "import PyQt6; import anthropic; import keyboard; print('OK')"`
- [x] Create `assets/icon.png` placeholder (32×32 PNG generated via PyQt6)
- [x] Create `config.py` with schema + defaults + load/save to `%APPDATA%/OHNO/`
- [x] Smoke test: `config.py` creates `config.json` in AppData on first run

### Acceptance Criteria
- [x] All imports resolve without error
- [x] `config.json` created automatically with defaults in correct AppData path
- [x] Git repo pushed to GitHub with `.gitignore` covering venv, `__pycache__`, `.exe`

### Notes
- Python 3.14.3 used (Windows Store install) — satisfies 3.11+ requirement
- GitHub repo: https://github.com/vincent3rdailearning-droid/ohno-translator

### Known Risks
| Risk | Mitigation |
|------|------------|
| PyQt6 install fails on some Windows configs | Use `pip install PyQt6` (not PyQt6-tools); check MSVC runtime |
| `keyboard` requires admin for some hotkey combos | Test Ctrl+Shift+T early; document if elevation needed |

---

## Phase 1 — Tray + Window

**Branch**: `feature/tray-window`
**Goal**: OHNO lives in system tray; Ctrl+Shift+T shows/hides a blank popup.

### Tasks
- [x] `main.py`: Create `QApplication`, `QSystemTrayIcon` with icon + left/right-click menus
- [x] `window.py`: Create frameless `QWidget` popup (fixed starting size, draggable)
- [x] `hotkeys.py`: Background thread listening for `Ctrl+Shift+T`, emits Qt signal
- [x] Wire hotkey signal → `window.show()` / `window.hide()` toggle
- [x] Implement click-outside-to-dismiss (`focusOutEvent`)
- [x] Implement Escape key to dismiss
- [x] Always-on-top flag: `Qt.WindowStaysOnTopHint`
- [x] Tray right-click menu: Open | Settings (placeholder) | Exit
- [x] `main.py`: App stays alive when popup is closed (no `sys.exit` on close)

### Acceptance Criteria
- [x] OHNO starts → tray icon appears within 3 seconds
- [x] `Ctrl+Shift+T` → popup appears in < 200ms
- [x] `Ctrl+Shift+T` again → popup hides
- [x] `Escape` dismisses popup
- [x] Click outside popup → popup hides
- [x] Tray right-click → menu appears with Open / Exit working
- [x] Exit from tray → app fully quits

### Notes
- `keyboard` lib hotkeys also pre-registered for `Ctrl+Shift+V` (clipboard, Phase 5)
- Smoke test: app ran 5s with no crash; tray icon confirmed visible

### Known Risks
| Risk | Mitigation |
|------|------------|
| `keyboard` lib hotkey conflicts with other apps | Test with common apps open; make rebindable in Phase 6 |
| Frameless window hard to drag on Windows 11 | Implement custom `mousePressEvent` + `mouseMoveEvent` |

---

## Phase 2 — Translation Core

**Branch**: `feature/translation-core`
**Goal**: Type in source textarea → translation appears in output after 500ms.
**Strategy**: Option B — Backend-first parallelism. Track A and Track B run simultaneously (background agents); Integration runs after both complete.

---

### Track A — `translation.py` (Agent 1, parallel)

**File**: `ohno/translation.py`
**Scope**: Standalone — does NOT touch `window.py`

- [x] `TranslationWorker(QThread)` class with `anthropic` client initialised from keyring
- [x] `pyqtSignal` definitions: `translation_ready(str)`, `error_occurred(str)`
- [x] 500ms debounce via `DebounceManager(QObject)` wrapping `QTimer` — resets on every keystroke
- [x] Tone-aware system prompt builder (Formal / Casual / Literal) from `TechSpec.md §4`
- [x] Handle empty source text → emit nothing, do not call API
- [x] Handle API errors (timeout, auth, rate-limit) → emit `error_occurred(str)` with user-facing message
- [x] Cancel in-flight request before starting a new one (store thread ref, call `quit()`)

---

### Track B — `clipboard.py` (Agent 2, parallel)

**File**: `ohno/clipboard.py`
**Scope**: Standalone — does NOT touch `window.py`
**Note**: Phase 5 prep done here since it's self-contained

- [x] `get_clipboard_text() -> str | None` — `pyperclip.paste()` with error handling
- [x] `set_clipboard_text(text: str)` — `pyperclip.copy(text)`
- [x] `QClipboard` wrapper: `get_qt_clipboard_text(app: QApplication) -> str | None`
- [x] Handle non-text clipboard content (images, empty) → return `None` gracefully
- [x] Module-level docstring describing public API

---

### Integration — wire into `window.py` (sequential, after both tracks complete)

- [x] Add source `QTextEdit` and output `QTextEdit` to `TranslatorWindow`
- [x] Instantiate `DebounceManager`; connect `textChanged` → `debounce.request()`
- [x] Connect `translation_ready` → update output textarea
- [x] Connect `error_occurred` → show inline error banner (`QLabel`)
- [x] Loading status label ("Translating…") shown while request is in-flight
- [x] Placeholder output text: "Translation will appear here…"
- [x] Clear output when source is cleared

---

### Acceptance Criteria
- [x] Type a sentence → translation appears within 1.5 seconds (p90)
- [x] Loading indicator visible during translation
- [x] Stop typing 500ms → translation fires (not on every keystroke)
- [x] Clear source → output clears
- [x] Disconnect internet → "Connection timed out" message shown
- [x] Missing API key → "API key not set" message shown

### Notes
- `DebounceManager` owns the full worker lifecycle (create, connect, cancel, clean up) — callers only call `request()` and connect to manager signals
- `focusOutEvent` replaced with `changeEvent(WindowDeactivate)` — fires only when another app takes focus, not when child QTextEdits receive focus internally
- `target_lang` ("English") and `tone` ("formal") are hardcoded for Phase 2; dropdowns + tone selector arrive in Phase 3
- Track A and Track B were implemented in parallel by two background agents simultaneously; integration was done sequentially after both completed

### Known Risks
| Risk | Mitigation |
|------|------------|
| API calls on QThread crash PyQt6 on some versions | Use `QMetaObject.invokeMethod` for thread-safe signal emit |
| Debounce timer fires for already-cancelled text | Cancel in-flight request before starting new one |

---

## Phase 3 — UI Polish

**Branch**: `feature/ui-polish`
**Goal**: Full layout matching wireframe — language dropdowns, swap, copy/clear, tone selector.

### Tasks
- [ ] Language dropdowns (Source + Target): populate from `TechSpec.md §6` language list
- [ ] Swap (⇄) button: swaps source↔target language AND swaps source/output text
- [ ] Tone selector: Formal / Casual / Literal radio buttons (QButtonGroup)
- [ ] Copy Output button: `pyperclip.copy(output_text.toPlainText())`
- [ ] Clear button: clears both source and output textareas
- [ ] Settings gear icon button (placeholder action until Phase 6)
- [ ] Title bar: custom drag area + close (hide) button + always-on-top pin toggle
- [ ] Min window size: 400×350px; resizable with splitter between source/output
- [ ] Light theme base styling (QSS stylesheet)
- [ ] Font: system default (no custom font deps)

### Acceptance Criteria
- [ ] All UI elements from wireframe present and functional
- [ ] Swap button swaps language pair and text content correctly
- [ ] Changing tone while text is in source area re-triggers translation
- [ ] Copy button copies output to clipboard
- [ ] Clear button clears both areas
- [ ] Window resizable; text areas expand with resize

### Known Risks
| Risk | Mitigation |
|------|------------|
| QSS styling inconsistent between Windows 10 / 11 | Test on both; use minimal QSS |
| Splitter between textareas may feel awkward | Consider fixed 50/50 split for MVP |

---

## Phase 4 — Word Lookup

**Branch**: `feature/word-lookup`
**Goal**: Highlight a word in source or output → definition tooltip with pronunciation.

### Tasks
- [ ] `word_lookup.py`: detect `mouseReleaseEvent` on both QTextEdits
- [ ] If selection ≥ 1 word: extract selected text
- [ ] Call Claude API for definition (prompt from `TechSpec.md §4`)
- [ ] Show definition as `QFrame` tooltip near cursor (not system tooltip — custom widget)
- [ ] Tooltip contains: word, pronunciation/romanization, part of speech, definition
- [ ] Pronunciation button in tooltip: `pyttsx3.init().say(selected_word)` in a thread
- [ ] Tooltip auto-dismisses on next click or 8 seconds
- [ ] Handle pyttsx3 unavailable: hide pronunciation button gracefully

### Acceptance Criteria
- [ ] Select a word → tooltip appears within 1.5 seconds
- [ ] Tooltip shows definition in correct format
- [ ] Click pronunciation button → word spoken aloud
- [ ] Tooltip dismisses on click outside or Escape
- [ ] Works in both source and output textareas
- [ ] Graceful degradation if pyttsx3 fails

### Known Risks
| Risk | Mitigation |
|------|------------|
| Definition tooltip overlaps translation output | Position tooltip above/below based on available screen space |
| pyttsx3 blocks UI thread | Run `say()` in a `QThread` or `threading.Thread` |

---

## Phase 5 — Clipboard Integration

**Branch**: `feature/clipboard`
**Goal**: `Ctrl+Shift+V` pastes clipboard contents into source textarea from anywhere.

### Tasks
- [ ] `clipboard.py`: `pyperclip.paste()` helper; `QClipboard` integration
- [ ] `hotkeys.py`: register second hotkey `Ctrl+Shift+V`
- [ ] On `Ctrl+Shift+V`: show popup (if hidden) + paste clipboard into source textarea
- [ ] If clipboard is empty/non-text: show brief "No text in clipboard" message
- [ ] Make clipboard hotkey rebindable (config key: `clipboard_hotkey`)
- [ ] Show popup window if it was hidden when clipboard hotkey fires

### Acceptance Criteria
- [ ] `Ctrl+Shift+V` while using any Windows app → OHNO popup appears + clipboard text pasted
- [ ] Translation triggers automatically after paste (500ms debounce)
- [ ] Empty clipboard → message shown, no crash
- [ ] Non-text clipboard content (image) → handled gracefully

### Known Risks
| Risk | Mitigation |
|------|------------|
| `Ctrl+Shift+V` conflicts with some apps | Make fully rebindable in Phase 6 |
| Clipboard access denied by some security software | Document known issue; suggest rebinding |

---

## Phase 6 — Settings Panel

**Branch**: `feature/settings`
**Goal**: Full settings dialog — all user preferences, API key secure storage, theme, autostart.

### Tasks
- [ ] `settings.py`: `SettingsDialog(QDialog)` modal
- [ ] Hotkey rebinder: capture any keypress combo → validate → store in config
- [ ] Clipboard hotkey rebinder: same approach
- [ ] Default language pair: Source + Target dropdowns
- [ ] Default tone: Formal / Casual / Literal radio buttons
- [ ] API Key field: `QLineEdit` with password masking + Show/Hide toggle → `keyring.set_password("ohno", "api_key", value)` on Save
- [ ] API Key display: show masked if already set, "Not set" if missing
- [ ] Model selector: dropdown (haiku-4-5 / sonnet-4-6)
- [ ] Theme: Light / Dark / System radio → apply `QPalette` + QSS immediately on change
- [ ] Start with Windows: checkbox → add/remove `HKCU\...\Run\OHNO` registry key
- [ ] Save / Cancel buttons; changes only apply on Save
- [ ] Settings gear icon in main window opens this dialog

### Acceptance Criteria
- [ ] All settings save correctly and persist across app restarts
- [ ] API key stored via keyring (not in config.json)
- [ ] Theme change applies immediately without restart
- [ ] Hotkey rebind takes effect immediately after save
- [ ] Start with Windows toggle works (test by rebooting)
- [ ] Cancel discards all unsaved changes

### Known Risks
| Risk | Mitigation |
|------|------------|
| Registry write for autostart may require elevation | Use `HKCU` (not HKLM) — no elevation needed |
| Invalid hotkey combo (e.g., single key) causes keyboard lib error | Validate combo requires modifier key before accepting |
| keyring fails on some Windows configs | Fallback: warn user, offer to store in config (with plaintext warning) |

---

## Phase 7 — Packaging + Release

**Branch**: `feature/packaging`
**Goal**: Single distributable `.exe`; README with install + setup instructions.

### Tasks
- [ ] Create `icon.ico` from `assets/icon.png` (must be .ico for Windows exe)
- [ ] Write `OHNO.spec` PyInstaller spec file with data files (assets)
- [ ] Build: `pyinstaller OHNO.spec` → test `dist/OHNO.exe` on clean Windows VM
- [ ] Create `README.md`: what is OHNO, install steps, first-run (add API key), hotkeys
- [ ] Create `CHANGELOG.md` with v1.0.0 entries
- [ ] Write release checklist (see below)
- [ ] Tag `v1.0.0` in git
- [ ] Create GitHub release with `.exe` attached

### Release Checklist
- [ ] Fresh Windows 10 install: exe runs without errors
- [ ] Fresh Windows 11 install: exe runs without errors
- [ ] API key setup flow works end-to-end
- [ ] Translation fires correctly (all 3 tones)
- [ ] Hotkey works when other apps are in focus
- [ ] System tray icon visible
- [ ] Exit from tray fully quits (no zombie process)
- [ ] Start with Windows tested (reboot)
- [ ] Antivirus scan: document false positive if present

### Known Risks
| Risk | Mitigation |
|------|------------|
| PyInstaller antivirus false positive | Code-sign the exe; add note to README about false positive |
| `.exe` size > 100MB | Use `--exclude-module` for unused Qt modules in spec |
| Missing DLLs on target machine | Test on clean VM without Python installed |

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Claude API rate limits during heavy use | Low | Medium | Show rate-limit error + 10s backoff + retry button |
| Hotkey conflicts with other installed apps | Medium | High | Allow full rebind in settings (Phase 6) |
| PyInstaller antivirus false positive | Medium | Medium | Code-sign exe; document exception in README |
| pyttsx3 voice quality poor | Low | Low | Acceptable for MVP; note as known limitation |
| `keyboard` lib requires elevated privileges | Low | High | Test early in Phase 1; document if needed |
| Windows version compatibility (10 vs 11) | Low | Medium | Test on both during packaging phase |

---

## Testing Approach

**MVP strategy: manual smoke test per phase** (no automated test suite for GUI MVP).

Each phase includes a checkbox acceptance criteria list above. Before merging a branch, all acceptance criteria must be manually verified.

### Final Release Checklist (Phase 7)
- Full Phase 7 release checklist above
- Regression: re-verify all Phase 1–6 acceptance criteria on the packaged `.exe`

### If bugs found post-release
- Branch: `fix/[bug-description]`
- Hotfix PR to `main`
- Bump version to `1.0.1`

---

## Development Conventions

- **Branch naming**: `feature/[feature-name]`, `setup`, `fix/[bug]`
- **Commit style**: conventional commits
  - `feat:` new feature
  - `fix:` bug fix
  - `chore:` deps, config, tooling
  - `docs:` documentation
- **One phase per PR** — merge to `main` after phase acceptance criteria pass
- **Never commit API keys** — `config.json` in `.gitignore`; API key in keyring only

---

## Lessons Learned

*← Populated after development is complete.*

---

## Post-Release Feedback

*← Populated after launch.*

# Implementation Plan — OHNO Translator Plugin

**Project**: OHNO Translator
**Version**: 1.0 (MVP)
**Date**: 2026-02-28
**Status**: Pre-development — docs complete, coding not yet started
**Current Phase**: Phase 0 (not yet started)

---

## Phase Overview

| Phase | Name | Deliverable | Branch | Status |
|-------|------|-------------|--------|--------|
| 0 | Setup | Repo, venv, deps, project skeleton | `setup` | ⬜ Not started |
| 1 | Tray + Window | System tray icon, basic popup, Ctrl+Shift+T hotkey | `feature/tray-window` | ⬜ Not started |
| 2 | Translation Core | Claude API, debounce, tone-aware prompts, loading/error states | `feature/translation-core` | ⬜ Not started |
| 3 | UI Polish | Language dropdowns, swap button, copy/clear, full layout | `feature/ui-polish` | ⬜ Not started |
| 4 | Word Lookup | Highlight → definition tooltip, TTS pronunciation | `feature/word-lookup` | ⬜ Not started |
| 5 | Clipboard Integration | Ctrl+Shift+V hotkey, auto-populate source | `feature/clipboard` | ⬜ Not started |
| 6 | Settings Panel | All settings, API key secure storage, theme, autostart | `feature/settings` | ⬜ Not started |
| 7 | Packaging + Release | PyInstaller .exe, installer, README | `feature/packaging` | ⬜ Not started |

---

## Phase 0 — Setup

**Branch**: `setup`
**Goal**: Working dev environment, all deps installed, project structure created.

### Tasks
- [ ] Create `ohno/` project folder with file structure from TechSpec
- [ ] `git init` + create GitHub repo + push initial commit
- [ ] Create Python 3.11 venv: `python -m venv .venv`
- [ ] Install dependencies: `pip install -r requirements.txt`
- [ ] Verify imports work: `python -c "import PyQt6; import anthropic; import keyboard; print('OK')"`
- [ ] Create `assets/icon.png` placeholder (any 32×32 PNG)
- [ ] Create `config.py` with schema + defaults + load/save to `%APPDATA%\OHNO\`
- [ ] Smoke test: `config.py` creates `config.json` in AppData on first run

### Acceptance Criteria
- [ ] All imports resolve without error
- [ ] `config.json` created automatically with defaults in correct AppData path
- [ ] Git repo pushed to GitHub with `.gitignore` covering venv, `__pycache__`, `.exe`

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
- [ ] `main.py`: Create `QApplication`, `QSystemTrayIcon` with icon + left/right-click menus
- [ ] `window.py`: Create frameless `QWidget` popup (fixed starting size, draggable)
- [ ] `hotkeys.py`: Background thread listening for `Ctrl+Shift+T`, emits Qt signal
- [ ] Wire hotkey signal → `window.show()` / `window.hide()` toggle
- [ ] Implement click-outside-to-dismiss (`QApplication.focusChanged` or `leaveEvent`)
- [ ] Implement Escape key to dismiss
- [ ] Always-on-top flag: `Qt.WindowStaysOnTopHint`
- [ ] Tray right-click menu: Open | Settings (placeholder) | Exit
- [ ] `main.py`: App stays alive when popup is closed (no `sys.exit` on close)

### Acceptance Criteria
- [ ] OHNO starts → tray icon appears within 3 seconds
- [ ] `Ctrl+Shift+T` → popup appears in < 200ms
- [ ] `Ctrl+Shift+T` again → popup hides
- [ ] `Escape` dismisses popup
- [ ] Click outside popup → popup hides
- [ ] Tray right-click → menu appears with Open / Exit working
- [ ] Exit from tray → app fully quits

### Known Risks
| Risk | Mitigation |
|------|------------|
| `keyboard` lib hotkey conflicts with other apps | Test with common apps open; make rebindable in Phase 6 |
| Frameless window hard to drag on Windows 11 | Implement custom `mousePressEvent` + `mouseMoveEvent` |

---

## Phase 2 — Translation Core

**Branch**: `feature/translation-core`
**Goal**: Type in source textarea → translation appears in output after 500ms.

### Tasks
- [ ] `translation.py`: `TranslationWorker(QThread)` with `anthropic` client
- [ ] 500ms debounce: `QTimer.singleShot(500, ...)` resets on every keystroke
- [ ] Build tone-aware system prompt (Formal / Casual / Literal) from `TechSpec.md §4`
- [ ] Wire source `QTextEdit.textChanged` → debounce → `TranslationWorker.start()`
- [ ] Worker emits `translation_ready(str)` signal → update output `QTextEdit`
- [ ] Worker emits `error_occurred(str)` signal → show error banner
- [ ] Loading spinner (animated `QLabel` or `QMovie`) visible during in-flight request
- [ ] Placeholder output text: "Translation will appear here..."
- [ ] Handle: empty source → clear output, do not call API
- [ ] Handle: API errors (see TechSpec §8) with appropriate messages

### Acceptance Criteria
- [ ] Type a sentence → translation appears within 1.5 seconds (p90)
- [ ] Loading spinner visible during translation
- [ ] Stop typing 500ms → translation fires (not on every keystroke)
- [ ] Clear source → output clears
- [ ] Disconnect internet → "Connection timed out" message shown
- [ ] Missing API key → "API key not set" message shown

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

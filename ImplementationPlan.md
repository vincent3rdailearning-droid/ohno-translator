# Implementation Plan — OHNO Translator Plugin

**Project**: OHNO Translator
**Version**: 1.0 (MVP)
**Date**: 2026-02-28
**Status**: Complete (all phases implemented)
**Current Phase**: Done — ready for testing and release

---

## Phase Overview

| Phase | Name | Deliverable | Branch | Status |
|-------|------|-------------|--------|--------|
| 0 | Setup | Repo, venv, deps, project skeleton | `setup` | ✅ Complete |
| 1 | Tray + Window | System tray icon, basic popup, Ctrl+Shift+T hotkey | `feature/tray-window` | ✅ Complete |
| 2 | Translation Core | Claude API, debounce, tone-aware prompts, loading/error states | `feature/translation-core` | ✅ Complete |
| 3 | UI Polish | Language dropdowns, swap button, copy/clear, full layout | `feature/ui-polish` | ✅ Complete |
| 4 | Word Lookup | Highlight → definition tooltip, TTS pronunciation | `feature/phases-4-7` | ✅ Complete |
| 5 | Clipboard Integration | Ctrl+Shift+V hotkey, auto-populate source | `feature/phases-4-7` | ✅ Complete |
| 6 | Settings Panel | Theme, autostart, hotkey rebind | `feature/phases-4-7` | ✅ Complete |
| 7 | Packaging + Release | PyInstaller .exe, README, CHANGELOG | `feature/phases-4-7` | ✅ Complete |

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
- [x] Language dropdowns (Source + Target): populate from `TechSpec.md §6` language list
- [x] Swap (⇄) button: swaps source↔target language AND swaps source/output text
- [x] Tone selector: Formal / Casual / Literal radio buttons (QButtonGroup)
- [x] Copy Output button: `pyperclip.copy(output_text.toPlainText())`
- [x] Clear button: clears both source and output textareas
- [x] Settings gear icon button (placeholder action until Phase 6)
- [x] Title bar: custom drag area + close (hide) button + always-on-top pin toggle
- [x] Min window size: 400×350px; resizable with splitter between source/output
- [x] Light theme base styling (QSS stylesheet)
- [x] Font: system default (no custom font deps)

### Acceptance Criteria
- [x] All UI elements from wireframe present and functional
- [x] Swap button swaps language pair and text content correctly
- [x] Changing tone while text is in source area re-triggers translation
- [x] Copy button copies output to clipboard
- [x] Clear button clears both areas
- [x] Window resizable; text areas expand with resize

### Notes
- Custom `_TitleBar` widget handles drag; main window no longer has `mousePressEvent`/`mouseMoveEvent` overrides
- `LANGUAGES` dict maps language codes to display names; reverse lookup via `_NAME_TO_CODE`
- Swap uses `blockSignals()` to prevent double-triggering translation during swap
- Copy uses `clipboard.set_clipboard_text()` (pyperclip wrapper from Phase 2)
- `cfg` dict passed from `main.py` to `TranslatorWindow` — reads `default_source_lang`, `default_target_lang`, `default_tone`
- Pin toggle re-applies `windowFlags()` and re-shows window to take effect (Qt requirement)

### Known Risks
| Risk | Mitigation |
|------|------------|
| QSS styling inconsistent between Windows 10 / 11 | Test on both; use minimal QSS |
| Splitter between textareas may feel awkward | Consider fixed 50/50 split for MVP |

---

## Phase 4 — Word Lookup

**Branch**: `feature/phases-4-7` (previously `feature/word-lookup`)
**Goal**: Highlight a word in source or output → definition tooltip with pronunciation.

### Tasks
- [x] `word_lookup.py`: `LookupManager` with `deep_translator` for definitions, `LookupPopup` QFrame tooltip
- [x] `_SelectableTextEdit` subclass: selection detection via `selectionChanged` + 200ms debounce timer
- [x] If selection ≤ 3 words and ≤ 40 chars: trigger lookup
- [x] Show definition as `QFrame` tooltip near cursor (custom widget, not system tooltip)
- [x] Tooltip contains: word, pronunciation/romanization, part of speech, definition
- [x] Pronunciation button in tooltip: `pyttsx3.init().say(selected_word)` in a background thread
- [x] Tooltip auto-dismisses on next click or 8 seconds
- [x] Handle pyttsx3 unavailable: hide pronunciation button gracefully

### Extra features implemented alongside Phase 4
- [x] **Resize grips**: `QSizeGrip` in both bottom corners for window resizing
- [x] **Minimize button**: added to custom title bar
- [x] **Pin fix**: toggle re-applies `windowFlags()` and re-shows if visible
- [x] **Translation history**: auto-save last 10 translations, history menu via History button
- [x] **Bring to Front**: tray menu action + `_ensure_on_screen()` safety check
- [x] **Settings dialog (partial)**: language, tone, hotkey text fields (Phase 6 partial)

### Acceptance Criteria
- [x] Select a word → tooltip appears within 1.5 seconds
- [x] Tooltip shows definition in correct format
- [x] Click pronunciation button → word spoken aloud
- [x] Tooltip dismisses on click outside or Escape
- [x] Works in both source and output textareas
- [x] Graceful degradation if pyttsx3 fails

### Notes
- Uses `deep_translator` (Google Translate) instead of Claude API — no API key needed for lookup
- `LookupManager` runs lookup in `QThread` to avoid blocking UI
- `_SelectableTextEdit.text_selected` signal carries `(word, lang_code)` tuple
- Lookup popup uses `Qt.WindowType.Popup` for auto-dismiss behavior

### Known Risks
| Risk | Mitigation |
|------|------------|
| Definition tooltip overlaps translation output | Position tooltip above/below based on available screen space |
| pyttsx3 blocks UI thread | Run `say()` in a `QThread` or `threading.Thread` |

---

## Phase 5 — Clipboard Integration

**Branch**: `feature/phases-4-7`
**Goal**: `Ctrl+Shift+V` pastes clipboard contents into source textarea from anywhere.

### Tasks
- [x] `clipboard.py`: `pyperclip.paste()` helper; `QClipboard` integration (done in Phase 2)
- [x] `hotkeys.py`: register second hotkey `Ctrl+Shift+V` (done in Phase 1)
- [x] `window.py`: `paste_clipboard()` method — show popup if hidden, set source text
- [x] `main.py`: connect `listener.clipboard_paste` signal to `window.paste_clipboard`
- [x] If clipboard is empty/non-text: show brief "No text in clipboard" status message (1.5s)
- [x] Make clipboard hotkey rebindable (config key: `clipboard_hotkey`)

### Acceptance Criteria
- [x] `Ctrl+Shift+V` while using any Windows app → OHNO popup appears + clipboard text pasted
- [x] Translation triggers automatically after paste (500ms debounce via `textChanged`)
- [x] Empty clipboard → message shown, no crash
- [x] Non-text clipboard content (image) → handled gracefully (returns None)

### Notes
- `paste_clipboard()` calls `get_clipboard_text()` → if non-empty, calls `setPlainText()` which triggers `textChanged` → auto-translation
- Window is shown via `toggle()` if hidden/minimized before pasting

### Known Risks
| Risk | Mitigation |
|------|------------|
| `Ctrl+Shift+V` conflicts with some apps | Fully rebindable in Settings |
| Clipboard access denied by some security software | Document known issue; suggest rebinding |

---

## Phase 6 — Settings Panel

**Branch**: `feature/phases-4-7`
**Goal**: Full settings dialog — theme, autostart, live hotkey rebind.

### Tasks
- [x] `settings.py`: `SettingsDialog(QDialog)` modal with language, tone, theme, hotkeys, autostart
- [x] Default language pair: Source + Target dropdowns
- [x] Default tone: Formal / Casual / Literal dropdown
- [x] Theme: Light / Dark / System dropdown → apply QSS immediately on change
- [x] Start with Windows: checkbox → add/remove `HKCU\...\Run\OHNO` registry key via `winreg`
- [x] Hotkey text fields (toggle + clipboard) with live rebind on save
- [x] `hotkeys.py`: `rebind()` method — removes old hotkeys, registers new ones (no restart)
- [x] `window.py`: `set_hotkey_listener()` stores reference; `_apply_settings()` calls `rebind()`
- [x] Save / Cancel buttons; changes only apply on Save
- [x] Settings gear icon in title bar + tray menu opens this dialog

### Skipped (not needed for Google Translate backend)
- API Key field (no API key needed)
- Model selector (no Claude API)
- keyring integration (no secrets to store)

### Acceptance Criteria
- [x] All settings save correctly and persist across app restarts
- [x] Theme change applies immediately without restart
- [x] Hotkey rebind takes effect immediately after save
- [x] Start with Windows toggle creates/removes registry entry
- [x] Cancel discards all unsaved changes

### Notes
- Dark theme: `#1e293b` background, `#e2e8f0` text, `#334155` inputs, `#0f172a` title bar
- System theme checks `HKCU\Software\Microsoft\Windows\CurrentVersion\Themes\Personalize\AppsUseLightTheme`
- Autostart writes to `HKCU\Software\Microsoft\Windows\CurrentVersion\Run\OHNO`
- `HotkeyListener.rebind()` uses `keyboard.remove_hotkey()` + `keyboard.add_hotkey()` — no thread restart needed

### Known Risks
| Risk | Mitigation |
|------|------------|
| Registry write for autostart may require elevation | Uses `HKCU` (not HKLM) — no elevation needed |
| Invalid hotkey combo causes keyboard lib error | Graceful error handling in `rebind()` |

---

## Phase 7 — Packaging + Release

**Branch**: `feature/phases-4-7`
**Goal**: Single distributable `.exe`; README with install + setup instructions.

### Tasks
- [x] Create `icon.ico` from `assets/icon.png` via Pillow
- [x] Write `OHNO.spec` PyInstaller spec file with data files, hidden imports, no-console
- [x] Add `pyinstaller` to `requirements.txt`
- [x] Create `README.md`: what is OHNO, dev setup, build instructions, hotkeys
- [x] Create `CHANGELOG.md` with v1.0.0 entries

### Deferred
- [ ] Build + test `dist/OHNO.exe` on clean Windows VM
- [ ] Tag `v1.0.0` in git
- [ ] Create GitHub release with `.exe` attached

### Notes
- `OHNO.spec`: one-file mode, no console, icon.ico, hidden imports for `pyttsx3.drivers.sapi5` and `deep_translator`
- Excludes `tkinter`, `unittest`, `xmlrpc`, `pydoc` to reduce size

### Known Risks
| Risk | Mitigation |
|------|------------|
| PyInstaller antivirus false positive | Code-sign the exe; add note to README |
| `.exe` size > 100MB | Excluded unused Qt modules in spec |
| Missing DLLs on target machine | Test on clean VM without Python installed |

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Google Translate rate limits | Low | Medium | deep-translator handles retries |
| Hotkey conflicts with other installed apps | Medium | High | Fully rebindable in settings |
| PyInstaller antivirus false positive | Medium | Medium | Code-sign exe; document exception in README |
| pyttsx3 voice quality poor | Low | Low | Acceptable for MVP; note as known limitation |
| `keyboard` lib requires elevated privileges | Low | High | Tested in Phase 1; works without elevation |
| Windows version compatibility (10 vs 11) | Low | Medium | Test on both during packaging phase |

---

## Testing Approach

**MVP strategy: manual smoke test per phase** (no automated test suite for GUI MVP).

Each phase includes a checkbox acceptance criteria list above. Before merging a branch, all acceptance criteria must be manually verified.

### Automated UAT (User Acceptance Testing) — Required Per Phase

**Before presenting any phase to the user for testing**, Claude must perform its own UAT pass:

1. **Create test cases**: Write 3–5 concrete use cases covering the phase's acceptance criteria (e.g., "Type 'hello', wait 1s, verify translation appears in output")
2. **Launch the app**: Run the app via `python main.py` in the background
3. **Execute test cases programmatically where possible**: Use Python scripts or Qt test helpers to simulate user actions and verify outcomes
4. **Test edge cases**: Empty input, rapid clicking, long text, special characters, CJK text, window resize/minimize/restore
5. **Verify no crashes**: App must survive 30+ seconds of normal use without segfault or unhandled exception
6. **Check for regressions**: Re-test key features from prior phases (e.g., hotkey toggle, translation, copy/clear)
7. **Document results**: Log which tests passed/failed in a brief summary before handing off to the user

**Only present the feature to the user after all UAT tests pass.** If a test fails, fix the issue and re-run UAT before asking the user to test.

This applies to all phases, all projects — not just this one.

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

- **Google Translate via `deep_translator` is sufficient for MVP** — no API key management needed, simplifies settings and onboarding significantly
- **`keyboard.remove_hotkey()` + `add_hotkey()` works for live rebinding** — no need to restart the listener thread
- **`QSizeGrip` is the easiest way to add resize handles** to frameless windows — just add to bottom corners
- **`changeEvent(WindowDeactivate)` is better than `focusOutEvent`** for click-outside-to-dismiss — avoids false triggers from internal child widget focus changes
- **`windowFlags()` must be re-applied and window re-shown** when toggling `WindowStaysOnTopHint` — Qt requirement
- **Windows dark mode detection** via `HKCU\...\Themes\Personalize\AppsUseLightTheme` registry key works reliably

---

## Post-Release Feedback

*← Populated after launch.*

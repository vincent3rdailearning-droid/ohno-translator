# OHNO Translator — CLAUDE.md

## Project Overview
A PyQt6 desktop translation popup for Windows. Lives in the system tray; appears via `Ctrl+Shift+T`. Translates text using the Claude API with tone control (Formal / Casual / Literal). No backend — config persists to `%APPDATA%/OHNO/config.json`, API key stored in system keyring.

## Tech Stack
- **Python 3.11+** (3.14.3 in use)
- **PyQt6** — UI framework (widgets, tray, threads, signals)
- **anthropic** — Claude API client (`claude-haiku-4-5-20251001` default)
- **keyboard** — Global hotkey listener (background thread)
- **pyperclip** — Clipboard read/write
- **pyttsx3** — Text-to-speech (word lookup pronunciation)
- **keyring** — Secure API key storage (never written to disk)

## Key Files

| File | Purpose |
|------|---------|
| `ohno/main.py` | Entry point — QApplication, tray icon, hotkey wiring |
| `ohno/window.py` | Frameless popup QWidget — drag, resize, dismiss |
| `ohno/translation.py` | QThread worker + Claude API + debounce timer |
| `ohno/hotkeys.py` | Background hotkey listener, emits Qt signals |
| `ohno/config.py` | Config schema, defaults, load/save to AppData |
| `ohno/settings.py` | Settings QDialog |
| `ohno/word_lookup.py` | Selection detection, definition tooltip, TTS |
| `ohno/clipboard.py` | Clipboard integration helpers |
| `ohno/assets/icon.png` | Tray icon (32×32 PNG) |
| `requirements.txt` | All pip dependencies |
| `ImplementationPlan.md` | Phase tracker — always kept up to date |

## Dev Setup

```bash
# Activate venv (always use this Python, not system Python)
.venv\Scripts\activate

# Run the app
cd ohno
python main.py

# Install deps (after cloning fresh)
pip install -r requirements.txt
```

## Phase-Based Development Process

IMPORTANT: This project follows a strict phase-based workflow. After completing each phase:

1. **Verify all acceptance criteria** in `ImplementationPlan.md` for that phase pass
2. **Update `ImplementationPlan.md`** immediately:
   - Mark phase status as `✅ Complete` in the Phase Overview table
   - Check off all completed tasks with `[x]`
   - Check off all acceptance criteria with `[x]`
   - Add a `### Notes` section with any deviations, gotchas, or version notes
   - Update `**Current Phase**` at the top to point to the next phase
   - Mark the next phase as `🔄 Next` in the table
3. **Commit the updated `ImplementationPlan.md`** along with the phase code
4. **Merge the feature branch to `main`** before starting the next phase branch

**For parallel phases (Option B)**: Update `ImplementationPlan.md` as soon as each track (Agent A / Agent B) completes — do not wait for the integration step. Check off that track's tasks immediately when the agent reports done, then check off the integration tasks after that step finishes.

## Parallel Development Strategy

Some Phase 2+ tasks can be implemented by two agents simultaneously, cutting wall-clock time roughly in half.

**Safe to parallelize** (no shared file dependency):
- Standalone worker classes: `translation.py`, `word_lookup.py`
- Pure helper modules: `clipboard.py`, `config.py`
- Separate dialogs: `settings.py` (once window.py API is stable)

**NOT safe to parallelize** (shared file — must remain sequential):
- Anything that modifies `window.py` simultaneously
- Feature chains where Task B depends on Task A's output
- Integration steps that wire multiple modules together

### Option B — Backend-first parallelism (Phase 2 example)

When a phase contains standalone backend modules plus a shared UI integration step:

1. **Agent A** (background): implement the standalone worker (`translation.py`)
2. **Agent B** (background): implement the standalone helper (`clipboard.py`)
3. Launch both agents in the **same terminal** with `run_in_background: true` — shared context, auto-notification on completion, no extra setup needed
4. **Integration pass** (after both complete): wire both into `window.py` in a single sequential step

**Never** parallelize tasks that touch the same file. The integration step always remains sequential.

---

## Branch Naming
- `setup` — Phase 0
- `feature/tray-window` — Phase 1
- `feature/translation-core` — Phase 2
- `feature/ui-polish` — Phase 3
- `feature/word-lookup` — Phase 4
- `feature/clipboard` — Phase 5
- `feature/settings` — Phase 6
- `feature/packaging` — Phase 7
- `fix/[description]` — Bug fixes post-release

## Commit Style (Conventional Commits)
- `feat:` new feature
- `fix:` bug fix
- `chore:` deps, config, tooling
- `docs:` documentation only

## Key Conventions

**Thread safety**: All Claude API calls run in `QThread` subclasses. Use `pyqtSignal` to emit results back to the main thread — never update UI directly from a worker thread.

**Config**: Load via `config.load()` at startup. Save via `config.save(cfg)` on settings change. API key is NEVER in config — always use `keyring.get_password("ohno", "api_key")`.

**Hotkeys**: Registered in `HotkeyListener` (background thread). Add new hotkeys there; connect signals in `main.py`.

**Dismiss logic**: Window hides (not closes) on Escape / click-outside / tray toggle. App never quits unless Exit is chosen from tray menu.

## Common Issues

**Hotkey not firing** — `keyboard` lib may need admin on some Windows configs. Run as administrator if `Ctrl+Shift+T` doesn't work.

**Tray icon not appearing** — Icon must be a valid PNG. If blank, regenerate `assets/icon.png` using the PyQt6 snippet in Phase 0 notes.

**Qt crash from worker thread** — Never call UI methods directly from `QThread`. Always emit a signal and let the main thread handle the update.

**`keyboard.wait()` blocking stop** — Call `keyboard.unhook_all()` from `HotkeyListener.stop()` to unblock the listener thread cleanly.

## Additional Documentation
- `PRD.md` — Product requirements, goals, wireframe
- `TechSpec.md` — Architecture, file structure, config schema, error handling, packaging
- `ImplementationPlan.md` — Phase-by-phase task list with acceptance criteria and current status

# Changelog

## v1.0.0 — 2026-03-07

### Added
- System tray icon with left-click toggle and right-click context menu
- Frameless, draggable, resizable translator window with always-on-top pin
- Real-time translation via Google Translate (15+ languages)
- 500ms debounce to avoid excessive API calls
- Language swap button (swaps source/target language and text)
- Tone selector (Formal / Casual / Literal) — accepted but not yet used by backend
- Copy output and Clear buttons
- Global hotkey `Ctrl+Shift+T` to show/hide window
- Global hotkey `Ctrl+Shift+V` to paste clipboard and auto-translate
- Word lookup: select 1-3 words for definition popup with TTS pronunciation
- Translation history (last 10 entries)
- Settings dialog: language defaults, tone, theme, hotkey rebind, start with Windows
- Light / Dark / System theme with instant switching
- Start with Windows toggle (registry-based)
- Live hotkey rebinding (no restart needed)
- Minimize button and bring-to-front tray action
- Resize grips on both bottom corners
- Click-outside-to-dismiss (when unpinned)
- Escape key to hide window
- PyInstaller spec for single-file .exe packaging

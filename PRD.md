# PRD — OHNO Translator Plugin

**Project**: OHNO Translator
**Version**: 1.0 (MVP)
**Date**: 2026-02-28
**Status**: Pre-development — docs complete, coding not yet started

---

## 1. Overview

OHNO is a lightweight PyQt6 desktop translation popup for Windows. It lives in the system tray and appears instantly via a global hotkey (`Ctrl+Shift+T`), overlaying the user's current window. Users can type or paste text, select source/target languages and tone, and receive a translation powered by the Claude API — without switching apps or opening a browser.

---

## 2. Problem Statement

Professionals and daily users working across multiple languages (especially Chinese Traditional/Simplified, Japanese, and English) face constant friction when translating text:

- **Copy → browser tab → paste → read → switch back** is 5+ steps for a single phrase
- Browser translation tools lack tone control (formal vs. casual vs. literal)
- No quick word lookup with pronunciation while reading documents or code comments
- Clipboard workflows break focus and context

OHNO eliminates this friction: one hotkey, instant popup, translated output in under 1.5 seconds.

---

## 3. Goals / Non-Goals

### Goals
- Real-time translation with Claude API (500ms debounce)
- Tone-aware translation: Formal / Casual / Literal
- Word lookup with definition tooltip and voice pronunciation
- Clipboard integration via configurable hotkey
- Minimal footprint — runs silently in system tray, appears only on demand
- User-configurable hotkeys, language pairs, API key, and theme

### Non-Goals
- Mobile or web version
- Multi-user or cloud sync features
- Offline translation (requires internet + Claude API)
- Dictionary database (word lookup is Claude-powered, not a local dict)
- Translation memory / history persistence (MVP scope)

---

## 4. Target Users

| User Type | Description |
|-----------|-------------|
| Bilingual professionals | Work in English + Chinese (Traditional/Simplified) or Japanese daily |
| Translators / editors | Need fast, tone-controlled reference translations while working |
| Developers | Translate code comments, docs, error messages without leaving their IDE |
| Language learners | Quick lookup of words and phrases with pronunciation |

**Primary language pairs**: English ↔ Chinese Traditional, English ↔ Chinese Simplified, English ↔ Japanese, Chinese ↔ Japanese

---

## 5. Core Features

| Feature | Detail |
|---------|--------|
| **Popup Window** | `Ctrl+Shift+T` global hotkey; draggable, resizable; always-on-top toggle; dismiss via Escape or click-outside |
| **Translation Panel** | Source textarea + language dropdown; Tone selector (Formal / Casual / Literal); Swap (⇄) button; Output textarea (read-only) + Copy + Clear |
| **Real-time Translation** | 500ms debounce timer; Claude API with tone-aware system prompt; loading spinner during request; error message + retry on failure |
| **Word Lookup** | Highlight any word in source or output → definition tooltip appears; voice pronunciation button (OS TTS via pyttsx3) |
| **Clipboard Integration** | `Ctrl+Shift+V` hotkey (rebindable); auto-populates source field from clipboard contents |
| **System Tray** | Background daemon; left-click to toggle popup; right-click menu: Open / Settings / Exit |
| **Settings Panel** | Hotkey rebind; clipboard hotkey rebind; default language pair; default tone; Claude API key (secure via keyring); Light / Dark / System theme; Start with Windows toggle |

---

## 6. UI Wireframe (ASCII)

```
┌─────────────────────────────────────────────────┐
│  OHNO Translator                          [×] [■] │  ← frameless, draggable title bar
├─────────────────────────────────────────────────┤
│  From: [Chinese Traditional ▼]   [⇄]  To: [English ▼] │
├─────────────────────────────────────────────────┤
│  Tone: ( Formal )  ( Casual )  ( Literal )       │
├─────────────────────────────────────────────────┤
│  ┌───────────────────────────────────────────┐  │
│  │ Source text area                          │  │
│  │ (editable, multi-line)                    │  │
│  └───────────────────────────────────────────┘  │
│                                                   │
│  ┌───────────────────────────────────────────┐  │
│  │ Translation output (read-only)            │  │
│  │                                           │  │
│  └───────────────────────────────────────────┘  │
│                                                   │
│  [Copy Output]  [Clear]              [⚙ Settings]│
└─────────────────────────────────────────────────┘
```

**Word lookup tooltip** (appears on text selection):
```
  ┌─────────────────────────────┐
  │ 翻譯 (fān yì)               │
  │ n. Translation; the act of  │
  │    converting text between  │
  │    languages.               │
  │                   [▶ Speak] │
  └─────────────────────────────┘
```

---

## 7. Success Metrics

| Metric | Target |
|--------|--------|
| Translation latency | < 1.5 seconds (p90) for typical sentences |
| Window appearance time | < 200ms after hotkey press |
| Crash rate | Zero crashes in daily use (8+ hours background) |
| Hotkey reliability | Hotkey triggers 100% of the time when app is running |
| API key security | API key never written to disk in plaintext |
| Startup performance | Tray icon visible < 3 seconds after Windows login (if autostart enabled) |

---

## 8. Open Questions

None — all resolved during kickoff Q&A.

| Question | Resolution |
|----------|------------|
| Which translation API? | Claude API (`claude-haiku-4-5` default, swappable in settings) |
| Offline support? | No — MVP is API-only |
| History/memory? | No — out of scope for MVP |
| Multiple windows? | No — single popup, single instance |
| Linux/macOS? | No — Windows-only for MVP |
| Installer format? | PyInstaller → single `.exe` |

---

## 9. Milestones

Linked to `ImplementationPlan.md` phases:

| Milestone | Phase | Branch |
|-----------|-------|--------|
| Repo setup, venv, deps | Phase 0 | `setup` |
| System tray + hotkey popup | Phase 1 | `feature/tray-window` |
| Claude API translation working | Phase 2 | `feature/translation-core` |
| Full UI layout polished | Phase 3 | `feature/ui-polish` |
| Word lookup + TTS | Phase 4 | `feature/word-lookup` |
| Clipboard hotkey | Phase 5 | `feature/clipboard` |
| Settings panel + secure storage | Phase 6 | `feature/settings` |
| PyInstaller .exe + release | Phase 7 | `feature/packaging` |

---

## 10. Lessons Learned

*← Populated after development is complete.*

---

## 11. Post-Release Feedback

*← Populated after launch.*

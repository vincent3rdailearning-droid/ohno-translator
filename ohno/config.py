"""
config.py — Configuration schema, defaults, and load/save helpers.

Config file location: %APPDATA%/OHNO/config.json
API key is NOT stored here — it lives in keyring ("ohno", "api_key").
"""

import json
import os
from pathlib import Path

# ---------------------------------------------------------------------------
# Schema & defaults
# ---------------------------------------------------------------------------

DEFAULTS: dict = {
    "hotkey": "ctrl+shift+t",
    "clipboard_hotkey": "ctrl+shift+v",
    "default_source_lang": "zh-TW",
    "default_target_lang": "en",
    "default_tone": "formal",
    "theme": "system",
    "start_with_windows": False,
    "model": "claude-haiku-4-5-20251001",
}


def _config_path() -> Path:
    """Return path to config.json, creating the parent directory if needed."""
    appdata = os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming")
    config_dir = Path(appdata) / "OHNO"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir / "config.json"


def load() -> dict:
    """Load config from disk, filling missing keys with defaults."""
    path = _config_path()
    config = dict(DEFAULTS)
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                stored = json.load(f)
            config.update({k: v for k, v in stored.items() if k in DEFAULTS})
        except (json.JSONDecodeError, OSError):
            pass  # Corrupted file — fall back to defaults
    return config


def save(config: dict) -> None:
    """Persist config dict to disk. Only known keys are written."""
    path = _config_path()
    safe = {k: config[k] for k in DEFAULTS if k in config}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(safe, f, indent=2)


# ---------------------------------------------------------------------------
# Smoke-test helper (called directly: python config.py)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    cfg = load()
    print(f"Config loaded from: {_config_path()}")
    print(json.dumps(cfg, indent=2))
    save(cfg)
    print("Config saved OK.")

# languages.py — Shared language code/name mapping.

LANGUAGES: dict[str, str] = {
    "zh-TW": "Chinese (Traditional)",
    "zh-CN": "Chinese (Simplified)",
    "ja":    "Japanese",
    "en":    "English",
    "ko":    "Korean",
    "fr":    "French",
    "de":    "German",
    "es":    "Spanish",
}

# Reverse lookup: display name -> code
_NAME_TO_CODE: dict[str, str] = {v: k for k, v in LANGUAGES.items()}

# Ordered list of display names (stable iteration order)
LANG_NAMES: list[str] = list(LANGUAGES.values())


def display_name_for_code(code: str) -> str:
    """Return the display name for a language code, or the code itself as fallback."""
    return LANGUAGES.get(code, code)

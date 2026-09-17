from __future__ import annotations

from hancock.prompts import MODES, SYSTEMS

VALID_MODES = set(MODES)


def normalize_mode(mode: str | None, default: str = "auto") -> str:
    if not mode:
        return default
    m = mode.strip().lower()
    return m if m in VALID_MODES else default


def system_prompt(mode: str | None) -> str:
    return SYSTEMS[normalize_mode(mode)]

from hancock.modes import normalize_mode, system_prompt
from hancock.prompts import SYSTEMS


def test_normalize_mode():
    assert normalize_mode("PENTEST") == "pentest"
    assert normalize_mode("nope") == "auto"
    assert normalize_mode(None) == "auto"


def test_all_modes_have_prompts():
    for mode in SYSTEMS:
        assert "Hancock" in system_prompt(mode) or "Hancock" in SYSTEMS[mode]

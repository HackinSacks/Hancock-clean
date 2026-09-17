import pytest

from hancock.tools.nmap_wrapper import run_nmap


def test_rejects_empty_target():
    with pytest.raises(ValueError):
        run_nmap("")


def test_rejects_bad_target():
    with pytest.raises(ValueError):
        run_nmap("evil; rm -rf /")


def test_rejects_bad_flag():
    with pytest.raises(ValueError):
        run_nmap("127.0.0.1", extra_flags=["--script=vuln"])

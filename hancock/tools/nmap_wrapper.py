"""Allowlisted nmap wrapper — explicit target required; never auto-invoked."""

from __future__ import annotations

import re
import shutil
import subprocess
from typing import Sequence

_SAFE_TARGET = re.compile(r"^[A-Za-z0-9_.:\-]+$")
_ALLOWED_FLAGS = {
    "-sV", "-sS", "-sT", "-Pn", "-T2", "-T3", "-T4", "-F", "-p-",
}


def run_nmap(target: str, extra_flags: Sequence[str] | None = None, timeout: int = 120) -> str:
    if not target or not _SAFE_TARGET.match(target):
        raise ValueError("invalid or missing target")
    flags: list[str] = []
    for f in extra_flags or ("-sV", "-T3"):
        if f.startswith("-p") and re.fullmatch(r"-p[0-9,\-]+", f):
            flags.append(f)
            continue
        if f not in _ALLOWED_FLAGS:
            raise ValueError(f"flag not allowlisted: {f}")
        flags.append(f)
    if not shutil.which("nmap"):
        raise RuntimeError("nmap binary not found on PATH")
    cmd = ["nmap", *flags, target]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)
    out = (proc.stdout or "") + (proc.stderr or "")
    if proc.returncode != 0:
        raise RuntimeError(f"nmap exited {proc.returncode}: {out[:500]}")
    return out

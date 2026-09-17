#!/usr/bin/env python3
"""Build data/hancock_v1.jsonl from MITRE ATT&CK + static cybersecurity Q&A (Mistral instruct)."""

from __future__ import annotations

import argparse
import json
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
MITRE_URL = "https://raw.githubusercontent.com/mitre/cti/master/enterprise-attack/enterprise-attack.json"

STATIC_QA = [
    {
        "q": "What is the PICERL incident response model?",
        "a": "PICERL: Prepare, Identify, Contain, Eradicate, Recover, Lessons Learned. It structures IR from readiness through post-incident improvement (aligned with NIST SP 800-61 practices).",
    },
    {
        "q": "How should a SOC analyst triage a Mimikatz detection on a domain controller?",
        "a": "Treat as CRITICAL true-positive until proven otherwise. Isolate/contain DC network paths if policy allows, collect volatile evidence, reset affected credentials including krbtgt (double rotation per AD guidance), hunt for lateral movement (T1003/T1078), and open a formal IR ticket.",
    },
    {
        "q": "Write a high-level authorized nmap service scan approach.",
        "a": "Only with written authorization and RoE. Prefer non-destructive flags (e.g. -sV -T3 -Pn on in-scope hosts), document scope/exclusions, rate-limit, and never scan third-party infrastructure. Hancock never auto-scans.",
    },
    {
        "q": "What is a Sigma rule used for?",
        "a": "Sigma is a generic detection signature format that describes log-based detections in YAML and can be converted to SIEM-specific queries (SPL, KQL, etc.).",
    },
    {
        "q": "What is YARA used for?",
        "a": "YARA matches textual/binary patterns to identify malware families and suspicious artefacts in files or memory.",
    },
    {
        "q": "Map credential dumping to MITRE ATT&CK.",
        "a": "Credential dumping is primarily T1003 (OS Credential Dumping) with common sub-techniques like LSASS memory (T1003.001). Often chained with Valid Accounts (T1078).",
    },
    {
        "q": "What should a CISO include in a board cyber risk summary?",
        "a": "Top residual risks with business impact, KRIs/KPIs vs appetite, material incidents, control gaps mapped to NIST CSF/ISO 27001, remediation owners/dates, and budget implications — concise and jargon-light.",
    },
    {
        "q": "Authorized engagement rule for Hancock pentest mode?",
        "a": "Hancock assists only within authorized scope/RoE, confirms authorization before active techniques, does not auto-scan, and never handles wallets or private keys.",
    },
]


def mistral_messages(user: str, assistant: str, system: str | None = None) -> dict:
    msgs = []
    if system:
        msgs.append({"role": "system", "content": system})
    msgs.append({"role": "user", "content": user})
    msgs.append({"role": "assistant", "content": assistant})
    return {"messages": msgs}


def download_mitre(path: Path) -> dict:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.stat().st_size > 1000:
        print(f"[pipeline] using cached {path}")
        return json.loads(path.read_text(encoding="utf-8"))
    print(f"[pipeline] downloading MITRE ATT&CK from {MITRE_URL}")
    with urllib.request.urlopen(MITRE_URL, timeout=120) as resp:  # noqa: S310
        data = resp.read()
    path.write_bytes(data)
    return json.loads(data.decode("utf-8"))


def techniques_from_mitre(bundle: dict) -> list[dict]:
    out = []
    for obj in bundle.get("objects", []):
        if obj.get("type") != "attack-pattern":
            continue
        if obj.get("revoked") or obj.get("x_mitre_deprecated"):
            continue
        ext_ids = [
            x.get("external_id")
            for x in obj.get("external_references", [])
            if x.get("source_name") == "mitre-attack" and x.get("external_id")
        ]
        if not ext_ids:
            continue
        tid = ext_ids[0]
        name = obj.get("name") or tid
        desc = (obj.get("description") or "").strip()
        if len(desc) > 1200:
            desc = desc[:1200] + "…"
        tactics = []
        for phase in obj.get("kill_chain_phases", []) or []:
            if phase.get("kill_chain_name") == "mitre-attack":
                tactics.append(phase.get("phase_name"))
        out.append({"id": tid, "name": name, "description": desc, "tactics": tactics})
    return out


def build_samples(techniques: list[dict]) -> list[dict]:
    samples: list[dict] = []
    sys_soc = "You are Hancock, CyberViser's SOC/pentest specialist. Be accurate and concise."
    for qa in STATIC_QA:
        samples.append(mistral_messages(qa["q"], qa["a"], sys_soc))
    for t in techniques:
        tactics = ", ".join(t["tactics"]) if t["tactics"] else "n/a"
        q = f"Explain MITRE ATT&CK technique {t['id']} ({t['name']}) and typical detections."
        a = (
            f"{t['id']} — {t['name']}.\n"
            f"Tactics: {tactics}.\n"
            f"Description: {t['description'] or 'See ATT&CK for full text.'}\n"
            f"Defenders should map telemetry to this technique, write detections (Sigma/KQL/SPL), "
            f"and validate in authorized lab/purple-team exercises."
        )
        samples.append(mistral_messages(q, a, sys_soc))
        q2 = f"What ATT&CK ID covers: {t['name']}?"
        a2 = f"{t['id']} ({t['name']}) under tactics: {tactics}."
        samples.append(mistral_messages(q2, a2, sys_soc))
    return samples


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=DATA / "hancock_v1.jsonl")
    ap.add_argument("--mitre-cache", type=Path, default=DATA / "enterprise-attack.json")
    ap.add_argument("--max-techniques", type=int, default=0, help="0 = all")
    args = ap.parse_args(argv)
    DATA.mkdir(parents=True, exist_ok=True)
    bundle = download_mitre(args.mitre_cache)
    techniques = techniques_from_mitre(bundle)
    if args.max_techniques > 0:
        techniques = techniques[: args.max_techniques]
    samples = build_samples(techniques)
    with args.out.open("w", encoding="utf-8") as fh:
        for s in samples:
            fh.write(json.dumps(s, ensure_ascii=False) + "\n")
    print(f"[pipeline] wrote {len(samples)} samples -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

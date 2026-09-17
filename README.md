# Hancock — CyberViser AI Security Co-Pilot (clean rewrite)

Lean FastAPI package for Johnny Watters / 0ai-Cyberviser. Not a dump of the 250k-line notebook tree.

Reference (read-only): https://github.com/0ai-Cyberviser/Hancock · Docs site: https://cyberviser.github.io/Hancock/

## Layout

```
hancock/          # package (CLI, API, backends, modes, tools)
training/         # dataset pipeline + QLoRA scripts
data/             # JSONL datasets (generated)
tests/
```

## Quick start (Kali WSL2)

```bash
cd /root/hancock
python3 -m venv .venv && source .venv/bin/activate
pip install -U pip && pip install -r requirements.txt && pip install -e .
cp .env.example .env

# Ollama (if missing): curl -fsSL https://ollama.com/install.sh | sh
ollama serve &          # if not already running
ollama pull llama3.1:8b # or mistral:7b for ~12GB VRAM comfort

python -m hancock --server
# curl http://127.0.0.1:5000/health
```

Windows PowerShell helper (writes a script, then runs it in Kali):

```powershell
wsl -d kali-linux -u root -- bash /root/hancock/scripts/bootstrap_kali.sh
```

## API

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` | status |
| GET | `/metrics` | Prometheus |
| POST | `/v1/chat` | conversational (`mode`) |
| POST | `/v1/ask` | single-shot |
| POST | `/v1/triage` | SOC triage |
| POST | `/v1/hunt` | hunting queries |
| POST | `/v1/respond` | PICERL IR |
| POST | `/v1/code` | security code |
| POST | `/v1/ciso` | exec/risk |
| POST | `/v1/sigma` | Sigma rules |
| POST | `/v1/yara` | YARA rules |
| POST | `/v1/ioc` | IOC enrichment |
| POST | `/v1/webhook` | SIEM push |

Modes: `pentest|soc|auto|code|ciso|sigma|yara|ioc`  
Backend: `HANCOCK_LLM_BACKEND=ollama|nvidia|openai` (default `ollama`)

## Safety

- Pentest prompts require **authorized engagement only**
- No auto-scanning; `hancock.tools.nmap_wrapper` runs only when explicitly called with a target
- No private keys / wallet features

## QLoRA fine-tune (RTX 5070 ~12GB)

```bash
source .venv/bin/activate
pip install -r requirements-train.txt

# Mistral-7B-Instruct-v0.3 may be gated — login first:
# huggingface-cli login
# or: export HF_TOKEN=hf_...

python -m training.pipeline          # -> data/hancock_v1.jsonl
python -m training.finetune_tiny_debug   # smoke test (tiny model)
# Full run (hours) — start in tmux/screen:
python -m training.finetune_qlora    # -> outputs/hancock-lora
```

### RTX 5070 / Blackwell (sm_120) note

Stable PyTorch CUDA wheels may lack sm_120. If `torch.cuda.is_available()` is false or you see
`CUDA error: no kernel image`, install a **nightly** CUDA build from https://pytorch.org and retry.
bitsandbytes must also match that CUDA major.

Monitor training:

```bash
tail -f outputs/hancock-lora/train.log
nvidia-smi -l 5
```

## License

Apache-2.0 — see `LICENSE`.

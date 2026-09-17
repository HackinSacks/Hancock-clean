#!/usr/bin/env bash
# Bootstrap Hancock on Kali WSL2 (run as root): bash /root/hancock/scripts/bootstrap_kali.sh
set -euo pipefail
HANCOCK_ROOT="${HANCOCK_ROOT:-/root/hancock}"
REF_ROOT="${REF_ROOT:-/root/hancock-ref}"

echo "[bootstrap] Hancock root: $HANCOCK_ROOT"
mkdir -p "$HANCOCK_ROOT"

if [[ ! -f "$HANCOCK_ROOT/pyproject.toml" ]]; then
  echo "[bootstrap] ERROR: project files missing at $HANCOCK_ROOT"
  echo "  Sync from GitHub branch clean-rewrite or copy the package tree first."
  exit 1
fi

if [[ ! -d "$REF_ROOT/.git" ]]; then
  echo "[bootstrap] cloning read-only reference to $REF_ROOT"
  git clone --depth 1 https://github.com/0ai-Cyberviser/Hancock.git "$REF_ROOT" || true
fi

export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y python3 python3-venv python3-pip curl ca-certificates git nmap || true

if ! command -v ollama >/dev/null 2>&1; then
  echo "[bootstrap] installing Ollama"
  curl -fsSL https://ollama.com/install.sh | sh
fi

if ! curl -sf http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
  echo "[bootstrap] starting ollama serve in background"
  nohup ollama serve >/var/log/ollama-hancock.log 2>&1 &
  sleep 3
fi

echo "[bootstrap] pulling chat model (llama3.1:8b preferred)"
ollama pull llama3.1:8b || ollama pull mistral:7b || echo "[bootstrap] model pull failed (network?)"

cd "$HANCOCK_ROOT"
python3 -m venv .venv
.venv/bin/pip install -U pip
.venv/bin/pip install -r requirements.txt
.venv/bin/pip install -e .
[[ -f .env ]] || cp .env.example .env

echo "[bootstrap] pytest"
.venv/bin/pytest -q || true

echo "[bootstrap] starting API briefly for /health"
.venv/bin/python -m hancock --server --host 127.0.0.1 --port 5000 >/tmp/hancock-api.log 2>&1 &
API_PID=$!
sleep 2
curl -sf http://127.0.0.1:5000/health || (echo "[bootstrap] health failed"; tail -50 /tmp/hancock-api.log; kill $API_PID; exit 1)
kill $API_PID || true

echo "[bootstrap] building dataset (MITRE download)"
.venv/bin/python -m training.pipeline || echo "[bootstrap] dataset build failed (network?)"

echo "[bootstrap] DONE"
echo "  cd $HANCOCK_ROOT && source .venv/bin/activate"
echo "  python -m hancock --server"
echo "  # train: pip install -r requirements-train.txt && python -m training.finetune_qlora"

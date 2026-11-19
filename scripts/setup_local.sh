#!/usr/bin/env bash
# One-command local setup (macOS / Linux / WSL): Python env, local LLMs, index, smoke test.
# Usage:  bash scripts/setup_local.sh            # generator qwen3:4b + judge gemma3:4b
#         GEN_MODEL=qwen3:8b bash scripts/setup_local.sh
set -euo pipefail
GEN_MODEL="${GEN_MODEL:-qwen3:4b}"
JUDGE_MODEL="${JUDGE_MODEL:-gemma3:4b}"
cd "$(dirname "$0")/.."

say() { printf '\n\033[1m==> %s\033[0m\n' "$*"; }

say "1/6 uv (Python package manager)"
if ! command -v uv >/dev/null 2>&1; then
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
fi
uv --version

say "2/6 Python dependencies (CPU-only torch; first run downloads ~1 GB)"
uv sync --frozen

say "3/6 Ollama (local LLM runtime)"
if ! command -v ollama >/dev/null 2>&1; then
  if [[ "$(uname)" == "Darwin" ]]; then
    echo "Install Ollama for macOS from https://ollama.com/download (or: brew install ollama), then re-run."
    exit 1
  fi
  curl -fsSL https://ollama.com/install.sh | sh
fi
if ! curl -fsS http://localhost:11434/api/version >/dev/null 2>&1; then
  echo "Starting ollama serve in the background (log: /tmp/ollama.log)"
  nohup ollama serve >/tmp/ollama.log 2>&1 &
  for _ in $(seq 1 30); do curl -fsS http://localhost:11434/api/version >/dev/null 2>&1 && break; sleep 1; done
fi

say "4/6 Models: generator=$GEN_MODEL judge=$JUDGE_MODEL (~2.5 GB + ~3 GB)"
ollama pull "$GEN_MODEL"
ollama pull "$JUDGE_MODEL"

say "5/6 .env and index"
[[ -f .env ]] || cp .env.example .env
uv run python -m regnav.cli ingest --config configs/local_stratified.yaml

say "6/6 Smoke test (one question; ~1-3 min on CPU)"
uv run python -m regnav.cli ask --config configs/local_stratified.yaml --model "$GEN_MODEL" --sector bank \
  "What do we need to do before engaging a third-party AI vendor?"

cat <<MSG

Done. Next:
  make ask Q="your question" SECTOR=insurer
  make app                       # Streamlit UI on http://localhost:8501
  make eval CONFIG=configs/hybrid_stratified.yaml   # needs data/eval/questions.jsonl
Optional: add Langfuse keys to .env for tracing.
MSG

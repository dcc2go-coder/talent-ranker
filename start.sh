#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Talent Ranker — AI Resume Screening"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Create virtual environment if missing
if [ ! -d ".venv" ]; then
  echo "→ Creating Python environment (one-time setup)…"
  python3 -m venv .venv
fi

source .venv/bin/activate

echo "→ Installing dependencies…"
pip install -q -r requirements.txt

if [ ! -f ".env" ]; then
  cp .env.example .env
  echo ""
  echo "  ⚠  No API key found yet."
  echo "     Open http://localhost:8000 and click Settings"
  echo "     to paste your OpenAI API key."
  echo ""
fi

PORT="${PORT:-8000}"
echo "→ Starting server at http://localhost:${PORT}"
echo "  Press Ctrl+C to stop."
echo ""

# Open browser on macOS
if [[ "$(uname)" == "Darwin" ]]; then
  (sleep 1.5 && open "http://localhost:${PORT}") &
fi

exec uvicorn app.main:app --host 127.0.0.1 --port "$PORT" --reload
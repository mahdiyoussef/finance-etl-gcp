#!/usr/bin/env bash
# run_local_demo.sh — Run the full local Finance ETL demo pipeline.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "==> Finance ETL Local Demo"
echo "    Project root: $PROJECT_ROOT"
echo ""

cd "$PROJECT_ROOT"

PYTHON="${PYTHON:-python3}"

echo "==> Step 1: Running pipeline..."
PYTHONPATH=. $PYTHON -m pipeline run --output data/demo --customers 25 --invoices 100

echo ""
echo "==> Step 2: Running tests..."
PYTHONPATH=. $PYTHON -m pytest tests/ -v

echo ""
echo "==> Demo complete. Outputs in data/demo/"
ls -lh data/demo/marts/ 2>/dev/null || true


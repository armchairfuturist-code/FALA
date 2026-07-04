#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

echo "=== ruff ==="
.venv/bin/ruff check .
echo ""

echo "=== ruff format check ==="
.venv/bin/ruff format --check .
echo ""

echo "=== mypy ==="
.venv/bin/mypy . 2>&1 || true
echo ""

echo "OK"

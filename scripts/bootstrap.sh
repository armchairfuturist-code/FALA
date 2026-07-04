#!/usr/bin/env bash
# FALA development environment bootstrap
# Run: source scripts/bootstrap.sh

set -e

cd "$(dirname "$0")/.."

if [ ! -d .venv ]; then
    echo "Creating virtualenv..."
    python -m venv .venv
fi

echo "Installing runtime deps..."
.venv/bin/pip install -r requirements.txt

echo "Installing dev deps..."
.venv/bin/pip install -r requirements-dev.txt

echo ""
echo "Done! Activate with:  source .venv/bin/activate"
echo "Or run directly:      .venv/bin/python fala.py"

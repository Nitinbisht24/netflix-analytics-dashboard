#!/usr/bin/env bash
# Convenience launcher: creates a venv on first run, installs deps, starts the app.
set -e

cd "$(dirname "$0")"

if [ ! -d "venv" ]; then
    echo "Creating virtual environment…"
    python3 -m venv venv
fi

# shellcheck disable=SC1091
source venv/bin/activate

echo "Installing dependencies…"
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt

echo "Starting Netflix Analytics Pro on http://localhost:${PORT:-5000} …"
python app.py

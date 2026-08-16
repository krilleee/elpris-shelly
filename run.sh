#!/bin/sh
# Kör run.py med projektets venv, oavsett var du står i filsystemet.
set -e
cd "$(dirname "$0")"

if [ ! -x .venv/bin/python ]; then
    echo "Ingen venv hittad – skapar .venv och installerar beroenden..."
    python3 -m venv .venv
    .venv/bin/pip install -q -r requirements.txt
fi

exec .venv/bin/python run.py "$@"

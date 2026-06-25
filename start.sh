#!/usr/bin/env bash
# dwyt — start the Download YouTube to MP3 web app
cd "$(dirname "$0")"
echo "🚀 dwyt arrancando en http://localhost:5000"
exec "$(dirname "$0")/.venv/bin/python3" app.py

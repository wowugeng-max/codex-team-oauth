#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

UI_URL="http://127.0.0.1:8765"

echo "Starting Codex Team OAuth UI..."
echo "Project: $SCRIPT_DIR"
echo "URL: $UI_URL"
echo
echo "Close this Terminal window or press Ctrl+C to stop the UI server."
echo

(sleep 1; open "$UI_URL") &
python3 ui_server.py --host 127.0.0.1 --port 8765

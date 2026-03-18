#!/bin/sh
# Refresh cron data every 30 seconds.
# Re-reads jobs.json and run history, writes opencron-data.json to canvas dir.
# Run as: nohup sh skills/opencron/watch_sync.sh &
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
while true; do
    python3 "$SCRIPT_DIR/update_canvas.py" --sync 2>/dev/null
    sleep 30
done

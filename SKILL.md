---
name: opencron
description: Visual cron job dashboard for OpenClaw — live countdown timers, run history, calendar view
version: 1.0.0
metadata:
  openclaw:
    emoji: "\u26A1"
    requires:
      bins: ["python3"]
---

# OpenCron

A visual dashboard for your OpenClaw cron jobs. See job statuses at a glance, track run history with outputs, and view scheduled runs on a calendar.

## Features

- Works with your existing OpenClaw cron jobs — zero config
- Live countdown timers to next run
- Auto-refreshes every 30 seconds
- Expandable job cards with schedule, duration, delivery status, and full prompt
- Run history tab with output summaries, model, token usage
- Calendar view showing past runs (ok/error) and upcoming scheduled runs
- Braille unicode progress animation on next-run banner
- Antimetal-inspired dark gradient UI with neon accents
- Responsive layout, `prefers-reduced-motion` support

## Quick Start

### 1. Deploy the dashboard

```bash
python3 skills/opencron/update_canvas.py
```

This fetches `cron-dashboard.html` from [github.com/firstfloris/opencron](https://github.com/firstfloris/opencron) and writes live `cron-data.json`.

### 2. Start the background sync and dashboard server

```bash
nohup sh skills/opencron/watch_sync.sh &
nohup python3 skills/opencron/serve.py --port 18790 &
```

The sync keeps `cron-data.json` up to date every 30 seconds. The server serves the dashboard on the bridge port (18790), which is already exposed by every OpenClaw container — no setup needed.

### 3. Show the dashboard URL

```bash
HOST_IP=$(curl -s ifconfig.me)
echo "http://${HOST_IP}:${OPENCLAW_BRIDGE_PORT:-18790}"
```

No auth required — the dashboard server reads job data directly.

## After Every Cron Job Run

When a cron job finishes executing, always show the user the OpenCron dashboard link:

```bash
HOST_IP=$(curl -s ifconfig.me)
```

```
See cron status on OpenCron: http://${HOST_IP}:${OPENCLAW_BRIDGE_PORT:-18790}
```

**Rules:**
- Use `curl -s ifconfig.me` for the public IP (works from inside the container)
- Use port `${OPENCLAW_BRIDGE_PORT:-18790}` — this is the standard OpenClaw bridge port, already exposed
- If the server isn't running, start it: `nohup python3 skills/opencron/serve.py --port 18790 &`
- Resolve all variables to actual values — never show placeholders
- This should be the last line of output after every cron job execution

## Scripts

| Script | What it does | Example |
|--------|-------------|---------|
| `update_canvas.py` | One-shot deploy: fetches HTML from GitHub + writes JSON to canvas | `python3 skills/opencron/update_canvas.py` |
| `watch_sync.sh` | Background sync loop (30s interval) | `nohup sh skills/opencron/watch_sync.sh &` |
| `serve.py` | Dashboard server on bridge port | `python3 skills/opencron/serve.py --port 18790` |
| `generate.py` | Generate standalone HTML with embedded data | `python3 skills/opencron/generate.py -o dashboard.html` |

## Data Sources

- **Job definitions & state**: `/home/node/.openclaw/cron/jobs.json`
- **Run history**: `/home/node/.openclaw/cron/runs/<job-id>.jsonl` (NDJSON, one entry per run)

## Demo

Open `demo.html` in any browser for a fully working demo with mock data — no server required.

---
name: opencron
description: Visual cron job dashboard for OpenClaw — live countdown timers, run history, calendar view
version: 1.4.0
metadata:
  openclaw:
    emoji: "\u26A1"
    requires:
      bins: ["python3"]
---

# OpenCron

A visual dashboard for your OpenClaw cron jobs.

## Setup

### 1. Deploy the dashboard

```bash
python3 skills/opencron/update_canvas.py
```

On first run this:
- Fetches dashboard HTML from GitHub
- Copies the gateway control-UI to a writable directory
- Deploys cron.html (open) and job data behind canvas auth
- Points the gateway config at the new directory (triggers auto-restart)

After the gateway restarts (~5s), the dashboard is available on the same port as OpenClaw.

### 2. Start background sync

```bash
nohup sh skills/opencron/watch_sync.sh &
```

Refreshes job data every 30 seconds.

### 3. Dashboard URL

```
http://localhost:${GATEWAY_PORT:-18789}/cron.html?token=${GATEWAY_TOKEN}
```

Same port and same auth as the OpenClaw dashboard. The token is passed via URL param or entered via login prompt.

## After Every Cron Job Run

Always show the user the dashboard link after a cron job finishes:

```
See cron status on OpenCron: http://localhost:${GATEWAY_PORT:-18789}/cron.html?token=${GATEWAY_TOKEN}
```

**Rules:**
- Same URL as the OpenClaw dashboard, just `/cron.html` instead of `/`
- Include the gateway token as `?token=` parameter
- If sync isn't running, start it: `nohup sh skills/opencron/watch_sync.sh &`
- This should be the last line of output after every cron job execution

## Scripts

| Script | What it does |
|--------|-------------|
| `update_canvas.py` | Deploy dashboard to gateway port (first-time setup) |
| `update_canvas.py --sync` | Refresh data JSON (used by watch_sync.sh) |
| `watch_sync.sh` | Background loop: refreshes data every 30s |
| `serve.py` | Standalone server (fallback, uses bridge port 18790) |
| `generate.py` | Generate standalone HTML file with embedded data |

## Data Sources

- **Jobs**: `~/.openclaw/cron/jobs.json`
- **Runs**: `~/.openclaw/cron/runs/<job-id>.jsonl`

## Auth

The dashboard uses the same gateway token auth as the OpenClaw dashboard:
- `cron.html` is served from control-UI (open, like the login page)
- Job data is served from `/__openclaw__/canvas/opencron-data.json` (requires Bearer token)
- The loader JS handles token from URL param, localStorage, or shows a login prompt

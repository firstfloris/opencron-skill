---
name: opencron
description: Visual cron job dashboard for OpenClaw — live countdown timers, run history, calendar view
version: 1.3.0
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
- Embeds live job data and run history into the HTML
- Points the gateway config at the new directory (triggers auto-restart)

After the gateway restarts (~5s), the dashboard is available on the same port as OpenClaw.

### 2. Start background sync

```bash
nohup sh skills/opencron/watch_sync.sh &
```

Re-embeds fresh data every 30 seconds.

### 3. Dashboard URL

```
http://localhost:${GATEWAY_PORT:-18789}/cron.html
```

Same port as the OpenClaw dashboard — no extra setup, no extra auth.

## After Every Cron Job Run

Always show the user the dashboard link after a cron job finishes:

```
See cron status on OpenCron: http://localhost:${GATEWAY_PORT:-18789}/cron.html
```

**Rules:**
- Same URL as the OpenClaw dashboard, just `/cron.html` instead of `/`
- If sync isn't running, start it: `nohup sh skills/opencron/watch_sync.sh &`
- This should be the last line of output after every cron job execution

## Scripts

| Script | What it does |
|--------|-------------|
| `update_canvas.py` | Deploy dashboard to gateway port (first-time setup + data embed) |
| `update_canvas.py --sync` | Re-embed fresh data (used by watch_sync.sh) |
| `watch_sync.sh` | Background loop: re-embeds data every 30s |
| `serve.py` | Standalone server (fallback, uses bridge port 18790) |
| `generate.py` | Generate standalone HTML file with embedded data |

## Data Sources

- **Jobs**: `~/.openclaw/cron/jobs.json`
- **Runs**: `~/.openclaw/cron/runs/<job-id>.jsonl`

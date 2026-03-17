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
- Secure: gateway token auth, no credentials exposed client-side
- Responsive layout, `prefers-reduced-motion` support

## Quick Start

### 1. Deploy the dashboard

```bash
python3 skills/opencron/update_canvas.py
```

This fetches `cron-dashboard.html` from [github.com/firstfloris/opencron](https://github.com/firstfloris/opencron) and writes live `cron-data.json`.

### 2. Start the background sync

```bash
nohup sh skills/opencron/watch_sync.sh &
```

Keeps `cron-data.json` in sync with `jobs.json` every 30 seconds.

### 3. Open the dashboard

Get the public IP and detect which port the dashboard is on:

```bash
HOST_IP=$(curl -s ifconfig.me)
CRON_PORT=${CANVAS_PORT:-8090}
curl -sf "http://127.0.0.1:${CRON_PORT}/cron.html" > /dev/null 2>&1 || CRON_PORT=18789
```

Dashboard URL:

```
http://${HOST_IP}:${CRON_PORT}/cron.html?token=${OPENCLAW_GATEWAY_TOKEN}
```

**Important:** Never use `hostname -I` — that returns the container's internal IP which is unreachable from outside.

## Scripts

| Script | What it does | Example |
|--------|-------------|---------|
| `update_canvas.py` | One-shot deploy: fetches HTML from GitHub + writes JSON to canvas | `python3 skills/opencron/update_canvas.py` |
| `watch_sync.sh` | Background sync loop (30s interval) | `nohup sh skills/opencron/watch_sync.sh &` |
| `generate.py` | Generate standalone HTML with embedded data | `python3 skills/opencron/generate.py -o dashboard.html` |
| `serve.py` | Run a local HTTP server for the dashboard | `python3 skills/opencron/serve.py --port 8787` |

## Serving Externally (Optional)

To access the dashboard from outside Docker, add an nginx reverse proxy. See `nginx-canvas.conf.template` for a production-ready config with:

- Token validation via query parameter
- Rate limiting (10 req/s per IP)
- GET/HEAD only
- Path allowlisting
- Security headers (CSP, X-Frame-Options, no-referrer)
- Run log JSONL serving from `/runs/`

### Docker Compose snippet

```yaml
canvas-proxy:
  image: nginx:alpine
  restart: unless-stopped
  environment:
    OPENCLAW_GATEWAY_TOKEN: ${OPENCLAW_GATEWAY_TOKEN}
  volumes:
    - ./nginx-canvas.conf.template:/etc/nginx/templates/default.conf.template:ro
    - ./cron/runs:/openclaw-data/cron/runs:ro
  ports:
    - "127.0.0.1:${CANVAS_PORT:-8090}:80"
  depends_on:
    openclaw-gateway:
      condition: service_healthy
```

## Data Sources

- **Job definitions & state**: `/home/node/.openclaw/cron/jobs.json` (read by gateway as `cron-data.json`)
- **Run history**: `/home/node/.openclaw/cron/runs/<job-id>.jsonl` (NDJSON, one entry per run)

## After Every Cron Job Run

When a cron job finishes executing, always show the user the OpenCron dashboard link. Detect the correct port and public IP:

```bash
HOST_IP=$(curl -s ifconfig.me)
CRON_PORT=${CANVAS_PORT:-8090}
curl -sf "http://127.0.0.1:${CRON_PORT}/cron.html" > /dev/null 2>&1 || CRON_PORT=18789
```

Then show:

```
See cron status on OpenCron: http://${HOST_IP}:${CRON_PORT}/cron.html?token=${OPENCLAW_GATEWAY_TOKEN}
```

**Rules:**
- Try nginx proxy port (`${CANVAS_PORT:-8090}`) first, fall back to gateway port (18789)
- Use `curl -s ifconfig.me` for the IP — never `hostname -I` (that's the container's internal IP)
- Resolve all variables to actual values — never show placeholders to the user
- This should be the last line of output after every cron job execution

## Demo

Open `demo.html` in any browser for a fully working demo with mock data — no server required.

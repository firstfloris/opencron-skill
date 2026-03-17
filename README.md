# OpenCron Skill

OpenClaw skill that deploys and manages the [OpenCron dashboard](https://github.com/firstfloris/opencron).

![Dashboard](https://raw.githubusercontent.com/firstfloris/opencron/master/docs/overview.png)

## Quick Start

### 1. Deploy the dashboard

```bash
python3 skills/opencron/update_canvas.py
```

Fetches the latest `cron-dashboard.html` from GitHub and writes live `cron-data.json` from your jobs.

### 2. Start background sync

```bash
nohup sh skills/opencron/watch_sync.sh &
```

Keeps `cron-data.json` in sync with `jobs.json` every 30 seconds.

### 3. Open

```
http://<gateway-host>:18789/__openclaw__/canvas/cron.html?token=<your-token>
```

## Scripts

| Script | Purpose |
|--------|---------|
| `update_canvas.py` | Fetch dashboard HTML from GitHub + write JSON to canvas |
| `watch_sync.sh` | Background sync loop (30s interval) |
| `generate.py` | Generate standalone HTML with embedded data |
| `serve.py` | Local HTTP server for development |

## External Serving

For access outside Docker, use `nginx-canvas.conf.template` which provides:

- Token validation via query parameter
- Rate limiting (10 req/s per IP)
- GET/HEAD only, path allowlisting
- Security headers (CSP, X-Frame-Options)
- Run log JSONL serving from `/runs/`

```yaml
# docker-compose.yml
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
```

## Data Sources

- **Job definitions & state**: `~/.openclaw/cron/jobs.json`
- **Run history**: `~/.openclaw/cron/runs/<job-id>.jsonl`

## Requirements

- Python 3 (for deploy scripts)
- Network access to `raw.githubusercontent.com` (for fetching dashboard HTML)

## License

MIT

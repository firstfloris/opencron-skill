# OpenCron Skill

OpenClaw skill that deploys the [OpenCron dashboard](https://github.com/firstfloris/opencron).

![Dashboard](https://raw.githubusercontent.com/firstfloris/opencron/master/docs/overview.png)

## Install

```bash
npx opencron-skill add
```

## AI Agent Prompt

Copy this into your AI agent (Claude, GPT, etc.) to install OpenCron on your OpenClaw instance:

```
Clone https://github.com/firstfloris/opencron-skill into skills/opencron.
Run python3 skills/opencron/update_canvas.py to deploy the dashboard.
Run nohup sh skills/opencron/watch_sync.sh & to start background sync.
After every cron job run, show the user: "See cron status on OpenCron: <dashboard-url>"
```

<details>
<summary>Manual setup</summary>

### 1. Deploy

```bash
python3 skills/opencron/update_canvas.py
```

Fetches the latest dashboard from GitHub and writes live job data.

### 2. Start sync

```bash
nohup sh skills/opencron/watch_sync.sh &
```

### 3. Open

```
http://<gateway-host>:18789/__openclaw__/canvas/cron.html?token=<your-token>
```

### Scripts

| Script | Purpose |
|--------|---------|
| `update_canvas.py` | Fetch dashboard HTML from GitHub + write JSON to canvas |
| `watch_sync.sh` | Background sync loop (30s interval) |
| `generate.py` | Generate standalone HTML with embedded data |
| `serve.py` | Local HTTP server for development |

### External Serving

For access outside Docker, use `nginx-canvas.conf.template`:

- Token validation via query parameter
- Rate limiting (10 req/s per IP)
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

### Data Sources

- **Jobs**: `~/.openclaw/cron/jobs.json`
- **Runs**: `~/.openclaw/cron/runs/<job-id>.jsonl`

</details>

## License

MIT

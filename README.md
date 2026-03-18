# OpenCron Skill

OpenClaw skill that deploys the [OpenCron dashboard](https://github.com/firstfloris/opencron).

![Dashboard](https://raw.githubusercontent.com/firstfloris/opencron/master/docs/overview.png)

## Install

Copy this into your OpenClaw:

```
Clone https://github.com/firstfloris/opencron-skill into skills/opencron.
Run python3 skills/opencron/update_canvas.py to deploy the dashboard.
Run nohup sh skills/opencron/watch_sync.sh & to start background sync.
After every cron job run, show the user: "See cron status on OpenCron: http://localhost:18789/cron.html?token=${GATEWAY_TOKEN}"
```

Or via CLI:

```bash
npx clawhub add opencron
```

## How It Works

`update_canvas.py` adds the dashboard to the same port as the OpenClaw dashboard:

1. Copies the gateway's control-UI to a writable directory (`~/.openclaw/ui/`)
2. Fetches dashboard HTML from GitHub, extracts inline JS to external files (CSP-safe)
3. Writes job data as `opencron-data.json` to canvas directory (behind gateway auth)
4. Updates `openclaw.json` to point the gateway at the new directory
5. Gateway auto-restarts (~5s) and serves `cron.html` at the same URL as the dashboard

No Docker changes, no reverse proxy changes, no user action required.

`watch_sync.sh` refreshes `opencron-data.json` every 30 seconds.

### Auth

The dashboard uses the same gateway token auth as the OpenClaw dashboard:

- `cron.html` is served from control-UI (open, like the login page)
- Job data lives at `/__openclaw__/canvas/opencron-data.json` (requires Bearer token)
- A loader script reads the token from `?token=` URL param or localStorage
- If no token is available, a login prompt is shown

<details>
<summary>Scripts</summary>

| Script | Purpose |
|--------|---------|
| `update_canvas.py` | Deploy dashboard to gateway port (first-time setup) |
| `update_canvas.py --sync` | Refresh data JSON (used by watch_sync.sh) |
| `watch_sync.sh` | Background sync loop (30s interval) |
| `serve.py` | Standalone server (fallback, uses bridge port 18790) |
| `generate.py` | Generate standalone HTML with embedded data |

</details>

<details>
<summary>Data sources</summary>

- **Jobs**: `~/.openclaw/cron/jobs.json`
- **Runs**: `~/.openclaw/cron/runs/<job-id>.jsonl`

</details>

## License

MIT

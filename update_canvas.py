#!/usr/bin/env python3
"""Deploy the OpenCron dashboard on the gateway port.

Copies the gateway's control-UI assets to a writable directory, adds
cron.html with embedded job data, and points the gateway config at the
new root.  The gateway auto-restarts on config change, so cron.html
becomes available at http://host:18789/cron.html — same port as the
OpenClaw dashboard, no extra auth.

Usage:
    python3 skills/opencron/update_canvas.py          # first-time setup + deploy
    python3 skills/opencron/update_canvas.py --sync   # refresh data only
"""

import json
import os
import shutil
import urllib.request
from pathlib import Path

JOBS_PATH = Path.home() / ".openclaw/cron/jobs.json"
RUNS_DIR = Path.home() / ".openclaw/cron/runs"
CONFIG_PATH = Path.home() / ".openclaw/openclaw.json"
UI_OVERLAY = Path.home() / ".openclaw/ui"
BUNDLED_UI = Path("/app/dist/control-ui")
CACHE_DIR = Path.home() / ".openclaw/cache/opencron"
DASHBOARD_CACHE = CACHE_DIR / "cron-dashboard.html"
DASHBOARD_URL = "https://raw.githubusercontent.com/firstfloris/opencron/master/cron-dashboard.html"


def fetch_template():
    """Download dashboard HTML from GitHub and cache locally."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    data = urllib.request.urlopen(DASHBOARD_URL).read()
    DASHBOARD_CACHE.write_bytes(data)
    return data.decode("utf-8")


def get_template():
    """Get cached template or fetch from GitHub."""
    if DASHBOARD_CACHE.exists():
        return DASHBOARD_CACHE.read_text("utf-8")
    return fetch_template()


def read_jobs():
    try:
        return json.loads(JOBS_PATH.read_text())
    except Exception:
        return {"jobs": []}


def read_runs(jobs):
    runs = {}
    for job in jobs.get("jobs", []):
        job_id = job.get("id", "")
        run_file = RUNS_DIR / f"{job_id}.jsonl"
        if run_file.exists():
            entries = []
            for line in run_file.read_text().strip().split("\n"):
                if line:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
            runs[job_id] = entries
        else:
            runs[job_id] = []
    return runs


def build_data_js(jobs=None, runs=None):
    """Build a JS file that sets window globals for job data."""
    if jobs is None:
        jobs = read_jobs()
    if runs is None:
        runs = read_runs(jobs)
    return (
        "window.__OPENCRON_DATA=" + json.dumps(jobs) + ";\n"
        "window.__OPENCRON_RUNS=" + json.dumps(runs) + ";\n"
    )


def externalize_scripts(html):
    """Extract inline <script> content to an external file.

    The gateway's control-UI sets a strict CSP (script-src 'self') that
    blocks inline scripts.  This moves all inline JS to opencron-app.js
    and replaces <script>...</script> with <script src="opencron-app.js">.
    Also removes inline event handlers (onload, onclick) since CSP blocks
    those too.
    """
    import re

    app_js_parts = []

    def replace_inline_script(m):
        content = m.group(1).strip()
        if content:
            app_js_parts.append(content)
        return ""

    html = re.sub(
        r"<script(?:\s[^>]*)?>(.+?)</script>",
        replace_inline_script,
        html,
        flags=re.DOTALL,
    )

    # Remove inline event handlers (onload="...", onclick="...")
    html = re.sub(r'\s+onload="[^"]*"', "", html)
    html = re.sub(r"\s+onload='[^']*'", "", html)

    app_js = "\n".join(app_js_parts)
    return html, app_js


def build_page(template=None):
    """Build HTML + external JS files for CSP-safe serving."""
    if template is None:
        template = get_template()

    html, app_js = externalize_scripts(template)

    # Add external script tags before </body>
    scripts = (
        '<script src="opencron-data.js"></script>\n'
        '<script src="opencron-app.js"></script>\n'
    )
    html = html.replace("</body>", scripts + "</body>")

    return html, app_js


def ensure_ui_overlay():
    """Copy bundled control-UI to a writable overlay directory.

    Returns True if the overlay was just created (config needs updating).
    """
    if UI_OVERLAY.exists() and (UI_OVERLAY / "index.html").exists():
        return False

    if not BUNDLED_UI.exists():
        print("Warning: bundled control-UI not found, creating minimal overlay")
        UI_OVERLAY.mkdir(parents=True, exist_ok=True)
        return True

    # Copy bundled UI to writable location
    if UI_OVERLAY.exists():
        shutil.rmtree(UI_OVERLAY)
    shutil.copytree(str(BUNDLED_UI), str(UI_OVERLAY), ignore=shutil.ignore_patterns("cron*"))
    return True


def update_gateway_config():
    """Point gateway.controlUi.root at the overlay directory.

    The gateway watches openclaw.json and auto-restarts on changes to
    the gateway.* section, so this takes effect without manual restart.
    """
    try:
        config = json.loads(CONFIG_PATH.read_text())
    except Exception:
        config = {}

    gw = config.setdefault("gateway", {})
    cui = gw.setdefault("controlUi", {})

    if cui.get("root") == str(UI_OVERLAY):
        return False  # already set

    cui["root"] = str(UI_OVERLAY)
    CONFIG_PATH.write_text(json.dumps(config, indent=2))
    return True


def deploy(html, app_js, data_js):
    """Write cron.html and JS files to the UI overlay."""
    UI_OVERLAY.mkdir(parents=True, exist_ok=True)
    (UI_OVERLAY / "cron.html").write_text(html, encoding="utf-8")
    (UI_OVERLAY / "opencron-app.js").write_text(app_js, encoding="utf-8")
    (UI_OVERLAY / "opencron-data.js").write_text(data_js, encoding="utf-8")


def main():
    import sys
    sync = "--sync" in sys.argv

    if sync:
        jobs = read_jobs()
        runs = read_runs(jobs)
        # Only update data JS on sync (app JS doesn't change)
        UI_OVERLAY.mkdir(parents=True, exist_ok=True)
        (UI_OVERLAY / "opencron-data.js").write_text(
            build_data_js(jobs, runs), encoding="utf-8"
        )
        return

    # Full deploy
    print(f"Fetching dashboard from {DASHBOARD_URL}...")
    template = fetch_template()
    jobs = read_jobs()
    runs = read_runs(jobs)
    html, app_js = build_page(template)
    data_js = build_data_js(jobs, runs)

    created = ensure_ui_overlay()
    deploy(html, app_js, data_js)

    if created:
        changed = update_gateway_config()
        if changed:
            print("Gateway config updated — gateway will auto-restart")

    print("Dashboard deployed to /cron.html")


if __name__ == "__main__":
    main()

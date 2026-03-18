#!/usr/bin/env python3
"""Deploy the OpenCron dashboard on the gateway port.

Copies the gateway's control-UI assets to a writable directory, adds
cron.html (open, like the login page) and puts job data behind canvas
auth at /__openclaw__/canvas/opencron-data.json.

The gateway auto-restarts on config change, so cron.html becomes
available at http://host:18789/cron.html — same port and same auth
as the OpenClaw dashboard.

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
CANVAS_DIR = Path.home() / ".openclaw/canvas"
BUNDLED_UI = Path("/app/dist/control-ui")
CACHE_DIR = Path.home() / ".openclaw/cache/opencron"
DASHBOARD_CACHE = CACHE_DIR / "cron-dashboard.html"
DASHBOARD_URL = "https://raw.githubusercontent.com/firstfloris/opencron/master/cron-dashboard.html"


# Loader JS — runs before the app to handle auth and data fetching.
#
# Uses safe DOM methods (createElement/textContent/appendChild) instead of
# innerHTML to comply with CSP and security policies.
#
# Strategy: do NOT set window.__OPENCRON_DATA (that triggers "embedded" mode
# which does full page reloads instead of XHR polling). Instead, patch
# window.fetch to:
#   1. Add Bearer auth headers for canvas paths
#   2. Rewrite the app's default JOBS_URL to our data endpoint
#   3. Intercept /runs/<id>.jsonl requests and serve from cached combined JSON
# This lets the app's built-in 30s polling work seamlessly.
LOADER_JS = r"""
(function() {
  var params = new URLSearchParams(window.location.search);
  var token = params.get('token');
  if (!token) {
    try { token = localStorage.getItem('opencron_token'); } catch(e) {}
  }

  if (!token) {
    document.addEventListener('DOMContentLoaded', function() {
      // Build login form using safe DOM methods
      var wrap = document.createElement('div');
      wrap.style.cssText = 'display:grid;place-items:center;min-height:100vh;background:#000;color:#fff;font-family:Inter,system-ui,sans-serif';

      var box = document.createElement('div');
      box.style.cssText = 'width:min(400px,90%);text-align:center';

      var h1 = document.createElement('h1');
      h1.style.cssText = 'font-size:22px;margin-bottom:16px';
      h1.textContent = 'OpenCron';

      var p = document.createElement('p');
      p.style.cssText = 'opacity:0.6;margin-bottom:24px';
      p.textContent = 'Enter your gateway token to view the dashboard';

      var input = document.createElement('input');
      input.type = 'password';
      input.placeholder = 'Gateway token';
      input.style.cssText = 'width:100%;padding:12px;border-radius:8px;border:1px solid rgba(255,255,255,0.15);background:rgba(255,255,255,0.08);color:#fff;font-size:14px;box-sizing:border-box';

      var btn = document.createElement('button');
      btn.textContent = 'Connect';
      btn.style.cssText = 'width:100%;margin-top:12px;padding:12px;border-radius:8px;border:none;background:#c8ff00;color:#000;font-weight:600;cursor:pointer;font-size:14px';

      function submit() {
        var v = input.value.trim();
        if (v) {
          try { localStorage.setItem('opencron_token', v); } catch(e) {}
          window.location.href = window.location.pathname + '?token=' + encodeURIComponent(v);
        }
      }

      btn.addEventListener('click', submit);
      input.addEventListener('keydown', function(e) {
        if (e.key === 'Enter') submit();
      });

      box.appendChild(h1);
      box.appendChild(p);
      box.appendChild(input);
      box.appendChild(btn);
      wrap.appendChild(box);

      while (document.body.firstChild) document.body.removeChild(document.body.firstChild);
      document.body.appendChild(wrap);
    });
    window.__OPENCRON_AUTH_PENDING = true;
    return;
  }

  try { localStorage.setItem('opencron_token', token); } catch(e) {}

  // Cache for runs data (refreshed on each jobs fetch)
  var cachedRuns = {};
  var DATA_URL = '/__openclaw__/canvas/opencron-data.json';

  // Patch fetch to add Bearer auth and rewrite URLs
  var origFetch = window.fetch;
  window.fetch = function(url, opts) {
    var urlStr = typeof url === 'string' ? url : url.toString();

    // Intercept runs requests — serve from cached combined data
    var runsMatch = urlStr.match(/\/runs\/([^/?]+)\.jsonl/);
    if (runsMatch) {
      var jobId = decodeURIComponent(runsMatch[1]);
      var entries = cachedRuns[jobId] || [];
      var lines = entries.map(function(e) { return JSON.stringify(e); }).join('\n');
      return Promise.resolve(new Response(lines, {
        status: 200,
        headers: { 'Content-Type': 'text/plain' }
      }));
    }

    // Intercept jobs data requests — rewrite to our endpoint + add auth
    if (urlStr.indexOf('cron-data.json') !== -1 || urlStr.indexOf('opencron-data.json') !== -1) {
      opts = opts || {};
      opts.headers = opts.headers || {};
      opts.headers['Authorization'] = 'Bearer ' + token;
      return origFetch.call(window, DATA_URL, opts).then(function(res) {
        if (res.status === 401 || res.status === 403) {
          try { localStorage.removeItem('opencron_token'); } catch(e) {}
          window.location.href = window.location.pathname;
          return res;
        }
        // Clone, parse to cache runs, return modified response with just jobs
        return res.clone().json().then(function(d) {
          cachedRuns = d.runs || {};
          // Return a new response with just the jobs data (what the app expects)
          return new Response(JSON.stringify(d.jobs), {
            status: 200,
            headers: { 'Content-Type': 'application/json' }
          });
        });
      });
    }

    // All other fetches — pass through, add auth for canvas paths
    if (urlStr.indexOf('/__openclaw__/canvas/') !== -1) {
      opts = opts || {};
      opts.headers = opts.headers || {};
      opts.headers['Authorization'] = 'Bearer ' + token;
    }
    return origFetch.call(window, url, opts);
  };
})();
""".strip()


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


def build_data_json(jobs=None, runs=None):
    """Build JSON with job data and run history for canvas path."""
    if jobs is None:
        jobs = read_jobs()
    if runs is None:
        runs = read_runs(jobs)
    return json.dumps({"jobs": jobs, "runs": runs})


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
    # Loader runs first (fetches data via auth), then app uses it
    scripts = (
        '<script src="opencron-loader.js"></script>\n'
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


def deploy_ui(html, app_js):
    """Write cron.html and JS files to the UI overlay (open, no auth)."""
    UI_OVERLAY.mkdir(parents=True, exist_ok=True)
    (UI_OVERLAY / "cron.html").write_text(html, encoding="utf-8")
    (UI_OVERLAY / "opencron-app.js").write_text(app_js, encoding="utf-8")
    (UI_OVERLAY / "opencron-loader.js").write_text(LOADER_JS, encoding="utf-8")


def deploy_data(data_json):
    """Write data JSON to canvas directory (behind gateway auth)."""
    CANVAS_DIR.mkdir(parents=True, exist_ok=True)
    (CANVAS_DIR / "opencron-data.json").write_text(data_json, encoding="utf-8")


def main():
    import sys
    sync = "--sync" in sys.argv

    if sync:
        jobs = read_jobs()
        runs = read_runs(jobs)
        deploy_data(build_data_json(jobs, runs))
        return

    # Full deploy
    print(f"Fetching dashboard from {DASHBOARD_URL}...")
    template = fetch_template()
    jobs = read_jobs()
    runs = read_runs(jobs)
    html, app_js = build_page(template)
    data_json = build_data_json(jobs, runs)

    created = ensure_ui_overlay()
    deploy_ui(html, app_js)
    deploy_data(data_json)

    if created:
        changed = update_gateway_config()
        if changed:
            print("Gateway config updated — gateway will auto-restart")

    print("Dashboard deployed to /cron.html")


if __name__ == "__main__":
    main()

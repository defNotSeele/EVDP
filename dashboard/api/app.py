#!/usr/bin/env python3
"""EVDP dashboard server: JSON API + the built React pages.

    /        About page (what the QR codes on the enclosures open)
    /data    live data dashboard
    /api/*   read-only JSON

Run in production with waitress (see systemd/evdp-dashboard.service):
    waitress-serve --listen=0.0.0.0:8080 app:app
"""

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, abort, jsonify, request, send_from_directory

HERE = Path(__file__).resolve().parent
# Reuse the ingesters' DB path and node list (one source of truth). Repo layout
# and Pi layout both put ingest/ two levels up: <root>/dashboard/api -> <root>/ingest
sys.path.insert(0, os.environ.get("EVDP_INGEST_DIR", str(HERE.parent.parent / "ingest")))
from common import DB_PATH  # noqa: E402

import queries as q  # noqa: E402

WEB_DIST = Path(os.environ.get("EVDP_WEB_DIST", HERE.parent / "web" / "dist"))
DB = os.environ.get("EVDP_DB", DB_PATH)

app = Flask(__name__, static_folder=None)


def _range():
    r = request.args.get("range", q.DEFAULT_RANGE)
    if r not in q.RANGES:
        abort(400, f"range must be one of {', '.join(q.RANGES)}")
    return r


def _with_db(fn, *args):
    con = q.connect(DB)
    try:
        return fn(con, *args)
    finally:
        con.close()


@app.get("/api/meta")
def api_meta():
    return jsonify({
        "server_time": q.iso(datetime.now(timezone.utc)),
        "ranges": list(q.RANGES),
        "default_range": q.DEFAULT_RANGE,
        "stale_after_s": q.STALE_AFTER_S,
        "nodes": _with_db(q.nodes),
    })


@app.get("/api/latest")
def api_latest():
    return jsonify(_with_db(q.latest))


@app.get("/api/history")
def api_history():
    return jsonify(_with_db(q.history, _range()))


@app.get("/api/paths")
def api_paths():
    return jsonify(_with_db(q.paths, _range()))


@app.get("/api/power")
def api_power():
    return jsonify(_with_db(q.power, _range()))


@app.after_request
def no_cache_api(resp):
    if request.path.startswith("/api/"):
        resp.headers["Cache-Control"] = "no-store"
    return resp


# ---- built React pages (Vite multi-page build) -----------------------------

@app.get("/")
def about():
    return send_from_directory(WEB_DIST, "about.html")


@app.get("/data")
def data():
    return send_from_directory(WEB_DIST, "index.html")


@app.get("/assets/<path:name>")
def assets(name):
    return send_from_directory(WEB_DIST / "assets", name)


if __name__ == "__main__":  # development only
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", "5000")), debug=True)

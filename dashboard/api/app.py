#!/usr/bin/env python3
"""EVDP dashboard server.

    /             About page (opened by the QR codes on the enclosures)
    /data         live data page
    /api/entry    everything the data page needs, in one response
    /api/paths    transport delivery and latency (analysis)

Environment: EVDP_DB (database path), EVDP_WEB_DIST (built front end, optional).
Production: waitress-serve --listen=0.0.0.0:8080 app:app
"""

import os
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, abort, jsonify, request, send_from_directory

import queries as q
from db import Database

DB_PATH = os.environ.get("EVDP_DB")
if not DB_PATH:
    raise SystemExit("EVDP_DB is not set")
db = Database(DB_PATH)

WEB_DIST = Path(os.environ.get("EVDP_WEB_DIST", Path(__file__).resolve().parent.parent / "web" / "dist"))

app = Flask(__name__, static_folder=None)


def _range():
    r = request.args.get("range", q.DEFAULT_RANGE)
    if r not in q.RANGES:
        abort(400, f"range must be one of {', '.join(q.RANGES)}")
    return r


@app.get("/api/entry")
def api_entry():
    return jsonify(q.entry(db, _range()))


@app.get("/api/paths")
def api_paths():
    return jsonify(q.paths(db, _range(), datetime.now(timezone.utc)))


@app.after_request
def cache_headers(resp):
    if request.path.startswith("/api/"):
        resp.headers["Cache-Control"] = "no-store"
    elif request.path.startswith("/assets/"):
        resp.headers["Cache-Control"] = "public, max-age=31536000, immutable"  # file names are content-hashed
    else:
        resp.headers["Cache-Control"] = "no-cache"
    return resp


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

"""Shared pieces for the EVDP ingesters: config, DB writes, node whitelist."""

import json
import logging
import os
import sqlite3
import subprocess
import threading
import time
from datetime import datetime, timezone

log = logging.getLogger("evdp")


def require_env(name):
    value = os.environ.get(name)
    if not value:
        raise SystemExit(f"{name} is not set")
    return value


def setup_logging(name):
    logging.basicConfig(level=logging.INFO, format=f"%(asctime)s {name} %(levelname)s %(message)s")


def node_id_from_num(num):
    """Meshtastic node number -> '!xxxxxxxx'."""
    return "!%08x" % (int(num) & 0xFFFFFFFF)


def utc_now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def wait_for_clock_sync(poll_secs=5):
    """Block until NTP has synced the Pi's clock, so received_at is never wrong."""
    while True:
        try:
            synced = subprocess.run(
                ["timedatectl", "show", "-p", "NTPSynchronized", "--value"],
                capture_output=True, text=True, timeout=10,
            ).stdout.strip() == "yes"
        except Exception as exc:
            log.warning("clock check failed (%s); continuing", exc)
            return
        if synced:
            return
        log.info("waiting for NTP clock sync...")
        time.sleep(poll_secs)


def to_json(obj):
    """Packet as JSON for the raw column (bytes and protobuf objects dropped)."""
    def clean(o):
        if isinstance(o, dict):
            return {k: clean(v) for k, v in o.items() if k != "raw" and not isinstance(v, (bytes, bytearray))}
        if isinstance(o, (list, tuple)):
            return [clean(v) for v in o]
        return o
    return json.dumps(clean(obj), default=str, separators=(",", ":"))


class Store:
    """Write access to the telemetry database.

    The `nodes` table is the whitelist: packets from any node not registered
    there are ignored. It is re-read periodically, so registering a node needs
    no restart.
    """

    WHITELIST_REFRESH_S = 60

    def __init__(self, path):
        # The meshtastic library delivers packets on its own reader thread; only
        # that one thread writes, so sharing the connection across threads is safe.
        self.db = sqlite3.connect(path, timeout=30, isolation_level=None, check_same_thread=False)
        self.db.execute("PRAGMA journal_mode = WAL")
        self.db.execute("PRAGMA foreign_keys = ON")
        self._lock = threading.Lock()
        self._known, self._known_at = set(), 0.0

    def is_known(self, node_id):
        with self._lock:
            if time.monotonic() - self._known_at > self.WHITELIST_REFRESH_S:
                self._known = {r[0] for r in self.db.execute("SELECT node_id FROM nodes")}
                self._known_at = time.monotonic()
            return node_id in self._known

    def update_node(self, node_id, short_name=None, long_name=None, hw_model=None):
        """Refresh a registered node's names from its NodeInfo broadcast."""
        self.db.execute(
            """UPDATE nodes SET short_name = COALESCE(?, short_name),
                                long_name  = COALESCE(?, long_name),
                                hw_model   = COALESCE(?, hw_model)
               WHERE node_id = ?""",
            (short_name, long_name, hw_model, node_id),
        )

    def add_reading(self, *, packet_id, node_id, transport, packet_time=None, gateway_id=None,
                    hops=None, rx_snr=None, rx_rssi=None, temperature=None, humidity=None,
                    replayed=False, raw=None):
        cur = self.db.execute(
            """INSERT OR IGNORE INTO readings
               (received_at, packet_time, packet_id, node_id, transport, gateway_id,
                hops, rx_snr, rx_rssi, temperature, humidity, replayed, raw)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (utc_now_iso(), packet_time, packet_id, node_id, transport, gateway_id,
             hops, rx_snr, rx_rssi, temperature, humidity, int(replayed), raw),
        )
        return cur.rowcount == 1

    def add_device_metrics(self, *, packet_id, node_id, transport, packet_time=None, gateway_id=None,
                           battery_level=None, voltage=None, channel_util=None, air_util_tx=None,
                           uptime_secs=None, raw=None):
        cur = self.db.execute(
            """INSERT OR IGNORE INTO device_metrics
               (received_at, packet_time, packet_id, node_id, transport, gateway_id,
                battery_level, voltage, channel_util, air_util_tx, uptime_secs, raw)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (utc_now_iso(), packet_time, packet_id, node_id, transport, gateway_id,
             battery_level, voltage, channel_util, air_util_tx, uptime_secs, raw),
        )
        return cur.rowcount == 1

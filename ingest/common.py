"""Shared pieces for the EVDP ingesters: config, clock check, database writes.

Both ingesters write to the same SQLite database. One row per DELIVERY: the same
reading arriving over LoRa and over MQTT gives two rows that share packet_id and
node_id and differ in transport. UNIQUE(packet_id, transport, node_id) absorbs
duplicates *within* a transport (mesh rebroadcasts, MQTT redelivery).
"""

import json
import logging
import os
import sqlite3
import subprocess
import time
from datetime import datetime, timezone

DB_PATH = os.environ.get("EVDP_DB", os.path.expanduser("~/evdp/telemetry.db"))

# Only the project's own nodes are stored. The gateway uplinks everything it
# hears, including third-party nodes on the public channel; their metadata is
# dropped here on purpose (data minimisation).
PROJECT_NODES = {
    "!a1f7f284": ("N1", "EVDP Node 1 LoRa"),
    "!a1f7f770": ("N2", "EVDP Node 2"),
    "!c1fc83d0": ("N3", "EVDP Pi listener"),
    "!084fbf75": ("Sax1", "Saxion microelectronics & edgeAI SolR1"),  # repeater: SenseCAP Solar Node, ROUTER; keeps its Saxion name; no sensor, battery telemetry
}

log = logging.getLogger("evdp")


def setup_logging(name):
    logging.basicConfig(
        level=logging.INFO,
        format=f"%(asctime)s {name} %(levelname)s %(message)s",
    )


def node_id_from_num(num):
    """Meshtastic node number (int) -> canonical '!xxxxxxxx' id."""
    return "!%08x" % (int(num) & 0xFFFFFFFF)


def utc_now_iso():
    """ISO-8601 UTC with milliseconds, e.g. 2026-11-15T19:20:01.123Z."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def wait_for_clock_sync(poll_secs=5):
    """Block until NTP has synchronised the clock.

    A Pi 5 without an RTC battery boots on its last saved time (seen: July) and
    is corrected only when NTP syncs. Rows written before that would carry a
    wrong received_at. User services can't order on time-sync.target, so the
    check is done here.
    """
    while True:
        try:
            out = subprocess.run(
                ["timedatectl", "show", "-p", "NTPSynchronized", "--value"],
                capture_output=True, text=True, timeout=10,
            ).stdout.strip()
        except Exception as exc:  # timedatectl missing or hung: don't block forever
            log.warning("clock check failed (%s); continuing", exc)
            return
        if out == "yes":
            log.info("clock synchronised")
            return
        log.info("waiting for NTP clock sync...")
        time.sleep(poll_secs)


def to_json(obj):
    """Best-effort JSON for the raw column: drop bytes, stringify the rest."""
    def clean(o):
        if isinstance(o, dict):
            return {k: clean(v) for k, v in o.items() if k != "raw" and not isinstance(v, (bytes, bytearray))}
        if isinstance(o, (list, tuple)):
            return [clean(v) for v in o]
        return o
    return json.dumps(clean(obj), default=str, separators=(",", ":"))


class Store:
    def __init__(self, path=DB_PATH):
        # check_same_thread=False: the meshtastic library delivers packets on its
        # own reader thread. Only that one thread writes, so this is safe.
        self.db = sqlite3.connect(path, timeout=30, isolation_level=None, check_same_thread=False)
        self.db.execute("PRAGMA journal_mode = WAL")
        self.db.execute("PRAGMA foreign_keys = ON")
        self.db.execute("PRAGMA busy_timeout = 30000")
        for node_id, (short, long_) in PROJECT_NODES.items():
            self.upsert_node(node_id, short, long_, only_if_missing=True)

    def upsert_node(self, node_id, short_name=None, long_name=None, hw_model=None, only_if_missing=False):
        if only_if_missing:
            self.db.execute(
                "INSERT OR IGNORE INTO nodes(node_id, short_name, long_name) VALUES (?,?,?)",
                (node_id, short_name, long_name),
            )
            return
        self.db.execute(
            """INSERT INTO nodes(node_id, short_name, long_name, hw_model) VALUES (?,?,?,?)
               ON CONFLICT(node_id) DO UPDATE SET
                 short_name = COALESCE(excluded.short_name, short_name),
                 long_name  = COALESCE(excluded.long_name,  long_name),
                 hw_model   = COALESCE(excluded.hw_model,   hw_model)""",
            (node_id, short_name, long_name, hw_model),
        )

    def add_reading(self, *, packet_id, node_id, transport, packet_time=None, gateway_id=None,
                    hops=None, rx_snr=None, rx_rssi=None, temperature=None, humidity=None, raw=None):
        cur = self.db.execute(
            """INSERT OR IGNORE INTO readings
               (received_at, packet_time, packet_id, node_id, transport, gateway_id,
                hops, rx_snr, rx_rssi, temperature, humidity, raw)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (utc_now_iso(), packet_time, packet_id, node_id, transport, gateway_id,
             hops, rx_snr, rx_rssi, temperature, humidity, raw),
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

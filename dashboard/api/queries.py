"""Read-only queries behind the dashboard API.

Everything here opens the database read-only, so the dashboard can never
write to, or hold a write lock on, the ingesters' database. Only curated
fields leave this module; the `raw` packet column is never returned.
"""

import sqlite3
from datetime import datetime, timedelta, timezone
from statistics import median

RANGES = {"6h": timedelta(hours=6), "24h": timedelta(hours=24), "7d": timedelta(days=7), "all": None}
DEFAULT_RANGE = "24h"

# Path latency is computed only from live arrivals. Before this instant the
# MQTT rows were backfilled from a capture file and the LoRa rows were
# replayed from Node 3's buffer, so their arrival times say nothing about
# path latency (BUILD_LOG session 3).
LATENCY_SINCE = "2026-11-15T19:31:00.000Z"
# A pair further apart than this is a buffer replay after an ingester restart,
# not a path delay. Excluded and counted.
LATENCY_MAX_ABS_S = 30.0

STALE_AFTER_S = 45 * 60  # sensor nodes report every 30 min


def connect(db_path):
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=10)
    con.row_factory = sqlite3.Row
    return con


def iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%S.") + f"{dt.microsecond // 1000:03d}Z"


def parse_iso(s):
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)


def since_for(range_key, now=None):
    now = now or datetime.now(timezone.utc)
    delta = RANGES[range_key]
    return iso(now - delta) if delta else "0000"


def nodes(con):
    rows = con.execute(
        "SELECT node_id, short_name, long_name, hw_model, role FROM nodes ORDER BY node_id").fetchall()
    sensor_ids = {r[0] for r in con.execute("SELECT DISTINCT node_id FROM readings")}
    return [dict(r) | {"has_sensor": r["node_id"] in sensor_ids} for r in rows]


def _measurements(con, since):
    """One row per measurement: both deliveries of a packet merged."""
    return con.execute(
        """SELECT node_id, packet_id,
                  MIN(received_at)            AS t,
                  AVG(temperature)            AS temperature,
                  AVG(humidity)               AS humidity,
                  GROUP_CONCAT(DISTINCT transport) AS transports
           FROM readings
           WHERE received_at >= ?
           GROUP BY node_id, packet_id
           ORDER BY t""",
        (since,),
    ).fetchall()


def _age(now, t):
    return round((now - parse_iso(t)).total_seconds())


def latest(con, now=None):
    """One card per field device (sensor nodes and the repeater; not Node 3,
    which is the Pi's own receiver): newest reading, how it arrived, and the
    newest energy report."""
    now = now or datetime.now(timezone.utc)
    newest = {}
    for r in _measurements(con, "0000"):
        newest[r["node_id"]] = r  # ordered by time, so the last one wins

    energy = {}
    for r in con.execute(
        """SELECT node_id, MIN(received_at) AS t, MAX(battery_level) AS battery_level,
                  AVG(voltage) AS voltage, GROUP_CONCAT(DISTINCT transport) AS transports
           FROM device_metrics GROUP BY node_id, packet_id ORDER BY t"""):
        energy[r["node_id"]] = r

    cards = []
    for n in nodes(con):
        if n["node_id"] not in newest and n["role"] != "ROUTER":
            continue  # Node 3 (the Pi's receiver) has no card
        card = {"node_id": n["node_id"], "short_name": n["short_name"],
                "long_name": n["long_name"], "role": n["role"], "has_sensor": n["has_sensor"],
                "reading": None, "energy": None}
        r = newest.get(n["node_id"])
        if r:
            tr = set(r["transports"].split(","))
            age = _age(now, r["t"])
            card["reading"] = {
                "time": r["t"], "age_s": age, "stale": age > STALE_AFTER_S,
                "temperature": round(r["temperature"], 2), "humidity": round(r["humidity"], 1),
                "via_lora": "lora" in tr, "via_mqtt": "mqtt" in tr,
            }
        e = energy.get(n["node_id"])
        if e:
            tr = set(e["transports"].split(","))
            card["energy"] = {
                "time": e["t"], "age_s": _age(now, e["t"]),
                "battery_level": e["battery_level"],
                "external_power": e["battery_level"] is not None and e["battery_level"] > 100,
                "voltage": None if e["voltage"] is None else round(e["voltage"], 3),
                "via_lora": "lora" in tr, "via_mqtt": "mqtt" in tr,
            }
        cards.append(card)
    # repeater first, then sensor nodes by name
    cards.sort(key=lambda c: (c["role"] != "ROUTER", c["short_name"] or ""))
    return cards


def history(con, range_key):
    return [
        {"time": r["t"], "node_id": r["node_id"],
         "temperature": round(r["temperature"], 2), "humidity": round(r["humidity"], 1)}
        for r in _measurements(con, since_for(range_key))
    ]


def paths(con, range_key):
    since = since_for(range_key)
    per_node = {}
    for r in _measurements(con, since):
        tr = set(r["transports"].split(","))
        c = per_node.setdefault(r["node_id"], {"both": 0, "lora_only": 0, "mqtt_only": 0})
        if tr == {"lora", "mqtt"}:
            c["both"] += 1
        elif tr == {"lora"}:
            c["lora_only"] += 1
        else:
            c["mqtt_only"] += 1
    summary = []
    for node_id, c in per_node.items():
        total = c["both"] + c["lora_only"] + c["mqtt_only"]
        summary.append({
            "node_id": node_id, "measurements": total, **c,
            "lora_rate": round((c["both"] + c["lora_only"]) / total, 3),
            "mqtt_rate": round((c["both"] + c["mqtt_only"]) / total, 3),
            "both_rate": round(c["both"] / total, 3),
        })

    pairs = con.execute(
        """SELECT l.node_id, l.packet_id, l.received_at AS lora_at, m.received_at AS mqtt_at
           FROM readings l
           JOIN readings m ON m.packet_id = l.packet_id AND m.node_id = l.node_id
                          AND m.transport = 'mqtt'
           WHERE l.transport = 'lora'
             AND MIN(l.received_at, m.received_at) >= ?
           ORDER BY l.received_at""",
        (max(since, LATENCY_SINCE),),
    ).fetchall()
    points, excluded = [], 0
    for p in pairs:
        delta = (parse_iso(p["lora_at"]) - parse_iso(p["mqtt_at"])).total_seconds()
        if abs(delta) > LATENCY_MAX_ABS_S:
            excluded += 1
            continue
        points.append({"time": min(p["lora_at"], p["mqtt_at"]), "node_id": p["node_id"],
                       "lora_minus_mqtt_ms": round(delta * 1000)})
    by_node = {}
    for pt in points:
        by_node.setdefault(pt["node_id"], []).append(pt["lora_minus_mqtt_ms"])
    return {
        "delivery": summary,
        "latency": {
            "points": points,
            "median_ms": {n: round(median(v)) for n, v in by_node.items()},
            "excluded_replays": excluded,
            "since": LATENCY_SINCE,
            "max_abs_s": LATENCY_MAX_ABS_S,
        },
    }


def power(con, range_key):
    rows = con.execute(
        """SELECT node_id, MIN(received_at) AS t,
                  MAX(battery_level) AS battery_level, AVG(voltage) AS voltage
           FROM device_metrics
           WHERE received_at >= ?
           GROUP BY node_id, packet_id            -- one point per report, either transport
           ORDER BY t""",
        (since_for(range_key),),
    ).fetchall()
    # battery_level > 100 is the firmware's way of saying "on external power":
    # passed through as-is, with a flag, so the UI can say "USB power" instead
    # of plotting 101 %.
    return [{"time": r["t"], "node_id": r["node_id"],
             "battery_level": r["battery_level"],
             "external_power": r["battery_level"] is not None and r["battery_level"] > 100,
             "voltage": None if r["voltage"] is None else round(r["voltage"], 3)}
            for r in rows]

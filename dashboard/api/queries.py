"""Queries behind the dashboard API. Only curated fields are returned; the raw
packet column never leaves this module."""

from datetime import datetime, timedelta, timezone
from statistics import median

RANGES = {"6h": timedelta(hours=6), "24h": timedelta(hours=24), "7d": timedelta(days=7), "all": None}
DEFAULT_RANGE = "24h"

REPORT_INTERVAL_S = 30 * 60   # nodes send readings and energy reports every 30 min
OVERDUE_GRACE_S = 5 * 60      # a report later than interval + grace counts as overdue


def iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%S.") + f"{dt.microsecond // 1000:03d}Z"


def parse_iso(s):
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)


def since_for(range_key, now):
    delta = RANGES[range_key]
    return iso(now - delta) if delta else "0000"


def nodes(db):
    """Registered nodes, in registration order."""
    sensor_ids = {r[0] for r in db.query("SELECT DISTINCT node_id FROM readings")}
    rows = db.query("SELECT node_id, short_name, long_name, hw_model, role FROM nodes ORDER BY rowid")
    return [dict(r) | {"has_sensor": r["node_id"] in sensor_ids} for r in rows]


def _measurements(db, since):
    """One row per measurement: the deliveries of a packet over both transports merged."""
    return db.query(
        """SELECT node_id, packet_id, MIN(received_at) AS t,
                  AVG(temperature) AS temperature, AVG(humidity) AS humidity,
                  GROUP_CONCAT(DISTINCT transport) AS transports
           FROM readings WHERE received_at >= ?
           GROUP BY node_id, packet_id ORDER BY t""",
        (since,),
    )


def _energy_reports(db, since):
    return db.query(
        """SELECT node_id, MIN(received_at) AS t, MAX(battery_level) AS battery_level,
                  AVG(voltage) AS voltage, GROUP_CONCAT(DISTINCT transport) AS transports
           FROM device_metrics WHERE received_at >= ?
           GROUP BY node_id, packet_id ORDER BY t""",
        (since,),
    )


def _status(now, t, transports):
    age = round((now - parse_iso(t)).total_seconds())
    tr = set(transports.split(","))
    return {"time": t, "age_s": age, "overdue": age > REPORT_INTERVAL_S + OVERDUE_GRACE_S,
            "via_lora": "lora" in tr, "via_mqtt": "mqtt" in tr}


def _energy(r):
    # The firmware reports battery_level > 100 when the device runs on external power.
    external = r["battery_level"] is not None and r["battery_level"] > 100
    # A voltage <= 0 means the device has no battery sensing (e.g. on USB power).
    voltage = r["voltage"] if r["voltage"] is not None and r["voltage"] > 0 else None
    return {"battery_level": None if external else r["battery_level"], "external_power": external,
            "voltage": None if voltage is None else round(voltage, 3)}


def devices(db, now):
    """One entry per field device (sensor nodes and the repeater, not the Pi's
    own receiver): latest reading, latest energy report, and how each arrived.
    `slot` is the device's fixed colour index: its position in registration order."""
    latest_reading = {r["node_id"]: r for r in _measurements(db, "0000")}
    latest_energy = {r["node_id"]: r for r in _energy_reports(db, "0000")}
    out = []
    for n in nodes(db):
        nid = n["node_id"]
        if nid not in latest_reading and n["role"] != "ROUTER":
            continue
        r, e = latest_reading.get(nid), latest_energy.get(nid)
        out.append(n | {
            "slot": len(out),
            "reading": r and _status(now, r["t"], r["transports"]) | {
                "temperature": round(r["temperature"], 2), "humidity": round(r["humidity"], 1)},
            "energy": e and _status(now, e["t"], e["transports"]) | _energy(e),
        })
    return out


def history(db, range_key, now):
    return [{"time": r["t"], "node_id": r["node_id"],
             "temperature": round(r["temperature"], 2), "humidity": round(r["humidity"], 1)}
            for r in _measurements(db, since_for(range_key, now))]


def energy(db, range_key, now):
    return [{"time": r["t"], "node_id": r["node_id"]} | _energy(r)
            for r in _energy_reports(db, since_for(range_key, now))]


def paths(db, range_key, now):
    """Delivery per transport and per-packet latency (LoRa minus MQTT arrival).
    Latency uses live arrivals only: pairs with a replayed row are skipped."""
    since = since_for(range_key, now)
    per_node = {}
    for r in _measurements(db, since):
        tr = set(r["transports"].split(","))
        key = "both" if tr == {"lora", "mqtt"} else "lora_only" if tr == {"lora"} else "mqtt_only"
        c = per_node.setdefault(r["node_id"], {"both": 0, "lora_only": 0, "mqtt_only": 0})
        c[key] += 1
    delivery = [{"node_id": nid, "measurements": sum(c.values()), **c} for nid, c in per_node.items()]

    pairs = db.query(
        """SELECT l.node_id, l.received_at AS lora_at, m.received_at AS mqtt_at
           FROM readings l
           JOIN readings m ON m.packet_id = l.packet_id AND m.node_id = l.node_id AND m.transport = 'mqtt'
           WHERE l.transport = 'lora' AND l.replayed = 0 AND m.replayed = 0 AND l.received_at >= ?
           ORDER BY l.received_at""",
        (since,),
    )
    points = [{"time": min(p["lora_at"], p["mqtt_at"]), "node_id": p["node_id"],
               "lora_minus_mqtt_ms": round((parse_iso(p["lora_at"]) - parse_iso(p["mqtt_at"])).total_seconds() * 1000)}
              for p in pairs]
    by_node = {}
    for p in points:
        by_node.setdefault(p["node_id"], []).append(p["lora_minus_mqtt_ms"])
    return {"delivery": delivery, "latency": points,
            "latency_median_ms": {nid: round(median(v)) for nid, v in by_node.items()}}


def entry(db, range_key, now=None):
    """Everything the data page needs, in one response."""
    now = now or datetime.now(timezone.utc)
    return {
        "server_time": iso(now),
        "range": range_key,
        "report_interval_s": REPORT_INTERVAL_S,
        "devices": devices(db, now),
        "history": history(db, range_key, now),
        "energy": energy(db, range_key, now),
    }

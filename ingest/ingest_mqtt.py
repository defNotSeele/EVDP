#!/usr/bin/env python3
"""MQTT ingester: Mosquitto on the Pi -> SQLite, transport='mqtt'.

Subscribes to msh/# (the topic root changed to msh/EU_868 when the region was
set, and the channel segment changes with the channel name, so no part of the
path below msh/ is assumed). Only the readable JSON topics are used:

    msh/<region>/2/json/<channel>/<gateway_id>

Field mapping (verified 2026-11-15, BUILD_LOG session 3):
    from      -> node_id (originator; converted to '!xxxxxxxx')
    sender    -> gateway_id (the node that uplinked it; NOT the originator)
    id        -> packet_id      timestamp -> packet_time
    hops_away -> hops           rssi/snr  -> gateway's reception of the LoRa hop

Packets with an empty type (ACK/routing, or PKI DMs the gateway can't decrypt)
are ignored. Only the project's own node ids are stored.

Credentials come from the environment: EVDP_MQTT_HOST/USER/PASS.
"""

import json
import os

import paho.mqtt.client as mqtt

from common import (PROJECT_NODES, Store, log, node_id_from_num, setup_logging,
                    to_json, wait_for_clock_sync)

HOST = os.environ.get("EVDP_MQTT_HOST", "localhost")
PORT = int(os.environ.get("EVDP_MQTT_PORT", "1883"))
USER = os.environ.get("EVDP_MQTT_USER", "meshtastic")
PASS = os.environ.get("EVDP_MQTT_PASS")
TOPIC = "msh/#"

ENV_KEYS = ("temperature", "relative_humidity")
DEV_KEYS = ("battery_level", "voltage", "channel_utilization", "air_util_tx", "uptime_seconds")

store = None


def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code.is_failure:
        log.error("broker refused connection: %s", reason_code)
        return
    log.info("connected to %s:%s, subscribing %s", HOST, PORT, TOPIC)
    client.subscribe(TOPIC, qos=0)


def on_disconnect(client, userdata, flags, reason_code, properties):
    log.warning("disconnected (%s); paho will reconnect", reason_code)


def on_message(client, userdata, msg):
    parts = msg.topic.split("/")
    if "json" not in parts:
        return  # binary ServiceEnvelope topics: ignored, the JSON twin carries the same packet
    try:
        data = json.loads(msg.payload)
    except ValueError:
        log.warning("non-JSON payload on %s", msg.topic)
        return
    try:
        handle(data, parts)
    except Exception:
        log.exception("failed to handle %s", msg.topic)


def handle(data, parts):
    if "from" not in data:
        return
    node_id = node_id_from_num(data["from"])
    if node_id not in PROJECT_NODES:
        return
    ptype = data.get("type")
    payload = data.get("payload")
    gateway_id = data.get("sender") or parts[-1]

    if ptype == "nodeinfo" and isinstance(payload, dict):
        # hardware arrives as a bare enum number here (e.g. 81); leave hw_model to
        # the LoRa side, which reports the name (SEEED_XIAO_S3).
        store.upsert_node(node_id, payload.get("shortname"), payload.get("longname"))
        log.info("nodeinfo %s %s / %s via %s", node_id, payload.get("longname"),
                 payload.get("shortname"), gateway_id)
        return
    if ptype != "telemetry" or not isinstance(payload, dict):
        return

    common = dict(
        packet_id=data.get("id"),
        node_id=node_id,
        transport="mqtt",
        packet_time=data.get("timestamp"),
        gateway_id=gateway_id,
        raw=to_json(data),
    )
    if any(k in payload for k in ENV_KEYS):
        new = store.add_reading(**common, hops=data.get("hops_away"),
                                rx_snr=data.get("snr"), rx_rssi=data.get("rssi"),
                                temperature=payload.get("temperature"),
                                humidity=payload.get("relative_humidity"))
        log.info("reading %s id=%s T=%s RH=%s via %s hops=%s snr=%s rssi=%s%s",
                 node_id, common["packet_id"], payload.get("temperature"),
                 payload.get("relative_humidity"), gateway_id, data.get("hops_away"),
                 data.get("snr"), data.get("rssi"), "" if new else " (duplicate)")
    elif any(k in payload for k in DEV_KEYS):
        new = store.add_device_metrics(**common,
                                       battery_level=payload.get("battery_level"),
                                       voltage=payload.get("voltage"),
                                       channel_util=payload.get("channel_utilization"),
                                       air_util_tx=payload.get("air_util_tx"),
                                       uptime_secs=payload.get("uptime_seconds"))
        log.info("device  %s id=%s batt=%s V=%s via %s%s", node_id, common["packet_id"],
                 payload.get("battery_level"), payload.get("voltage"), gateway_id,
                 "" if new else " (duplicate)")


def main():
    global store
    setup_logging("mqtt")
    if not PASS:
        raise SystemExit("EVDP_MQTT_PASS is not set")
    wait_for_clock_sync()
    store = Store()
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="evdp-ingest-mqtt")
    client.username_pw_set(USER, PASS)
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message
    client.reconnect_delay_set(min_delay=1, max_delay=60)
    client.connect(HOST, PORT, keepalive=60)
    client.loop_forever(retry_first_connection=True)


if __name__ == "__main__":
    main()

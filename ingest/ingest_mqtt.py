#!/usr/bin/env python3
"""MQTT ingester: Mosquitto on the Pi -> SQLite, transport='mqtt'.

Uses the JSON topics only: msh/<region>/2/json/<channel>/<gateway_id>.
`from` is the originating node; `sender` is the gateway that uplinked it.

Environment: EVDP_DB, EVDP_MQTT_PASS, and optionally EVDP_MQTT_HOST/PORT/USER.
"""

import json
import os

import paho.mqtt.client as mqtt

from common import Store, log, node_id_from_num, require_env, setup_logging, to_json, wait_for_clock_sync

HOST = os.environ.get("EVDP_MQTT_HOST", "localhost")
PORT = int(os.environ.get("EVDP_MQTT_PORT", "1883"))
USER = os.environ.get("EVDP_MQTT_USER", "meshtastic")
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
        return  # the binary /e/ twin carries the same packet
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
    if not store.is_known(node_id):
        return
    ptype = data.get("type")
    payload = data.get("payload")
    gateway_id = data.get("sender") or parts[-1]

    if ptype == "nodeinfo" and isinstance(payload, dict):
        # hw_model is left to the LoRa side, which reports the name rather than the enum number
        store.update_node(node_id, payload.get("shortname"), payload.get("longname"))
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
        log.info("reading %s id=%s T=%s RH=%s via %s%s", node_id, common["packet_id"],
                 payload.get("temperature"), payload.get("relative_humidity"), gateway_id,
                 "" if new else " duplicate")
    elif any(k in payload for k in DEV_KEYS):
        new = store.add_device_metrics(**common,
                                       battery_level=payload.get("battery_level"),
                                       voltage=payload.get("voltage"),
                                       channel_util=payload.get("channel_utilization"),
                                       air_util_tx=payload.get("air_util_tx"),
                                       uptime_secs=payload.get("uptime_seconds"))
        log.info("device  %s id=%s batt=%s V=%s via %s%s", node_id, common["packet_id"],
                 payload.get("battery_level"), payload.get("voltage"), gateway_id,
                 "" if new else " duplicate")


def main():
    global store
    setup_logging("mqtt")
    db_path = require_env("EVDP_DB")
    password = require_env("EVDP_MQTT_PASS")
    wait_for_clock_sync()
    store = Store(db_path)
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="evdp-ingest-mqtt")
    client.username_pw_set(USER, password)
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message
    client.reconnect_delay_set(min_delay=1, max_delay=60)
    client.connect(HOST, PORT, keepalive=60)
    client.loop_forever(retry_first_connection=True)


if __name__ == "__main__":
    main()

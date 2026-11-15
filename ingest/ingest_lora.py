#!/usr/bin/env python3
"""LoRa ingester: Node 3 (USB serial on the Pi) -> SQLite, transport='lora'.

Exits non-zero when the serial connection is lost, so systemd restarts it.
While running it owns Node 3's serial port: stop the service before using the
meshtastic CLI on Node 3.

Environment: EVDP_DB (database path), EVDP_LORA_PORT (Node 3's serial port).
"""

import sys
import threading
import time

from pubsub import pub
import meshtastic.serial_interface

from common import Store, log, node_id_from_num, require_env, setup_logging, to_json, wait_for_clock_sync

# On connect, Node 3 first hands over the packets it buffered while nothing was
# listening. Their received_at is the hand-over time, not the air time, so
# packets arriving in this window after connecting are stored as replayed.
STARTUP_REPLAY_S = 10

store = None
lost = threading.Event()
live_after = None  # monotonic time after which packets count as live


def on_receive(packet, interface):
    # Node 3 reports its own device metrics to the client over USB; skip them.
    my_info = getattr(interface, "myInfo", None)
    if my_info is not None and packet.get("from") == my_info.my_node_num:
        return
    try:
        handle(packet)
    except Exception:
        log.exception("failed to handle packet id=%s", packet.get("id"))


def handle(packet):
    if "from" not in packet:
        return
    node_id = node_id_from_num(packet["from"])
    if not store.is_known(node_id):
        return
    decoded = packet.get("decoded") or {}
    port = decoded.get("portnum")
    replayed = live_after is None or time.monotonic() < live_after

    common = dict(packet_id=packet.get("id"), node_id=node_id, transport="lora", raw=to_json(packet))
    hop_start, hop_limit = packet.get("hopStart"), packet.get("hopLimit")
    hops = hop_start - hop_limit if hop_start is not None and hop_limit is not None else None

    if port == "TELEMETRY_APP":
        tel = decoded.get("telemetry") or {}
        env = tel.get("environmentMetrics")
        dev = tel.get("deviceMetrics")
        if env and ("temperature" in env or "relativeHumidity" in env):
            new = store.add_reading(**common, hops=hops, replayed=replayed,
                                    rx_snr=packet.get("rxSnr"), rx_rssi=packet.get("rxRssi"),
                                    temperature=env.get("temperature"),
                                    humidity=env.get("relativeHumidity"))
            log.info("reading %s id=%s T=%s RH=%s hops=%s%s%s", node_id, common["packet_id"],
                     env.get("temperature"), env.get("relativeHumidity"), hops,
                     " replayed" if replayed else "", "" if new else " duplicate")
        elif dev:
            new = store.add_device_metrics(**common,
                                           battery_level=dev.get("batteryLevel"),
                                           voltage=dev.get("voltage"),
                                           channel_util=dev.get("channelUtilization"),
                                           air_util_tx=dev.get("airUtilTx"),
                                           uptime_secs=dev.get("uptimeSeconds"))
            log.info("device  %s id=%s batt=%s V=%s%s", node_id, common["packet_id"],
                     dev.get("batteryLevel"), dev.get("voltage"), "" if new else " duplicate")
    elif port == "NODEINFO_APP":
        user = decoded.get("user") or {}
        store.update_node(node_id, user.get("shortName"), user.get("longName"), user.get("hwModel"))


def on_lost(interface=None):
    log.error("serial connection lost")
    lost.set()


def main():
    global store, live_after
    setup_logging("lora")
    db_path = require_env("EVDP_DB")
    port = require_env("EVDP_LORA_PORT")
    wait_for_clock_sync()
    store = Store(db_path)
    pub.subscribe(on_receive, "meshtastic.receive")
    pub.subscribe(on_lost, "meshtastic.connection.lost")
    log.info("opening %s", port)
    iface = meshtastic.serial_interface.SerialInterface(devPath=port)
    live_after = time.monotonic() + STARTUP_REPLAY_S
    log.info("connected; packets in the next %d s are marked replayed", STARTUP_REPLAY_S)
    lost.wait()
    try:
        iface.close()
    except Exception:
        pass
    sys.exit(1)


if __name__ == "__main__":
    main()

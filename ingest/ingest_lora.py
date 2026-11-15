#!/usr/bin/env python3
"""LoRa ingester: Node 3 (USB on the Pi) -> SQLite, transport='lora'.

Every packet Node 3 hears over the air is delivered by the meshtastic library
already decrypted and decoded. Telemetry packets from the project's nodes are
stored; NodeInfo packets refresh the names in the nodes table.

Exits non-zero if the serial connection is lost, so systemd restarts it.
While this runs it owns Node 3's serial port: stop the service before using
the meshtastic CLI on Node 3.
"""

import os
import sys
import threading
import time

from pubsub import pub
import meshtastic.serial_interface

from common import (PROJECT_NODES, Store, log, node_id_from_num, setup_logging,
                    to_json, wait_for_clock_sync)

PORT = os.environ.get(
    "EVDP_LORA_PORT",
    "/dev/serial/by-id/usb-Espressif_Systems_seeed-xiao-s3_E83DC1FC83D0-if00",
)

store = None
lost = threading.Event()


def on_receive(packet, interface):
    # Skip Node 3's own packets. It reports its device metrics to the
    # connected client every minute over USB; those never cross the radio and
    # aren't part of the comparison.
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
    if node_id not in PROJECT_NODES:
        return
    decoded = packet.get("decoded") or {}
    port = decoded.get("portnum")

    common = dict(
        packet_id=packet.get("id"),
        node_id=node_id,
        transport="lora",
        packet_time=packet.get("rxTime"),
        gateway_id=None,
        raw=to_json(packet),
    )
    hop_start, hop_limit = packet.get("hopStart"), packet.get("hopLimit")
    hops = hop_start - hop_limit if hop_start is not None and hop_limit is not None else None

    if port == "TELEMETRY_APP":
        tel = decoded.get("telemetry") or {}
        env = tel.get("environmentMetrics")
        dev = tel.get("deviceMetrics")
        if env and ("temperature" in env or "relativeHumidity" in env):
            new = store.add_reading(**common, hops=hops,
                                    rx_snr=packet.get("rxSnr"), rx_rssi=packet.get("rxRssi"),
                                    temperature=env.get("temperature"),
                                    humidity=env.get("relativeHumidity"))
            log.info("reading %s id=%s T=%s RH=%s hops=%s snr=%s rssi=%s%s",
                     node_id, common["packet_id"], env.get("temperature"), env.get("relativeHumidity"),
                     hops, packet.get("rxSnr"), packet.get("rxRssi"), "" if new else " (duplicate)")
        elif dev:
            new = store.add_device_metrics(**common,
                                           battery_level=dev.get("batteryLevel"),
                                           voltage=dev.get("voltage"),
                                           channel_util=dev.get("channelUtilization"),
                                           air_util_tx=dev.get("airUtilTx"),
                                           uptime_secs=dev.get("uptimeSeconds"))
            log.info("device  %s id=%s batt=%s V=%s%s", node_id, common["packet_id"],
                     dev.get("batteryLevel"), dev.get("voltage"), "" if new else " (duplicate)")
    elif port == "NODEINFO_APP":
        user = decoded.get("user") or {}
        store.upsert_node(node_id, user.get("shortName"), user.get("longName"), user.get("hwModel"))
        log.info("nodeinfo %s %s / %s", node_id, user.get("longName"), user.get("shortName"))


def on_lost(interface=None):
    log.error("serial connection lost")
    lost.set()


def main():
    global store
    setup_logging("lora")
    wait_for_clock_sync()
    store = Store()
    pub.subscribe(on_receive, "meshtastic.receive")
    pub.subscribe(on_lost, "meshtastic.connection.lost")
    log.info("opening %s", PORT)
    iface = meshtastic.serial_interface.SerialInterface(devPath=PORT)
    me = iface.getMyNodeInfo() or {}
    log.info("connected to %s (%s)", (me.get("user") or {}).get("id"), (me.get("user") or {}).get("longName"))
    # Node 3 has no time source of its own (no GPS, no phone, no WiFi), so it
    # leaves rxTime empty. Give it the Pi's NTP time on every connect; from then
    # on rxTime (-> packet_time) records when the packet came off the air, which
    # stays correct even for packets the node buffered while the ingester was
    # down. received_at only records when the Pi got it over USB.
    #
    # The first setTime goes out while the node is still replaying packets it
    # buffered, and sits in that queue for 10-20 s: the node then applies an
    # already-stale timestamp (observed: rxTime a constant 10-21 s behind,
    # changing only at each restart). So set it again once the start-up queue
    # has drained, and every 6 h after that.
    def set_clock(reason):
        try:
            iface.localNode.setTime(int(time.time()))
            log.info("set node clock from the Pi (NTP): %s", reason)
        except Exception:
            log.exception("could not set node clock")

    def clock_loop():
        if lost.wait(60):
            return
        set_clock("after start-up queue drained")
        while not lost.wait(6 * 3600):
            set_clock("periodic")

    set_clock("on connect")
    threading.Thread(target=clock_loop, name="clock", daemon=True).start()
    lost.wait()
    try:
        iface.close()
    except Exception:
        pass
    sys.exit(1)


if __name__ == "__main__":
    main()

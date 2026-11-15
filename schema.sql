-- EVDP — Meshtastic environmental monitoring
-- SQLite schema for dual-transport telemetry ingestion.
--
-- Design notes:
--   * One row per DELIVERY, not per measurement. The same reading arriving by
--     both transports produces two rows sharing packet_id and node_id but
--     differing in transport. That duplication is deliberate — it is the
--     comparison the project exists to make.
--   * UNIQUE(packet_id, transport, node_id) collapses duplicates WITHIN a
--     transport (mesh rebroadcasts, MQTT redelivery) while preserving
--     duplicates ACROSS transports.

PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

-- ---------------------------------------------------------------- nodes ----
-- Registered project nodes. The ingesters only store packets from nodes listed here.

CREATE TABLE IF NOT EXISTS nodes (
  node_id    TEXT PRIMARY KEY,   -- e.g. '!a1f7f284'
  short_name TEXT,               -- e.g. 'N1'
  long_name  TEXT,               -- e.g. 'EVDP Node 1 LoRa'
  hw_model   TEXT,               -- e.g. 'SEEED_XIAO_S3'
  role       TEXT,               -- CLIENT / ROUTER
  location   TEXT,               -- deployment site, free text
  notes      TEXT
);

-- ------------------------------------------------------------- readings ----
-- Environment telemetry: temperature and relative humidity from the SHT40.

CREATE TABLE IF NOT EXISTS readings (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  received_at  TEXT    NOT NULL,          -- ISO-8601 UTC, when the Pi ingested
  packet_time  INTEGER,                   -- packet's own timestamp (epoch)
  packet_id    INTEGER,                   -- Meshtastic packet id
  node_id      TEXT    NOT NULL REFERENCES nodes(node_id),  -- originator
  transport    TEXT    NOT NULL CHECK (transport IN ('lora','mqtt')),
  gateway_id   TEXT,                      -- bridging node; NULL for lora
  hops         INTEGER,                   -- hop_start - hop_limit
  rx_snr       REAL,
  rx_rssi      INTEGER,
  temperature  REAL,                      -- degrees Celsius
  humidity     REAL,                      -- percent RH
  replayed     INTEGER NOT NULL DEFAULT 0,  -- 1: received_at is not the live arrival time
  raw          TEXT,                      -- original payload, for reprocessing
  UNIQUE(packet_id, transport, node_id)
);

-- -------------------------------------------------------- device_metrics ----
-- Device telemetry: battery, voltage and airtime utilisation.
-- Evidence for the solar power budget and for duty-cycle compliance.

CREATE TABLE IF NOT EXISTS device_metrics (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  received_at   TEXT    NOT NULL,
  packet_time   INTEGER,
  packet_id     INTEGER,
  node_id       TEXT    NOT NULL REFERENCES nodes(node_id),
  transport     TEXT    NOT NULL CHECK (transport IN ('lora','mqtt')),
  gateway_id    TEXT,
  battery_level INTEGER,                  -- percent; >100 indicates USB power
  voltage       REAL,
  channel_util  REAL,                     -- % airtime observed on channel
  air_util_tx   REAL,                     -- % airtime this node transmitted
  uptime_secs   INTEGER,
  raw           TEXT,
  UNIQUE(packet_id, transport, node_id)
);

-- ---------------------------------------------------------------- index ----

CREATE INDEX IF NOT EXISTS idx_readings_packet    ON readings(packet_id);
CREATE INDEX IF NOT EXISTS idx_readings_node_time ON readings(node_id, received_at);
CREATE INDEX IF NOT EXISTS idx_readings_transport ON readings(transport, received_at);
CREATE INDEX IF NOT EXISTS idx_dm_node_time       ON device_metrics(node_id, received_at);

-- ----------------------------------------------------------------- views ----

-- Latest reading per node, per transport — for the dashboard's status tiles.
CREATE VIEW IF NOT EXISTS latest_readings AS
SELECT r.node_id, n.long_name, n.short_name, r.transport,
       r.received_at, r.temperature, r.humidity, r.rx_snr, r.hops
FROM readings r
LEFT JOIN nodes n ON n.node_id = r.node_id
WHERE r.id IN (
  SELECT MAX(id) FROM readings GROUP BY node_id, transport
);

-- Path comparison: readings that arrived by BOTH transports, with the delay
-- between arrivals. This is the project's central analysis.
CREATE VIEW IF NOT EXISTS path_comparison AS
SELECT packet_id,
       node_id,
       MIN(received_at) AS first_arrival,
       MAX(received_at) AS last_arrival,
       (julianday(MAX(received_at)) - julianday(MIN(received_at))) * 86400.0
         AS delta_seconds,
       COUNT(*) AS path_count
FROM readings
WHERE packet_id IS NOT NULL
GROUP BY packet_id, node_id
HAVING COUNT(DISTINCT transport) > 1;

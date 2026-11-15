-- Adds readings.replayed and marks the rows from the 2026-11-15 bring-up whose
-- received_at is not a live arrival time: LoRa rows 1-3 were handed over from
-- Node 3's buffer, MQTT rows 4-6 were backfilled from a capture file.
ALTER TABLE readings ADD COLUMN replayed INTEGER NOT NULL DEFAULT 0;
UPDATE readings SET replayed = 1 WHERE id IN (1, 2, 3, 4, 5, 6);

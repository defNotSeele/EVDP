import { useMemo, useState } from "react";
import DeviceCard from "./Components/DeviceCard/DeviceCard.jsx";
import Panel from "../../Common/Panel/Panel.jsx";
import Segmented from "../../Common/Segmented/Segmented.jsx";
import TableView from "../../Common/TableView/TableView.jsx";
import TimeChart from "../../Common/TimeChart/TimeChart.jsx";
import { useEntry } from "../../lib/api.js";
import { formatFull, toMs } from "../../lib/time.js";
import "./Data.scss";

const RANGES = [
  { key: "6h", label: "6 h", ms: 6 * 3600e3 },
  { key: "24h", label: "24 h", ms: 24 * 3600e3 },
  { key: "7d", label: "7 days", ms: 7 * 86400e3 },
  { key: "all", label: "All", ms: null },
];

const ENERGY_METRICS = [
  { key: "battery_level", label: "Battery %", format: (v) => `${v.toFixed(0)} %`, y: { domain: [0, 100], ticks: [0, 25, 50, 75, 100] } },
  { key: "voltage", label: "Voltage", format: (v) => `${v.toFixed(2)} V` },
];

/** [{ device, data: [{ t, value, detail }] }] for the devices that have points. */
function seriesOf(devices, rows, pick, detail) {
  return devices
    .map((device) => ({
      device,
      data: rows
        .filter((r) => r.node_id === device.node_id && pick(r) != null)
        .map((r) => ({ t: toMs(r.time), value: pick(r), detail: detail?.(r) })),
    }))
    .filter((s) => s.data.length > 0);
}

export default function Data() {
  const [rangeKey, setRangeKey] = useState("6h");
  const [metricKey, setMetricKey] = useState("battery_level");
  const { data, error, loading } = useEntry(rangeKey);

  const devices = data?.devices ?? [];
  const range = useMemo(() => {
    const to = data ? toMs(data.server_time) : Date.now();
    const span = RANGES.find((r) => r.key === rangeKey).ms;
    if (span) return { from: to - span, to };
    const times = [...(data?.history ?? []), ...(data?.energy ?? [])].map((p) => toMs(p.time));
    return { from: times.length ? Math.min(...times) : to - 86400e3, to };
  }, [data, rangeKey]);

  const metric = ENERGY_METRICS.find((m) => m.key === metricKey);
  const energySeries = seriesOf(devices, data?.energy ?? [], (r) => r[metric.key]);

  return (
    <main className="page data-page">
      <header className="data-page__intro">
        <p className="data-page__kicker">Meshtastic weather collection project</p>
        <h1>Live data</h1>
        <p className="muted">
          Sensor nodes measure air temperature and humidity. Every reading travels to the collector
          twice: over the LoRa mesh and over WiFi/MQTT. <a href="/">About this project</a>
        </p>
      </header>

      <div className="data-page__filters">
        <Segmented label="Time range" options={RANGES} value={rangeKey} onChange={setRangeKey} />
        {error && <span role="alert" className="small">⚠ Could not refresh ({error}); showing the last data received.</span>}
      </div>

      <section className="data-page__cards" aria-label="Devices">
        {devices.map((d) => <DeviceCard key={d.node_id} device={d} reportIntervalS={data.report_interval_s} />)}
        {!data && !error && <p className="muted">Loading…</p>}
      </section>

      {data && (
        <div className={loading ? "data-page__charts is-refreshing" : "data-page__charts"}>
          <Panel title="Energy"
                 aside={<Segmented label="Energy metric" options={ENERGY_METRICS} value={metricKey} onChange={setMetricKey} />}>
            {energySeries.length > 0
              ? <TimeChart series={energySeries} range={range} format={metric.format} y={metric.y} />
              : <p className="muted small">No {metric.label.toLowerCase()} reported in this range.</p>}
            <TableView caption="Energy reports"
              columns={[{ key: "time", label: "Time" }, { key: "device", label: "Device" },
                        { key: "battery", label: "Battery", numeric: true }, { key: "voltage", label: "Voltage", numeric: true }]}
              rows={data.energy.slice().reverse().map((r) => ({
                time: formatFull(toMs(r.time)),
                device: devices.find((d) => d.node_id === r.node_id)?.short_name ?? r.node_id,
                battery: r.external_power ? "external" : r.battery_level == null ? "—" : `${r.battery_level} %`,
                voltage: r.voltage == null ? "—" : `${r.voltage.toFixed(2)} V`,
              }))} />
          </Panel>

          <div className="data-page__temps">
            {devices.filter((d) => d.has_sensor).map((device) => {
              const series = seriesOf([device], data.history, (r) => r.temperature,
                                      (r) => `${r.humidity.toFixed(0)} % rel. humidity`);
              return (
                <Panel key={device.node_id} title={`Temperature · ${device.short_name}`}>
                  {series.length > 0
                    ? <TimeChart series={series} range={range} format={(v) => `${v.toFixed(1)} °C`} axis={(v) => `${v}°`} />
                    : <p className="muted small">No readings in this range.</p>}
                  <TableView caption={`Temperature and humidity, ${device.short_name}`}
                    columns={[{ key: "time", label: "Time" }, { key: "temp", label: "°C", numeric: true },
                              { key: "rh", label: "%RH", numeric: true }]}
                    rows={data.history.filter((r) => r.node_id === device.node_id).reverse().map((r) => ({
                      time: formatFull(toMs(r.time)), temp: r.temperature.toFixed(2), rh: r.humidity.toFixed(1),
                    }))} />
                </Panel>
              );
            })}
          </div>
        </div>
      )}

      <footer className="muted small">Times shown in your local time zone. Updates every minute.</footer>
    </main>
  );
}

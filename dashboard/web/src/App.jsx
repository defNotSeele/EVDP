import { useMemo, useState } from "react";
import DeviceCard from "./components/DeviceCard.jsx";
import EnergyChart from "./components/EnergyChart.jsx";
import TempChart from "./components/TempChart.jsx";
import { useApi, useDarkMode } from "./lib.js";

const RANGES = [
  { key: "6h", label: "6 h", ms: 6 * 3600e3 },
  { key: "24h", label: "24 h", ms: 24 * 3600e3 },
  { key: "7d", label: "7 days", ms: 7 * 86400e3 },
  { key: "all", label: "All", ms: null },
];

export default function App() {
  const dark = useDarkMode();
  const [range, setRange] = useState("24h");
  const cards = useApi("/api/latest");
  const history = useApi(`/api/history?range=${range}`);
  const power = useApi(`/api/power?range=${range}`);

  // x-domain: the selected window ending now; "All" spans the data itself.
  const { from, to } = useMemo(() => {
    const now = Date.now();
    const r = RANGES.find((x) => x.key === range);
    if (r.ms) return { from: now - r.ms, to: now };
    const times = [...(history.data || []), ...(power.data || [])].map((p) => Date.parse(p.time));
    return { from: times.length ? Math.min(...times) : now - 86400e3, to: now };
  }, [range, history.data, power.data]);

  const cardList = cards.data || [];
  const devices = cardList; // repeater + sensor nodes, in card order
  const sensors = cardList.filter((c) => c.has_sensor);
  const refetching = history.loading || power.loading;
  const error = cards.error || history.error || power.error;

  return (
    <main className="page">
      <header style={{ display: "grid", gap: 8 }}>
        <div className="eyebrow">EVDP · Meshtastic environmental monitoring</div>
        <h1>Live data</h1>
        <p className="muted">
          Two sensor nodes measure air temperature and humidity. Every reading travels to the
          collector twice: over the LoRa mesh and over WiFi/MQTT. <a href="/">About this project</a>
        </p>
      </header>

      <div className="filters" role="group" aria-label="Time range">
        <div className="seg">
          {RANGES.map((r) => (
            <button key={r.key} aria-pressed={range === r.key} onClick={() => setRange(r.key)}>{r.label}</button>
          ))}
        </div>
        {error && <span role="alert" className="small"><span aria-hidden="true">⚠ </span>Could not load data ({error}); showing the last data received.</span>}
      </div>

      <section className="cards" aria-label="Devices">
        {cardList.map((c) => <DeviceCard key={c.node_id} card={c} dark={dark} />)}
        {!cards.data && !cards.error && <p className="muted">Loading…</p>}
      </section>

      <div className={refetching ? "refetching" : ""} style={{ display: "grid", gap: 12 }}>
        {power.data && devices.length > 0 && (
          <EnergyChart power={power.data} devices={devices} from={from} to={to} dark={dark} />
        )}
        <div className="charts-2">
          {history.data && sensors.map((n) => (
            <TempChart key={n.node_id} node={n} history={history.data} from={from} to={to} dark={dark} />
          ))}
        </div>
      </div>

      <footer className="muted small">Times in Europe/Amsterdam. Updates every minute.</footer>
    </main>
  );
}

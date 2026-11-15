import { useState } from "react";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { ChartTooltip, LineLegend, TableView } from "./ChartBits.jsx";
import { formatFull, formatTick, seriesColor, timeTicks, toMs, valueTicks } from "../lib.js";

const METRICS = {
  battery: { label: "Battery %", unit: "%", domain: [0, 100], digits: 0 },
  voltage: { label: "Voltage", unit: "V", domain: ["auto", "auto"], digits: 2 },
};

/** One line per device. Readings on external power (battery_level > 100) are
 *  not plotted as a percentage: there is no battery state to show. */
export default function EnergyChart({ power, devices, from, to, dark }) {
  // Open on Battery % only if some device actually reports a battery level.
  const hasBattery = power.some((p) => p.battery_level != null && !p.external_power);
  const [metric, setMetric] = useState(hasBattery ? "battery" : "voltage");
  const m = METRICS[metric];
  const ids = devices.map((d) => d.node_id);

  const rows = [];
  for (const p of power) {
    if (!ids.includes(p.node_id)) continue;
    const v = metric === "battery" ? (p.external_power ? null : p.battery_level) : p.voltage;
    rows.push({ t: toMs(p.time), [p.node_id]: v });
  }
  rows.sort((a, b) => a.t - b.t);

  const onExternal = devices.filter((d) => power.some((p) => p.node_id === d.node_id && p.external_power));
  const span = to - from;
  const grid = dark ? "#2c2c2a" : "#e1e0d9";
  const axis = dark ? "#383835" : "#c3c2b7";
  const tick = { fill: "#898781", fontSize: 12 };
  const surface = dark ? "#1a1a19" : "#fcfcfb";
  const vals = rows.flatMap((r) => ids.map((id) => r[id])).filter((v) => v != null);
  const y = metric === "battery" ? { domain: [0, 100], ticks: [0, 25, 50, 75, 100], decimals: 0 }
    : valueTicks(Math.min(...vals), Math.max(...vals));

  return (
    <section className="card section" aria-labelledby="energy-h">
      <div className="section-head">
        <h2 id="energy-h">Energy</h2>
        <div className="seg" role="group" aria-label="Energy metric">
          {Object.entries(METRICS).map(([k, v]) => (
            <button key={k} aria-pressed={metric === k} onClick={() => setMetric(k)}>{v.label}</button>
          ))}
        </div>
      </div>
      <LineLegend items={devices.map((d) => ({
        key: d.node_id, color: seriesColor(d.node_id, dark),
        label: d.role === "ROUTER" ? `${d.short_name} (repeater)` : d.short_name,
      }))} />
      <div style={{ width: "100%", height: 240 }}>
        <ResponsiveContainer>
          <LineChart data={rows} margin={{ top: 8, right: 16, bottom: 4, left: 0 }}>
            <CartesianGrid stroke={grid} vertical={false} />
            <XAxis dataKey="t" type="number" scale="time" domain={[from, to]} ticks={timeTicks(from, to)}
                   tickFormatter={(v) => formatTick(v, span)} stroke={axis} tick={tick} tickLine={false} />
            <YAxis domain={y.domain} ticks={y.ticks} stroke={axis} tick={tick} tickLine={false} width={40}
                   tickFormatter={(v) => Number(v).toFixed(y.decimals)} />
            <Tooltip cursor={{ stroke: axis, strokeWidth: 1 }}
                     content={<ChartTooltip rows={(payload) => payload.filter((p) => p.value != null).map((p) => ({
                       color: p.color, name: devices.find((d) => d.node_id === p.dataKey)?.short_name,
                       value: `${Number(p.value).toFixed(m.digits)} ${m.unit}`,
                     }))} />} />
            {devices.map((d) => (
              <Line key={d.node_id} dataKey={d.node_id} name={d.short_name} type="linear"
                    stroke={seriesColor(d.node_id, dark)} strokeWidth={2} connectNulls isAnimationActive={false}
                    dot={{ r: 4, fill: seriesColor(d.node_id, dark), stroke: surface, strokeWidth: 2 }}
                    activeDot={{ r: 5, stroke: surface, strokeWidth: 2 }} />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
      {metric === "battery" && onExternal.length > 0 && (
        <p className="muted small">
          On external (USB) power, so no battery level to plot: {onExternal.map((d) => d.short_name).join(", ")}.
          Switch to Voltage to see them.
        </p>
      )}
      <TableView caption="Energy reports"
        columns={[{ key: "time", label: "Time" }, { key: "dev", label: "Device" },
                  { key: "batt", label: "Battery", num: true }, { key: "volt", label: "Voltage", num: true }]}
        rows={power.filter((p) => ids.includes(p.node_id)).slice().reverse().map((p) => ({
          time: formatFull(toMs(p.time)),
          dev: devices.find((d) => d.node_id === p.node_id)?.short_name,
          batt: p.external_power ? "external" : p.battery_level == null ? "—" : `${p.battery_level} %`,
          volt: p.voltage == null ? "—" : `${p.voltage.toFixed(2)} V`,
        }))} />
    </section>
  );
}

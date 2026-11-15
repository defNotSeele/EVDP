import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { ChartTooltip, TableView } from "./ChartBits.jsx";
import { formatFull, formatTick, seriesColor, timeTicks, toMs, valueTicks } from "../lib.js";

/** One node, one series: the title names it, so no legend box. The tooltip
 *  also carries humidity, which arrives in the same packet. */
export default function TempChart({ node, history, from, to, dark }) {
  const rows = history
    .filter((h) => h.node_id === node.node_id)
    .map((h) => ({ t: toMs(h.time), temperature: h.temperature, humidity: h.humidity }));
  const color = seriesColor(node.node_id, dark);
  const span = to - from;
  const grid = dark ? "#2c2c2a" : "#e1e0d9";
  const axis = dark ? "#383835" : "#c3c2b7";
  const tick = { fill: "#898781", fontSize: 12 };
  const surface = dark ? "#1a1a19" : "#fcfcfb";
  const last = rows[rows.length - 1];
  const temps = rows.map((r) => r.temperature);
  const y = valueTicks(Math.min(...temps), Math.max(...temps));
  const hid = `temp-${node.short_name}`;

  return (
    <section className="card section" aria-labelledby={hid}>
      <div className="section-head">
        <h2 id={hid}>Temperature · {node.short_name}</h2>
        <span className="muted small">
          {last ? `${last.temperature.toFixed(1)} °C at ${formatFull(last.t)}` : "no readings in this range"}
        </span>
      </div>
      <div style={{ width: "100%", height: 220 }}>
        <ResponsiveContainer>
          <LineChart data={rows} margin={{ top: 8, right: 44, bottom: 4, left: 0 }}>
            <CartesianGrid stroke={grid} vertical={false} />
            <XAxis dataKey="t" type="number" scale="time" domain={[from, to]} ticks={timeTicks(from, to)}
                   tickFormatter={(v) => formatTick(v, span)} stroke={axis} tick={tick} tickLine={false} />
            <YAxis domain={y.domain} ticks={y.ticks} stroke={axis} tick={tick} tickLine={false} width={40}
                   tickFormatter={(v) => `${v}°`} />
            <Tooltip cursor={{ stroke: axis, strokeWidth: 1 }}
                     content={<ChartTooltip rows={(payload) => {
                       const d = payload[0]?.payload;
                       return d ? [
                         { color, value: `${d.temperature.toFixed(1)} °C`, name: "temperature" },
                         { value: `${d.humidity.toFixed(0)} %`, name: "rel. humidity" },
                       ] : [];
                     }} />} />
            <Line dataKey="temperature" type="linear" stroke={color} strokeWidth={2} isAnimationActive={false}
                  dot={rows.length <= 60 ? { r: 4, fill: color, stroke: surface, strokeWidth: 2 } : false}
                  activeDot={{ r: 5, stroke: surface, strokeWidth: 2 }}
                  label={(p) => p.index === rows.length - 1
                    ? <text x={p.x + 8} y={p.y + 4} fontSize={12} fill={dark ? "#f0efec" : "#0b0b0b"}>{`${p.value.toFixed(1)}°`}</text>
                    : null} />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <TableView caption={`Temperature and humidity, ${node.short_name}`}
        columns={[{ key: "time", label: "Time" }, { key: "temp", label: "°C", num: true }, { key: "rh", label: "%RH", num: true }]}
        rows={rows.slice().reverse().map((r) => ({
          time: formatFull(r.t), temp: r.temperature.toFixed(2), rh: r.humidity.toFixed(1),
        }))} />
    </section>
  );
}

import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import ChartTooltip from "../ChartTooltip/ChartTooltip.jsx";
import Legend from "../Legend/Legend.jsx";
import { useTheme } from "../../theme/ThemeContext.jsx";
import { formatTick, timeTicks, valueTicks } from "../../lib/time.js";
import "./TimeChart.scss";

/**
 * Line chart over time, one line per device.
 *
 *   series  [{ device: { node_id, short_name, slot }, data: [{ t, value, detail? }] }]
 *   range   { from, to } in ms
 *   format  value -> label used in the tooltip and the end label
 *   axis    value -> y-axis tick label
 *   y       optional fixed { domain, ticks }; otherwise fitted to the data
 *
 * A single series needs no legend (the panel title names it) and gets an end label.
 */
export default function TimeChart({ series, range, format, axis = String, y }) {
  const { colors } = useTheme();
  const byTime = new Map();
  for (const { device, data } of series) {
    for (const p of data) {
      const row = byTime.get(p.t) || { t: p.t };
      row[device.node_id] = p.value;
      if (p.detail) row[`${device.node_id}:detail`] = p.detail;
      byTime.set(p.t, row);
    }
  }
  const rows = [...byTime.values()].sort((a, b) => a.t - b.t);
  const yAxis = y || valueTicks(series.flatMap((s) => s.data.map((p) => p.value)));
  const single = series.length === 1;
  const tick = { fill: colors.muted, fontSize: 12 };
  const dot = (color) => ({ r: 4, fill: color, stroke: colors.surface, strokeWidth: 2 });

  const tooltipRows = (payload) =>
    payload.filter((p) => p.value != null).flatMap((p) => {
      const device = series.find((s) => s.device.node_id === p.dataKey).device;
      const detail = p.payload[`${p.dataKey}:detail`];
      return [
        { slot: device.slot, value: format(p.value), name: device.short_name },
        ...(detail ? [{ value: detail }] : []),
      ];
    });

  return (
    <div className="time-chart">
      {!single && <Legend items={series.map((s) => s.device)} />}
      <div className="time-chart__plot">
        <ResponsiveContainer>
          <LineChart data={rows} margin={{ top: 8, right: single ? 48 : 16, bottom: 4, left: 0 }}>
            <CartesianGrid stroke={colors.grid} vertical={false} />
            <XAxis dataKey="t" type="number" scale="time" domain={[range.from, range.to]} ticks={timeTicks(range)}
                   tickFormatter={(v) => formatTick(v, range.to - range.from)}
                   stroke={colors.axis} tick={tick} tickLine={false} />
            <YAxis domain={yAxis.domain} ticks={yAxis.ticks} tickFormatter={axis}
                   stroke={colors.axis} tick={tick} tickLine={false} width={44} />
            <Tooltip cursor={{ stroke: colors.axis, strokeWidth: 1 }}
                     content={<ChartTooltip rows={tooltipRows} />} />
            {series.map(({ device }) => {
              const color = colors.series(device.slot);
              return (
                <Line key={device.node_id} dataKey={device.node_id} name={device.short_name}
                      type="linear" connectNulls isAnimationActive={false}
                      stroke={color} strokeWidth={2} dot={rows.length <= 60 && dot(color)}
                      activeDot={{ ...dot(color), r: 5 }}
                      label={single ? (p) => p.index === rows.length - 1 && (
                        <text x={p.x + 8} y={p.y + 4} fontSize={12} fill={colors.text}>{format(p.value)}</text>
                      ) : undefined} />
              );
            })}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

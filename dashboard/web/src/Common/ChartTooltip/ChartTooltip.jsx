import { formatFull } from "../../lib/time.js";
import "./ChartTooltip.scss";

/** Values lead, names follow; each series keyed by a short stroke of its colour. */
export default function ChartTooltip({ active, payload, label, rows }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="chart-tooltip">
      <div className="chart-tooltip__time">{formatFull(label)}</div>
      {rows(payload).map((row, i) => (
        <div key={i} className="chart-tooltip__row">
          <span className={row.slot != null ? `chart-tooltip__key slot-${row.slot}` : "chart-tooltip__key"} />
          <strong>{row.value}</strong>
          {row.name && <span className="chart-tooltip__name">{row.name}</span>}
        </div>
      ))}
    </div>
  );
}

import { formatFull } from "../lib.js";

/** Tooltip: values lead (strong), series names follow (secondary), each row keyed
 *  by a short stroke of the series colour. Text never wears the series colour. */
export function ChartTooltip({ active, payload, label, rows }) {
  if (!active || !payload || !payload.length) return null;
  const items = rows ? rows(payload) : payload.map((p) => ({
    color: p.color, value: p.value, name: p.name,
  }));
  return (
    <div style={{
      background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 8,
      padding: "8px 10px", fontSize: 13, boxShadow: "0 2px 8px rgba(0,0,0,0.12)",
    }}>
      <div className="muted" style={{ marginBottom: 4 }}>{formatFull(label)}</div>
      {items.map((it, i) => (
        <div key={i} style={{ display: "flex", alignItems: "center", gap: 8 }}>
          {it.color && <span aria-hidden="true" style={{ width: 12, height: 2, background: it.color, borderRadius: 1 }} />}
          <strong style={{ fontWeight: 600 }}>{it.value}</strong>
          <span className="muted">{it.name}</span>
        </div>
      ))}
    </div>
  );
}

/** Legend that mirrors the mark (a line key for line charts); text in text tokens. */
export function LineLegend({ items }) {
  return (
    <ul style={{ display: "flex", flexWrap: "wrap", gap: "4px 16px", listStyle: "none", margin: 0, padding: 0, fontSize: 13 }}>
      {items.map((it) => (
        <li key={it.key} style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <span aria-hidden="true" style={{ width: 16, height: 2, background: it.color, borderRadius: 1 }} />
          <span className="muted">{it.label}</span>
        </li>
      ))}
    </ul>
  );
}

/** Every chart's values are reachable without hovering. */
export function TableView({ columns, rows, caption }) {
  return (
    <details className="table-view">
      <summary>Show table</summary>
      <div className="table-scroll">
        <table className="data">
          <caption style={{ position: "absolute", left: -9999 }}>{caption}</caption>
          <thead>
            <tr>{columns.map((c) => <th key={c.key} className={c.num ? "num" : ""}>{c.label}</th>)}</tr>
          </thead>
          <tbody>
            {rows.length === 0 && <tr><td colSpan={columns.length} className="muted">No data in this range.</td></tr>}
            {rows.map((r, i) => (
              <tr key={i}>{columns.map((c) => <td key={c.key} className={c.num ? "num" : ""}>{r[c.key]}</td>)}</tr>
            ))}
          </tbody>
        </table>
      </div>
    </details>
  );
}

import "./TableView.scss";

/** The numbers behind a chart, reachable without hovering. */
export default function TableView({ caption, columns, rows }) {
  return (
    <details className="table-view">
      <summary>Show table</summary>
      <div className="table-view__scroll">
        <table>
          <caption>{caption}</caption>
          <thead>
            <tr>{columns.map((c) => <th key={c.key} className={c.numeric ? "numeric" : undefined}>{c.label}</th>)}</tr>
          </thead>
          <tbody>
            {rows.length === 0 && <tr><td colSpan={columns.length}>No data in this range.</td></tr>}
            {rows.map((r, i) => (
              <tr key={i}>
                {columns.map((c) => <td key={c.key} className={c.numeric ? "numeric" : undefined}>{r[c.key]}</td>)}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </details>
  );
}

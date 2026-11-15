import "./Legend.scss";

/** Line keys in each device's colour; the text stays in text colours. */
export default function Legend({ items }) {
  return (
    <ul className="legend">
      {items.map((d) => (
        <li key={d.node_id} className={`legend__item slot-${d.slot}`}>
          <span className="legend__key" aria-hidden="true" />
          {d.role === "ROUTER" ? `${d.short_name} (repeater)` : d.short_name}
        </li>
      ))}
    </ul>
  );
}

import "./Panel.scss";

/** A titled card: heading, optional controls or note on the right, then content. */
export default function Panel({ title, aside, children }) {
  return (
    <section className="panel">
      <header className="panel__head">
        <h2>{title}</h2>
        {aside && <div className="panel__aside">{aside}</div>}
      </header>
      {children}
    </section>
  );
}

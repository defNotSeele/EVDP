import "./Block.scss";

/** A titled section of running text. */
export default function Block({ title, children }) {
  return (
    <section className="block">
      <h2>{title}</h2>
      {children}
    </section>
  );
}

import { formatAge, seriesColor, viaLabel } from "../lib.js";

function Swatch({ color }) {
  return <span aria-hidden="true" style={{
    display: "inline-block", width: 10, height: 10, borderRadius: "50%",
    background: color, flex: "none",
  }} />;
}

function Stale({ show, what }) {
  if (!show) return null;
  return (
    <div role="status" style={{
      display: "flex", gap: 6, alignItems: "center", fontSize: 13, color: "var(--text-primary)",
    }}>
      <span aria-hidden="true" style={{ color: "var(--warning)", fontWeight: 700 }}>⚠</span>
      No {what} for over 45 min
    </div>
  );
}

function Row({ label, children }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", gap: 12, fontSize: 13 }}>
      <span className="muted">{label}</span>
      <span style={{ textAlign: "right" }}>{children}</span>
    </div>
  );
}

function Energy({ energy }) {
  if (!energy) return <Row label="Energy"><span className="muted">no report yet</span></Row>;
  const level = energy.external_power
    ? "external power"
    : energy.battery_level == null ? "—" : `${energy.battery_level} %`;
  return (
    <>
      <Row label="Battery">{level}</Row>
      <Row label="Voltage">{energy.voltage == null ? "—" : `${energy.voltage.toFixed(2)} V`}</Row>
      <Row label="Energy report">{formatAge(energy.age_s)}</Row>
    </>
  );
}

export default function DeviceCard({ card, dark }) {
  const isRepeater = card.role === "ROUTER";
  const r = card.reading;
  const lastVia = r ? viaLabel(r.via_lora, r.via_mqtt)
    : card.energy ? viaLabel(card.energy.via_lora, card.energy.via_mqtt) : "—";
  const lastAge = r ? r.age_s : card.energy?.age_s;

  return (
    <article className="card" style={{ display: "grid", gap: 12, alignContent: "start" }}
             aria-label={`${card.short_name} ${isRepeater ? "repeater" : "sensor node"}`}>
      <header style={{ display: "grid", gap: 2 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <Swatch color={seriesColor(card.node_id, dark)} />
          <h2 style={{ fontSize: 16 }}>{isRepeater ? `Repeater · ${card.short_name}` : card.short_name}</h2>
        </div>
        <div className="muted small">{card.long_name}</div>
      </header>

      {r ? (
        <div style={{ display: "flex", gap: 20, alignItems: "baseline", flexWrap: "wrap" }}>
          <div>
            <div style={{ fontSize: 32, fontWeight: 600, lineHeight: 1.1 }}>{r.temperature.toFixed(1)} °C</div>
            <div className="muted small">temperature</div>
          </div>
          <div>
            <div style={{ fontSize: 22, fontWeight: 600, lineHeight: 1.1 }}>{r.humidity.toFixed(0)} %</div>
            <div className="muted small">rel. humidity</div>
          </div>
        </div>
      ) : isRepeater ? (
        <p className="muted small">Relays the sensor nodes' packets across the mesh. No sensor of its own.</p>
      ) : null}

      <div style={{ display: "grid", gap: 4 }}>
        {lastAge == null
          ? <Row label="Last message"><span className="muted">not heard yet</span></Row>
          : <>
              <Row label="Last message via">{lastVia}</Row>
              <Row label="Received">{formatAge(lastAge)}</Row>
            </>}
        <Energy energy={card.energy} />
      </div>

      <Stale show={r?.stale} what="reading" />
    </article>
  );
}

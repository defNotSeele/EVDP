const CONTACT_PHONE = "+31616998168";

function Block({ title, children }) {
  return (
    <section className="section">
      <h2>{title}</h2>
      {children}
    </section>
  );
}

export default function About() {
  return (
    <main className="page" style={{ maxWidth: 720 }}>
      <header style={{ display: "grid", gap: 10 }}>
        <div className="eyebrow">Saxion · Embedded Vision · student project</div>
        <h1>You found a weather sensor</h1>
        <p className="muted">
          This small box measures the air temperature and humidity here, and sends the readings
          over a low-power radio network. It is part of a university student project.
        </p>
        <a href="/data" className="card" style={{
          display: "flex", justifyContent: "space-between", alignItems: "center",
          textDecoration: "none", fontWeight: 600, fontSize: 17, color: "var(--text-primary)",
        }}>
          See the live data <span aria-hidden="true">→</span>
        </a>
      </header>

      <Block title="What it does">
        <p>
          Every 30 minutes a sensor records temperature and relative humidity. The reading travels
          to a small computer by two independent routes: hop by hop over a LoRa radio mesh
          (Meshtastic), and over WiFi to a message broker. The project compares the two routes on the
          same readings, to show how a mesh network keeps working when one route fails.
        </p>
      </Block>

      <Block title="What it collects, and what it doesn't">
        <ul style={{ margin: 0, paddingLeft: 20, display: "grid", gap: 4 }}>
          <li>Air temperature and humidity, and the devices' own battery and signal data.</li>
          <li><strong>No personal data.</strong> No camera, no microphone, nothing that identifies you.</li>
          <li>Other people's radio devices nearby may be heard, but their data is discarded and never stored.</li>
          <li>The network is private and encrypted; locations are not published.</li>
        </ul>
      </Block>

      <Block title="How the data is used">
        <p>
          For teaching and for the project report only. The readings are shown publicly on the
          live data page. Nothing is sold or shared with third parties.
        </p>
      </Block>

      <Block title="Please leave it in place">
        <p>
          The box runs on solar power and needs no attention. If it is damaged, in the way, or you
          have questions, please get in touch.
        </p>
      </Block>

      <Block title="Contact">
        <p>
          Phone: <a href={`tel:${CONTACT_PHONE}`}>{CONTACT_PHONE}</a>
        </p>
      </Block>
    </main>
  );
}

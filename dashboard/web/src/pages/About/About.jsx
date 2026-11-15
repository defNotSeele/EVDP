import Block from "./Components/Block/Block.jsx";
import "./About.scss";

const CONTACT_PHONE = "+31616998168";

export default function About() {
  return (
    <main className="page about-page">
      <header className="about-page__intro">
        <p className="about-page__kicker">Meshtastic weather collection project</p>
        <h1>You found a weather sensor</h1>
        <p className="muted">
          This small box measures the air temperature and humidity here and sends the readings over
          a low-power radio network. It is part of a student project.
        </p>
        <a className="about-page__cta" href="/data">See the live data <span aria-hidden="true">→</span></a>
      </header>

      <Block title="What it does">
        <p>
          Every 30 minutes a sensor records temperature and relative humidity. The reading travels to
          a small computer by two independent routes: hop by hop over a LoRa radio mesh, and over
          WiFi to a message broker. The project compares the two routes on the same readings, to
          show how a mesh network keeps working when one route fails.
        </p>
        <p>
          The radio network runs on <a href="https://meshtastic.org" rel="noopener">Meshtastic</a>, open-source
          firmware for long-range, off-grid messaging. <a href="https://meshtastic.org/docs/introduction/" rel="noopener">Learn more</a>
        </p>
      </Block>

      <Block title="How the data is used">
        <p>
          For the project and its report only. The readings are shown publicly on the live data page.
          Nothing is sold or shared with third parties.
        </p>
      </Block>

      <Block title="Please leave it in place">
        <p>
          The box needs no attention. If it is damaged, in the way, or you have questions, please get
          in touch here: <a href={`tel:${CONTACT_PHONE}`}>{CONTACT_PHONE}</a>
        </p>
      </Block>
    </main>
  );
}

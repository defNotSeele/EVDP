import { formatWhen } from "../../../../lib/time.js";
import "./DeviceCard.scss";

function via(status) {
  if (status.via_lora && status.via_mqtt) return "Mesh (LoRa) + MQTT";
  return status.via_lora ? "Mesh (LoRa) only" : "MQTT only";
}

function Row({ label, children }) {
  return (
    <div className="device-card__row">
      <span>{label}</span>
      <span>{children}</span>
    </div>
  );
}

function Overdue({ status, intervalMin }) {
  if (!status?.overdue) return null;
  return (
    <p className="device-card__overdue" role="status">
      <span aria-hidden="true">⚠</span> Overdue, expected every {intervalMin} min
    </p>
  );
}

/** One field device: latest reading (sensor nodes), how it arrived, and energy. */
export default function DeviceCard({ device, reportIntervalS }) {
  const { reading, energy } = device;
  const last = reading || energy;
  const intervalMin = Math.round(reportIntervalS / 60);
  const isRepeater = device.role === "ROUTER";

  return (
    <article className={`device-card slot-${device.slot}`}>
      <header>
        <h2><span className="device-card__swatch" aria-hidden="true" />{isRepeater ? `Repeater · ${device.short_name}` : device.short_name}</h2>
        <p className="device-card__name">{device.long_name}</p>
      </header>

      {reading && (
        <div className="device-card__reading">
          <div><strong className="device-card__temp">{reading.temperature.toFixed(1)} °C</strong>temperature</div>
          <div><strong className="device-card__rh">{reading.humidity.toFixed(0)} %</strong>rel. humidity</div>
        </div>
      )}
      {isRepeater && <p className="device-card__note">Relays the sensor nodes' packets across the mesh.</p>}

      <div className="device-card__rows">
        {last ? (
          <>
            <Row label="Last message">{formatWhen(last.time, last.age_s)}</Row>
            <Row label="Received via">{via(last)}</Row>
          </>
        ) : (
          <Row label="Last message">not heard yet</Row>
        )}
        <Row label="Battery">
          {!energy ? "no report yet" : energy.external_power ? "external power"
            : energy.battery_level == null ? "not measured" : `${energy.battery_level} %`}
        </Row>
        {energy?.voltage != null && <Row label="Voltage">{energy.voltage.toFixed(2)} V</Row>}
      </div>

      <Overdue status={reading} intervalMin={intervalMin} />
    </article>
  );
}

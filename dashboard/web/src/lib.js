import { useEffect, useRef, useState } from "react";

// Fixed colour per device (never reassigned by rank or filter). Validated with
// the dataviz palette script in both modes (all-pairs, 3 slots).
export const SERIES = {
  "!a1f7f284": { light: "#2a78d6", dark: "#3987e5" }, // N1  blue
  "!a1f7f770": { light: "#eb6834", dark: "#d95926" }, // N2  orange
  "!084fbf75": { light: "#1baf7a", dark: "#199e70" }, // Sax1 aqua (repeater)
};

export function useDarkMode() {
  const query = "(prefers-color-scheme: dark)";
  const read = () => {
    const stamp = document.documentElement.dataset.theme;
    if (stamp === "dark") return true;
    if (stamp === "light") return false;
    return window.matchMedia(query).matches;
  };
  const [dark, setDark] = useState(read);
  useEffect(() => {
    const mq = window.matchMedia(query);
    const on = () => setDark(read());
    mq.addEventListener("change", on);
    const obs = new MutationObserver(on);
    obs.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
    return () => { mq.removeEventListener("change", on); obs.disconnect(); };
  }, []);
  return dark;
}

export function seriesColor(nodeId, dark) {
  const s = SERIES[nodeId];
  return s ? (dark ? s.dark : s.light) : "#898781";
}

/** Fetch JSON and re-poll every `intervalMs`. While refetching, the previous
 *  data stays on screen (no skeleton flash); `loading` lets the caller dim it. */
export function useApi(path, intervalMs = 60000) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);
  const seq = useRef(0);
  useEffect(() => {
    let timer;
    const load = async () => {
      const my = ++seq.current;
      setLoading(true);
      try {
        const res = await fetch(path, { cache: "no-store" });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const json = await res.json();
        if (my === seq.current) { setData(json); setError(null); }
      } catch (e) {
        if (my === seq.current) setError(String(e.message || e));
      } finally {
        if (my === seq.current) setLoading(false);
      }
    };
    load();
    timer = setInterval(load, intervalMs);
    return () => clearInterval(timer);
  }, [path, intervalMs]);
  return { data, error, loading };
}

const TZ = "Europe/Amsterdam";
const fmtTime = new Intl.DateTimeFormat("en-GB", { timeZone: TZ, hour: "2-digit", minute: "2-digit" });
const fmtDay = new Intl.DateTimeFormat("en-GB", { timeZone: TZ, day: "numeric", month: "short" });
const fmtFull = new Intl.DateTimeFormat("en-GB", {
  timeZone: TZ, day: "numeric", month: "short", hour: "2-digit", minute: "2-digit",
});

export const toMs = (iso) => Date.parse(iso);

/** Offset of Europe/Amsterdam from UTC at `ms`, in ms (handles DST). */
function tzOffset(ms) {
  const parts = Object.fromEntries(new Intl.DateTimeFormat("en-US", {
    timeZone: TZ, hourCycle: "h23", year: "numeric", month: "2-digit", day: "2-digit",
    hour: "2-digit", minute: "2-digit", second: "2-digit",
  }).formatToParts(ms).map((p) => [p.type, p.value]));
  const asUtc = Date.UTC(+parts.year, +parts.month - 1, +parts.day, +parts.hour, +parts.minute, +parts.second);
  return asUtc - Math.floor(ms / 1000) * 1000;
}

const HOUR = 3600e3;
const TIME_STEPS = [0.25, 0.5, 1, 2, 3, 6, 12, 24, 48, 168].map((h) => h * HOUR);

/** Evenly spaced time ticks on round local hours/days, about `target` of them. */
export function timeTicks(from, to, target = 6) {
  const span = to - from;
  const step = TIME_STEPS.find((s) => span / s <= target) || TIME_STEPS[TIME_STEPS.length - 1];
  const off = tzOffset(from);
  let t = Math.ceil((from + off) / step) * step - off;
  const out = [];
  for (; t <= to; t += step) out.push(t);
  return out;
}

/** Round value ticks (1/2/5 × 10^n steps) covering [min, max], with the domain to match. */
export function valueTicks(min, max, target = 4) {
  if (!isFinite(min) || !isFinite(max)) return { ticks: [0, 1], domain: [0, 1], decimals: 0 };
  if (min === max) { min -= 1; max += 1; }
  const raw = (max - min) / target;
  const mag = 10 ** Math.floor(Math.log10(raw));
  const step = [1, 2, 5, 10].map((m) => m * mag).find((s) => s >= raw);
  const lo = Math.floor(min / step) * step;
  const hi = Math.ceil(max / step) * step;
  const ticks = [];
  for (let v = lo; v <= hi + step / 2; v += step) ticks.push(+v.toFixed(6));
  const decimals = Math.max(0, -Math.floor(Math.log10(step) + 1e-9));
  return { ticks, domain: [lo, hi], decimals };
}
export const formatTick = (ms, spanMs) => (spanMs > 36 * 3600e3 ? fmtDay.format(ms) : fmtTime.format(ms));
export const formatFull = (ms) => fmtFull.format(ms);

export function formatAge(seconds) {
  if (seconds == null) return "—";
  if (seconds < 90) return "just now";
  const m = Math.round(seconds / 60);
  if (m < 90) return `${m} min ago`;
  const h = Math.round(m / 60);
  if (h < 36) return `${h} h ago`;
  return `${Math.round(h / 24)} days ago`;
}

export function viaLabel(viaLora, viaMqtt) {
  if (viaLora && viaMqtt) return "Mesh (LoRa) + MQTT";
  if (viaLora) return "Mesh (LoRa) only";
  if (viaMqtt) return "MQTT only";
  return "—";
}

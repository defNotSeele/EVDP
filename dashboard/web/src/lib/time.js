import { scaleLinear, scaleTime } from "d3-scale";

// Everything is shown in the viewer's own time zone.
const clock = new Intl.DateTimeFormat("en-GB", { hour: "2-digit", minute: "2-digit" });
const day = new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short" });
const full = new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });

export const toMs = (iso) => Date.parse(iso);
export const formatClock = (ms) => clock.format(ms);
export const formatFull = (ms) => full.format(ms);
export const formatTick = (ms, spanMs) => (spanMs > 36 * 3600e3 ? day : clock).format(ms);

export const timeTicks = ({ from, to }) => scaleTime().domain([from, to]).ticks(6).map(Number);

export function valueTicks(values) {
  const finite = values.filter(Number.isFinite);
  const [min, max] = finite.length ? [Math.min(...finite), Math.max(...finite)] : [0, 1];
  const scale = scaleLinear().domain(min === max ? [min - 1, max + 1] : [min, max]).nice(4);
  return { domain: scale.domain(), ticks: scale.ticks(4) };
}

export function formatAge(seconds) {
  if (seconds < 90) return "just now";
  const minutes = Math.round(seconds / 60);
  if (minutes < 90) return `${minutes} min ago`;
  const hours = Math.round(minutes / 60);
  return hours < 36 ? `${hours} h ago` : `${Math.round(hours / 24)} days ago`;
}

/** "23:29 (38 min ago)": the moment itself, plus how long ago it was. */
export const formatWhen = (iso, ageS) => `${formatClock(toMs(iso))} (${formatAge(ageS)})`;

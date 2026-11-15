import { useEffect, useRef, useState } from "react";

const REFRESH_MS = 60_000;

/** Everything the data page shows, from /api/entry. The first response is kept
 *  and rendered; refreshes replace it every minute and whenever the range
 *  changes. During a refresh the previous data stays on screen. */
export function useEntry(range) {
  const [state, setState] = useState({ data: null, error: null, loading: true });
  const request = useRef(0);

  useEffect(() => {
    const load = async () => {
      const id = ++request.current;
      setState((s) => ({ ...s, loading: true }));
      try {
        const res = await fetch(`/api/entry?range=${range}`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        if (id === request.current) setState({ data, error: null, loading: false });
      } catch (e) {
        if (id === request.current) setState((s) => ({ ...s, error: String(e.message || e), loading: false }));
      }
    };
    load();
    const timer = setInterval(load, REFRESH_MS);
    return () => clearInterval(timer);
  }, [range]);

  return state;
}

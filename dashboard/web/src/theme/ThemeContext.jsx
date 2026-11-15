import { createContext, useContext, useEffect, useState } from "react";

const QUERY = "(prefers-color-scheme: dark)";
const ThemeContext = createContext(null);

function isDark() {
  const stamp = document.documentElement.dataset.theme;
  if (stamp) return stamp === "dark";
  return window.matchMedia(QUERY).matches;
}

/** Colours for SVG chart marks. They come from the CSS tokens, so the palette
 *  is defined in one place (styles/_tokens.scss). */
function readColors() {
  const css = getComputedStyle(document.documentElement);
  const v = (name) => css.getPropertyValue(`--${name}`).trim();
  return {
    surface: v("surface"),
    grid: v("grid"),
    axis: v("axis"),
    muted: v("text-muted"),
    text: v("text-primary"),
    series: (slot) => v(`series-${slot}`) || v("text-muted"),
  };
}

export function ThemeProvider({ children }) {
  const [theme, setTheme] = useState(() => ({ dark: isDark(), colors: readColors() }));
  useEffect(() => {
    const update = () => setTheme({ dark: isDark(), colors: readColors() });
    const mq = window.matchMedia(QUERY);
    mq.addEventListener("change", update);
    const obs = new MutationObserver(update);
    obs.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
    return () => {
      mq.removeEventListener("change", update);
      obs.disconnect();
    };
  }, []);
  return <ThemeContext.Provider value={theme}>{children}</ThemeContext.Provider>;
}

export function useTheme() {
  return useContext(ThemeContext);
}

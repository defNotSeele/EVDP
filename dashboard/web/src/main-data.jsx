import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import Data from "./pages/Data/Data.jsx";
import { ThemeProvider } from "./theme/ThemeContext.jsx";
import "./styles/global.scss";

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <ThemeProvider><Data /></ThemeProvider>
  </StrictMode>,
);

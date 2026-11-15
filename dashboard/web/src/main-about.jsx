import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import About from "./pages/About/About.jsx";
import "./styles/global.scss";

createRoot(document.getElementById("root")).render(
  <StrictMode><About /></StrictMode>,
);

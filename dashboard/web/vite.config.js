import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { resolve } from "node:path";

// Two pages: about.html is the public landing page the QR codes open (served
// at "/" by Flask), index.html is the live data dashboard (served at "/data").
export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      input: {
        data: resolve(__dirname, "index.html"),
        about: resolve(__dirname, "about.html"),
      },
    },
  },
  server: {
    proxy: { "/api": "http://127.0.0.1:5000" },
  },
});

import { defineConfig } from "vite";
import { svelte } from "@sveltejs/vite-plugin-svelte";

// Set LUMI_HTTPS=1 to serve over https with a self-signed cert — needed for microphone
// access from another device on the LAN (browsers require a secure context).
const useHttps = process.env.LUMI_HTTPS === "1";

export default defineConfig(async () => ({
  plugins: [
    svelte(),
    ...(useHttps ? [(await import("@vitejs/plugin-basic-ssl")).default()] : []),
  ],
  server: {
    host: true,
    port: 5173,
    proxy: {
      "/api": "http://localhost:8000",
      "/ws": { target: "ws://localhost:8000", ws: true },
    },
  },
}));

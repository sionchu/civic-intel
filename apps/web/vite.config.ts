import { cloudflare } from "@cloudflare/vite-plugin";
import { sites } from "@openai/sites-vite-plugin";
import vinext from "vinext";
import { defineConfig } from "vite";
import nextConfig from "./next.config";

export default defineConfig(({ mode }) => ({
  // Runtime credentials belong to the host, never a local build's .env files.
  envDir: false,
  plugins: [
    vinext({ nextConfig: { ...nextConfig, output: undefined } }),
    ...(mode === "sites" ? [sites()] : []),
    cloudflare({
      viteEnvironment: { name: "rsc", childEnvironments: ["ssr"] },
      inspectorPort: false,
      config: {
        name: "civic-intel-web",
        main: "./worker.ts",
        compatibility_date: "2026-10-03",
        compatibility_flags: ["nodejs_compat"],
      },
    }),
  ],
}));

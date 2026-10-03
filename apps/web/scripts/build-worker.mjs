import { spawnSync } from "node:child_process";
import { access, readFile, rm, writeFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";

const mode = process.argv[2];
if (!["worker", "sites"].includes(mode)) throw new Error("Expected worker or sites build mode");
const root = new URL("../", import.meta.url);
if (mode === "sites") {
  await access(new URL(".openai/hosting.json", root)).catch(() => {
    throw new Error("Sites packaging requires the registered Site's hosting manifest");
  });
}

// Vinext 1.0.1 writes Next's generated types. Preserve the existing Next build inputs.
const paths = ["next-env.d.ts", ".next/types/routes.d.ts"];
const saved = await Promise.all(paths.map(async (path) => {
  const file = new URL(path, root);
  try { return { file, bytes: await readFile(file) }; }
  catch (error) { if (error.code !== "ENOENT") throw error; return { file, bytes: null }; }
}));
let status = 1;
try {
  const osKeys = new Set(["PATH", "SYSTEMROOT", "WINDIR", "COMSPEC", "PATHEXT", "TEMP", "TMP",
    "USERPROFILE", "APPDATA", "LOCALAPPDATA", "HOMEDRIVE", "HOMEPATH", "USERNAME"]);
  const environment = Object.fromEntries(Object.entries(process.env)
    .filter(([key]) => osKeys.has(key.toUpperCase())));
  Object.assign(environment, { NEXT_TELEMETRY_DISABLED: "1", WRANGLER_SEND_METRICS: "false",
    CLOUDFLARE_CF_FETCH_ENABLED: "false", WRANGLER_WRITE_LOGS: "false" });
  const result = spawnSync(process.execPath, [
    fileURLToPath(new URL("node_modules/vite/bin/vite.js", root)), "build", "--mode", mode,
  ], { cwd: fileURLToPath(root), env: environment, stdio: "inherit" });
  if (result.error) throw result.error;
  status = result.status ?? 1;
} finally {
  for (const { file, bytes } of saved) {
    if (bytes !== null) await writeFile(file, bytes);
    else await rm(file, { force: true });
  }
}
process.exitCode = status;

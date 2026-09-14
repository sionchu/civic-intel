import { existsSync, readdirSync } from "node:fs";
import { resolve } from "node:path";

const appRoot = resolve(import.meta.dirname, "..");
const standaloneRoot = resolve(appRoot, ".next", "standalone");
const staticRoot = resolve(standaloneRoot, ".next", "static");
const requiredPaths = [
  resolve(standaloneRoot, "server.js"),
  resolve(standaloneRoot, ".next", "BUILD_ID"),
  staticRoot,
];

for (const requiredPath of requiredPaths) {
  if (!existsSync(requiredPath)) {
    throw new Error(`Standalone runtime path is missing: ${requiredPath}`);
  }
}

if (readdirSync(staticRoot, { recursive: true }).length === 0) {
  throw new Error("Standalone static asset directory is empty.");
}

console.log("Standalone runtime contract verified.");

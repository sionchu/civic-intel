import { cpSync, existsSync, mkdirSync, rmSync } from "node:fs";
import { resolve } from "node:path";

const appRoot = resolve(import.meta.dirname, "..");
const standaloneRoot = resolve(appRoot, ".next", "standalone");
const staticSource = resolve(appRoot, ".next", "static");
const staticTarget = resolve(standaloneRoot, ".next", "static");
const publicSource = resolve(appRoot, "public");
const publicTarget = resolve(standaloneRoot, "public");

if (!existsSync(resolve(standaloneRoot, "server.js")) || !existsSync(staticSource)) {
  throw new Error("Next standalone output is incomplete; run next build first.");
}

rmSync(staticTarget, { recursive: true, force: true });
mkdirSync(resolve(standaloneRoot, ".next"), { recursive: true });
cpSync(staticSource, staticTarget, { recursive: true });

if (existsSync(publicSource)) {
  rmSync(publicTarget, { recursive: true, force: true });
  cpSync(publicSource, publicTarget, { recursive: true });
}

console.log("Standalone runtime assets prepared.");

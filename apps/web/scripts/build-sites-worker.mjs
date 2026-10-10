// Build the 모두의국감 Sites Worker candidate: this same Next app on the official Sites Vinext
// starter (Cloudflare Workers), reading the publication-gated public read model from D1 instead of
// prerendering every Person/Organization page into the deployment artifact. The static snapshot
// (build-sites-snapshot.mjs) stays the production path until the owner approves a cutover.
//
// Usage: node scripts/build-sites-worker.mjs [--plugin-root <installed Sites plugin dir>]
//          [--out <dir>] [--lockfile <previous successful generated lock>]
//          [--load-local <projection dir from export-public-projection.mjs>]
//
// --out receives the generated Sites project source (never edit it; rebuild). --load-local applies
// the D1 migration and a projection to the starter's local (Miniflare) D1 for preview only.
import { spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import {
  cpSync, existsSync, mkdirSync, readdirSync, readFileSync, rmSync, statSync, writeFileSync,
} from "node:fs";
import { homedir } from "node:os";
import { join, relative, resolve } from "node:path";
import { parseArgs } from "node:util";

import { sizeReport, SITES_PLATFORM_LIMIT_BYTES } from "./bundle-size-report.mjs";
import { EMAIL, forbiddenToken } from "./public-boundary.mjs";

const appRoot = resolve(import.meta.dirname, "..");
const repoRoot = resolve(appRoot, "..", "..");
const stage = resolve(appRoot, ".sites-worker-build");

function fail(message) {
  console.error(`SITES_WORKER_BUILD_FAILED: ${message}`);
  process.exit(1);
}

function run(command, args, options = {}) {
  // Honor the npm selected by the caller (e.g. npm 11.21 exec), without global tool changes.
  const npmCli = command === 'npm' && process.env.npm_execpath;
  const shell = process.platform === "win32" && command === "npm" && !npmCli;
  const result = spawnSync(npmCli ? process.execPath : command, npmCli ? [npmCli, ...args] : args,
    { cwd: stage, stdio: "inherit", shell, ...options });
  if (result.status !== 0) fail(`${command} ${args.join(" ")} exited ${result.status}`);
  return result;
}

function walk(dir) {
  return readdirSync(dir).flatMap((name) => {
    const path = join(dir, name);
    return statSync(path).isDirectory() ? walk(path) : [path];
  });
}

const { values } = parseArgs({
  options: {
    "plugin-root": { type: "string" },
    out: { type: "string", default: resolve(repoRoot, "dist", "moduigukgam-site-worker") },
    "load-local": { type: "string" },
    lockfile: { type: "string" },
  },
});

// Read before stage cleanup: the caller may retain the successful lock inside that stage.
const suppliedLock = values.lockfile ? readFileSync(resolve(values.lockfile)) : null;

// 1. The official starter from the installed Sites plugin (not vendored: Sites owns it).
const pluginCache = join(homedir(), ".codex", "plugins", "cache", "openai-curated-remote", "sites");
const pluginRoot = values["plugin-root"]
  ?? (existsSync(pluginCache) ? join(pluginCache, readdirSync(pluginCache).sort().at(-1)) : null);
const starter = pluginRoot && join(pluginRoot, "skills", "sites", "templates", "vinext-starter");
if (!starter || !existsSync(join(starter, "vite.config.ts"))) fail("Sites plugin Vinext starter not found; pass --plugin-root");
const pluginVersion = JSON.parse(readFileSync(join(pluginRoot, ".codex-plugin", "plugin.json"), "utf8")).version ?? "UNKNOWN";

// 2. Stage: starter build/runtime files + this app + the D1 transport. node_modules is reused
//    while the lockfile is unchanged.
mkdirSync(stage, { recursive: true });
for (const name of readdirSync(stage)) {
  if (!["node_modules", ".lock-sha256", ".wrangler"].includes(name)) rmSync(join(stage, name), { recursive: true, force: true });
}
const STARTER_SKIP = new Set(["app", "components", "examples", "hooks", "db", "drizzle", "node_modules", "README.md"]);
for (const name of readdirSync(starter).filter((entry) => !STARTER_SKIP.has(entry))) {
  cpSync(join(starter, name), join(stage, name), { recursive: true });
}
cpSync(join(appRoot, "app"), join(stage, "app"), { recursive: true });
cpSync(join(appRoot, "public"), join(stage, "public"), { recursive: true });
rmSync(join(stage, "app", "admin"), { recursive: true, force: true });
cpSync(join(appRoot, "sites-worker", "public-read.d1.ts"), join(stage, "app", "public-read.ts"));
cpSync(join(appRoot, "sites-worker", "db"), join(stage, "db"), { recursive: true });
cpSync(join(appRoot, "sites-worker", "drizzle"), join(stage, "drizzle"), {
  recursive: true, filter: (path) => !path.endsWith('rollback_snapshot_writer.sql'),
});
cpSync(join(appRoot, 'sites-worker', 'api'), join(stage, 'app', 'api'), { recursive: true });
mkdirSync(join(stage, 'sites-worker'), { recursive: true });
for (const name of ['snapshot-writer.mjs', 'snapshot-operations.mjs']) {
  cpSync(join(appRoot, 'sites-worker', name), join(stage, 'sites-worker', name));
}
mkdirSync(join(stage, 'scripts'), { recursive: true });
for (const name of ['public-boundary.mjs', 'snapshot-scopes.mjs']) cpSync(join(appRoot, 'scripts', name), join(stage, 'scripts', name));

const out = resolve(values.out);
const linked = existsSync(join(out, ".openai", "hosting.json"))
  ? JSON.parse(readFileSync(join(out, ".openai", "hosting.json"), "utf8")) : {};
writeFileSync(join(stage, ".openai", "hosting.json"), `${JSON.stringify({
  ...(linked.project_id ? { project_id: linked.project_id } : {}), d1: "DB", r2: null,
}, null, 2)}\n`);

// This app's runtime dependencies on top of the starter's pinned set.
const appPackage = JSON.parse(readFileSync(join(appRoot, "package.json"), "utf8"));
const stagePackage = JSON.parse(readFileSync(join(stage, "package.json"), "utf8"));
// Official Cloudflare Vinext patch release and its declared compatible RSC peer. Keep the Sites
// integration intact; beta.5's lazy Link navigation chunk is broken in the retained starter.
stagePackage.devDependencies.vinext = '1.0.1';
stagePackage.devDependencies['@vitejs/plugin-rsc'] = '0.5.36';
const added = Object.entries(appPackage.dependencies).filter(([name]) => !stagePackage.dependencies[name]);
{
  stagePackage.dependencies = Object.fromEntries(
    [...Object.entries(stagePackage.dependencies), ...added].sort(([a], [b]) => a.localeCompare(b)),
  );
  stagePackage.name = "moduigukgam-sites-worker";
  writeFileSync(join(stage, "package.json"), `${JSON.stringify(stagePackage, null, 2)}\n`);
  // npm's retained cross-platform starter lock omitted optional WASM dependencies on Windows.
  // Resolve a fresh generated-stage lock, then require npm ci to validate it (no install fallback).
  rmSync(join(stage, 'package-lock.json'), { force: true });
  // Resolve once with the caller's supported npm, then validate with the strict ci step.
  if (suppliedLock) {
    // An explicit prior lock prevents registry re-resolution during a repeat build. npm ci
    // below still validates it against the current generated package and integrity hashes.
    writeFileSync(join(stage, 'package-lock.json'), suppliedLock);
  } else {
    run("npm", ["install", '--package-lock-only',
      "--ignore-scripts", "--workspaces=false", "--include=dev", "--include=optional", "--no-audit", "--no-fund"]);
  }
}
const lockSha = createHash("sha256").update(readFileSync(join(stage, "package-lock.json"))).digest("hex");
const lockMarker = join(stage, ".lock-sha256");
if (values.lockfile || !existsSync(join(stage, "node_modules")) || !existsSync(lockMarker) || readFileSync(lockMarker, "utf8") !== lockSha) {
  // A failed ci can leave a partial node_modules tree. Never reuse the previous success marker.
  rmSync(lockMarker, { force: true });
  run("npm", ["run", "install:ci"]);
  writeFileSync(lockMarker, lockSha);
}

// 3. Build with the starter's portable entry point. No private API origin exists in this build.
const env = { ...process.env, NODE_ENV: "production", NEXT_TELEMETRY_DISABLED: "1" };
for (const name of ["CIVIC_API_URL", "NEXT_PUBLIC_API_URL", "CIVIC_PUBLIC_BASE_URL", "CIVIC_INDEXING_ENABLED", "CIVIC_SNAPSHOT_AT"]) {
  delete env[name];
}
rmSync(join(stage, "dist"), { recursive: true, force: true });
// Typecheck the app against the Worker types (D1 binding, cloudflare:workers) before building.
run(process.execPath, ["node_modules/typescript/bin/tsc", "--noEmit", "-p", "."]);
run("npm", ["run", "build"], { env });

// 4. Fail closed on the public boundary and on anything that is not this code-only artifact.
const dist = join(stage, "dist");
const distFiles = walk(dist);
const artifactSize = sizeReport(dist, {});
if (artifactSize.bundle.total_bytes > SITES_PLATFORM_LIMIT_BYTES) {
  fail(`Worker artifact exceeds ${SITES_PLATFORM_LIMIT_BYTES} uncompressed bytes`);
}
const rel = (path) => relative(dist, path).split("\\").join("/");
for (const path of distFiles.filter((file) => /\.(html|txt|m?js|json|map)$/.test(file))) {
  const text = readFileSync(path, "utf8");
  const token = forbiddenToken(text, "http://localhost:8000");
  if (token) fail(`forbidden token ${JSON.stringify(token)} in dist/${rel(path)}`);
  if (/\.html$/.test(path) && EMAIL.test(text)) fail(`email-like text in dist/${rel(path)}`);
}
const serverCode = distFiles.filter((file) => file.endsWith(".js")).map((file) => readFileSync(file, "utf8")).join("\n");
if (serverCode.includes("operator-data") || serverCode.includes("/admin/review")) fail("operator surface present in Worker build");
if (!serverCode.includes("snapshot_meta")) fail("D1 public-read transport missing from the Worker build");
const wrangler = JSON.parse(readFileSync(join(dist, "server", "wrangler.json"), "utf8"));
if (!wrangler.d1_databases?.some((binding) => binding.binding === "DB")) fail("D1 binding DB missing from the Worker config");

// 5. Optional local preview data: migration, projection, activation in the starter's local D1.
if (values["load-local"]) {
  const projection = resolve(values["load-local"]);
  const wranglerCli = ["--import", "./scripts/sites-env.mjs", "./node_modules/wrangler/bin/wrangler.js"];
  // Only this disposable local D1 is writable. Rebuilds retain its ACTIVE/PREVIOUS snapshots.
  const localSchema = join(stage, '.wrangler', 'local-schema.sql');
  mkdirSync(join(stage, '.wrangler'), { recursive: true });
  writeFileSync(localSchema, readFileSync(join(stage, 'drizzle', '0000_public_projection.sql'), 'utf8').replaceAll('CREATE TABLE ', 'CREATE TABLE IF NOT EXISTS '));
  run(process.execPath, [...wranglerCli, 'd1', 'execute', 'DB', '--local', '--config', 'dist/server/wrangler.json', '--persist-to', '.wrangler/state', '--file', localSchema]);
  const probe = run(process.execPath, [...wranglerCli, 'd1', 'execute', 'DB', '--local', '--config', 'dist/server/wrangler.json', '--persist-to', '.wrangler/state', '--json', '--command', 'PRAGMA table_info(snapshot_meta)'], { stdio: ['ignore', 'pipe', 'inherit'], encoding: 'utf8' });
  const columns = JSON.parse(probe.stdout).flatMap((result) => result.results ?? []).map((column) => column.name);
  const writerColumns = ['writer_manifest_sha256', 'writer_phase', 'writer_cursor', 'validation_cursor', 'pointer_epoch', 'writer_transition_sha256'];
  const present = writerColumns.filter((name) => columns.includes(name)).length;
  if (present !== 0 && present !== writerColumns.length) fail('partial local D1 writer migration; resolve state before proceeding');
  if (present === 0) run(process.execPath, [...wranglerCli, 'd1', 'execute', 'DB', '--local', '--config', 'dist/server/wrangler.json', '--persist-to', '.wrangler/state', '--file', join(stage, 'drizzle', '0001_snapshot_writer.sql')]);
  for (const file of [join(projection, "load.sql"), join(projection, "activate.sql")]) {
    run(process.execPath, [...wranglerCli, "d1", "execute", "DB", "--local", "--config", "dist/server/wrangler.json",
      "--persist-to", ".wrangler/state", "--file", file]);
  }
}

// 6. The generated Sites project source (what a Sites save packages), plus its manifest.
mkdirSync(out, { recursive: true });
for (const name of readdirSync(out)) {
  if (name !== ".openai") rmSync(join(out, name), { recursive: true, force: true });
}
const SOURCE_SKIP = new Set([
  "node_modules", "dist", ".next", ".wrangler", ".vinext", ".sites-runtime", ".lock-sha256", "tsconfig.tsbuildinfo",
  "next-env.d.ts",
]);
for (const name of readdirSync(stage).filter((entry) => !SOURCE_SKIP.has(entry))) {
  cpSync(join(stage, name), join(out, name), { recursive: true });
}
const commit = spawnSync("git", ["rev-parse", "HEAD"], { cwd: repoRoot, encoding: "utf8" }).stdout.trim() || "UNKNOWN";
const dirty = spawnSync("git", ["status", "--porcelain"], { cwd: repoRoot, encoding: "utf8" }).stdout.trim() !== "";
const manifest = {
  site_name: "모두의국감",
  shape: "SITES_WORKER_D1_PUBLIC_READ",
  semantics: "Code/runtime only; public records are read from the ACTIVE D1 snapshot (REPLACEABLE_PUBLIC_READ_SNAPSHOT_NOT_SSOT)",
  canonical_store: "Civic Intel PostgreSQL (private); D1 rows come only from export-public-projection.mjs",
  git_commit: commit,
  git_worktree_dirty: dirty,
  sites_plugin_version: pluginVersion,
  vinext_version: stagePackage.devDependencies.vinext,
  rsc_plugin_version: stagePackage.devDependencies['@vitejs/plugin-rsc'],
  generated_lock_sha256: lockSha,
  worker_artifact: artifactSize,
};
writeFileSync(join(out, "worker-manifest.json"), `${JSON.stringify(manifest, null, 2)}\n`);
console.log(JSON.stringify({ status: "PASS", out, stage, ...manifest }, null, 2));

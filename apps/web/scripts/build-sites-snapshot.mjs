// Build the 모두의국감 ChatGPT Sites bundle: a static, replaceable snapshot of the public read
// projection, rendered by this same Next app from a private Civic Intel API that reads the
// canonical (Mac) PostgreSQL. The API/DB are only contacted at build time on the build host;
// the bundle carries no API origin, credentials, operator surface or write path.
//
// Usage: node scripts/build-sites-snapshot.mjs --api http://127.0.0.1:8000
//          [--out <dir>] [--base-url https://<site-host>] [--index]
import { spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import {
  cpSync, existsSync, mkdirSync, readdirSync, readFileSync, rmSync, statSync, symlinkSync, writeFileSync,
} from "node:fs";
import { join, relative, resolve } from "node:path";
import { parseArgs } from "node:util";

const appRoot = resolve(import.meta.dirname, "..");
const repoRoot = resolve(appRoot, "..", "..");
const stage = resolve(appRoot, ".sites-build");

const { values } = parseArgs({
  options: {
    api: { type: "string" },
    out: { type: "string", default: resolve(repoRoot, "dist", "moduigukgam-site") },
    "base-url": { type: "string" },
    index: { type: "boolean", default: false },
  },
});

function fail(message) {
  console.error(`SNAPSHOT_BUILD_FAILED: ${message}`);
  process.exit(1);
}

const api = values.api?.replace(/\/+$/, "");
if (!api) fail("--api <private Civic Intel API origin on this host> is required");
const apiOrigin = new URL(api).origin;
if (values.index && !values["base-url"]) fail("--index requires --base-url of the public Site");

async function getJson(path) {
  const response = await fetch(`${api}${path}`, { cache: "no-store" });
  if (!response.ok) fail(`${path} returned HTTP ${response.status}`);
  return response.json();
}

// 1. The source API must be ready (schema + DB) before anything is rendered.
const ready = await getJson("/ready");
if (ready.status !== "ready") fail("/ready did not report ready");
const [people, organizations, targets, committees] = await Promise.all([
  getJson("/people"),
  getJson("/organizations"),
  getJson("/gukgam/2026/targets"),
  getJson("/gukgam/2026/committees"),
]);
if (!Array.isArray(people) || people.length === 0) fail("/people returned no public Person");

// 2. Stage a copy of the app without the operator surface, rendered statically.
rmSync(stage, { recursive: true, force: true });
mkdirSync(stage, { recursive: true });
for (const name of ["app", "public", "package.json", "tsconfig.json", "next-env.d.ts"]) {
  if (existsSync(join(appRoot, name))) cpSync(join(appRoot, name), join(stage, name), { recursive: true });
}
symlinkSync(join(appRoot, "node_modules"), join(stage, "node_modules"), "junction");
rmSync(join(stage, "app", "admin"), { recursive: true, force: true });
// Static export cannot emit a dynamic route with zero entries; an empty public Organization list
// simply has no detail pages (the directory page still renders its empty state).
if (!Array.isArray(organizations) || organizations.length === 0) {
  rmSync(join(stage, "app", "organizations", "[id]"), { recursive: true, force: true });
}

function walk(dir) {
  return readdirSync(dir).flatMap((name) => {
    const path = join(dir, name);
    return statSync(path).isDirectory() ? walk(path) : [path];
  });
}

let rewritten = 0;
for (const file of walk(join(stage, "app")).filter((path) => /\.(ts|tsx)$/.test(path))) {
  const source = readFileSync(file, "utf8");
  const next = source.replace('export const dynamic = "force-dynamic";', 'export const dynamic = "force-static";');
  if (next !== source) {
    writeFileSync(file, next);
    rewritten += 1;
  }
}
// Prerender every public Person/Organization detail page in the staged copy only; the server build
// keeps rendering these routes per request.
const STATIC_PARAMS = {
  "people": "getPeople",
  "organizations": "getOrganizations",
};
for (const [route, loader] of Object.entries(STATIC_PARAMS)) {
  const page = join(stage, "app", route, "[id]", "page.tsx");
  if (!existsSync(page)) continue;
  writeFileSync(page, `${readFileSync(page, "utf8")}
import { ${loader} as listForSnapshot } from "../../data";

export async function generateStaticParams(): Promise<{ id: string }[]> {
  const result = await listForSnapshot();
  if (result.state === "error") throw new Error(\`Snapshot export cannot list ${route}: \${result.error.code}\`);
  return result.data.map((item) => ({ id: item.id }));
}
`);
}

const stillDynamic = walk(join(stage, "app")).filter((path) => readFileSync(path, "utf8").includes("force-dynamic"));
if (rewritten < 7 || stillDynamic.length > 0) {
  fail(`request-time routes not fully switched to static (rewritten ${rewritten}, remaining ${stillDynamic.length})`);
}

writeFileSync(join(stage, "next.config.ts"), `import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "export",
  trailingSlash: true,
  images: { unoptimized: true },
};

export default nextConfig;
`);

// 3. Build. Indexing stays off unless explicitly requested for the final public Site URL.
const generatedAt = new Date();
const snapshotAt = `${new Intl.DateTimeFormat("sv-SE", {
  timeZone: "Asia/Seoul", year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit",
}).format(generatedAt)} KST`;
const env = { ...process.env, NODE_ENV: "production", NEXT_TELEMETRY_DISABLED: "1" };
for (const name of ["NEXT_PUBLIC_API_URL", "CIVIC_PUBLIC_BASE_URL", "CIVIC_INDEXING_ENABLED"]) delete env[name];
Object.assign(env, { CIVIC_API_URL: api, CIVIC_SITES_EXPORT: "1", CIVIC_SNAPSHOT_AT: snapshotAt });
if (values["base-url"]) env.CIVIC_PUBLIC_BASE_URL = values["base-url"];
if (values.index) env.CIVIC_INDEXING_ENABLED = "true";

const build = spawnSync(process.execPath, [join(appRoot, "node_modules", "next", "dist", "bin", "next"), "build"], {
  cwd: stage, env, stdio: "inherit",
});
if (build.status !== 0) fail(`next build exited ${build.status}`);

// 4. Replace the bundle, keeping the Sites project link (.openai/) if the folder is already linked.
const out = resolve(values.out);
mkdirSync(out, { recursive: true });
for (const name of readdirSync(out)) {
  if (name !== ".openai") rmSync(join(out, name), { recursive: true, force: true });
}
cpSync(join(stage, "out"), out, { recursive: true });

// Next 16 export writes segment-prefetch payloads as nested folders (`__next.people/$d$id/__PAGE__.txt`)
// while its client requests the flattened name (`__next.people.$d$id.__PAGE__.txt`). Add the
// flattened copy so client navigation does not 404 on a plain static host.
for (const path of walk(out)) {
  const parts = relative(out, path).split(/[\\/]/);
  const start = parts.findIndex((part) => part.startsWith("__next.") && part !== parts.at(-1));
  if (start < 0 || parts[0] === "_next") continue;
  const flattened = join(out, ...parts.slice(0, start), parts.slice(start).join("."));
  if (!existsSync(flattened)) cpSync(path, flattened);
}

// Sites caps an uncompressed deployment at 256 MiB. The exported client navigates with
// `<route>/index.txt` and prefetches the flattened segment files only, so the nested segment folders
// and `__next._full.txt` (byte-identical to the sibling index.txt) are never requested. Drop them,
// and the detail-route page segments below; no page content or data is removed.
const SITES_MAX_BYTES = 256 * 1024 * 1024;
for (const path of walk(out)) {
  const parts = relative(out, path).split(/[\\/]/);
  if (parts[0] === "_next" || parts[0] === ".openai") continue;
  const nested = parts.findIndex((part) => part.startsWith("__next.") && part !== parts.at(-1));
  if (nested >= 0) {
    rmSync(join(out, ...parts.slice(0, nested + 1)), { recursive: true, force: true });
  } else if (parts.at(-1) === "__next._full.txt") {
    const sibling = join(out, ...parts.slice(0, -1), "index.txt");
    if (!existsSync(sibling) || !readFileSync(sibling).equals(readFileSync(path))) {
      fail(`${parts.join("/")} differs from its index.txt; refusing to drop it`);
    }
    rmSync(path);
  } else if (/^__next\..+\.\$d\$id\.__PAGE__\.txt$/.test(parts.at(-1))) {
    // Detail-page segment prefetch payloads (`/people/[id]`, `/organizations/[id]`) repeat their
    // sibling index.txt. The client treats a missing prefetch segment as a cache miss and navigates
    // with `<route>/index.txt` (verified in the exported client), so dropping these keeps every page
    // and record while staying under the Sites limit.
    if (!existsSync(join(out, ...parts.slice(0, -1), "index.txt"))) {
      fail(`${parts.join("/")} has no sibling index.txt; refusing to drop it`);
    }
    rmSync(path);
  }
}

// 5. Fail closed on missing routes, operator surface or anything that is not public projection.
const files = walk(out).filter((path) => !relative(out, path).startsWith(".openai"));
const rel = (path) => relative(out, path).split("\\").join("/");
const bundleBytes = files.reduce((total, path) => total + statSync(path).size, 0);
if (bundleBytes > SITES_MAX_BYTES) {
  fail(`bundle is ${(bundleBytes / 2 ** 20).toFixed(2)} MiB; Sites allows ${SITES_MAX_BYTES / 2 ** 20} MiB uncompressed`);
}
for (const required of [
  "index.html", "people/index.html", "organizations/index.html", "gukgam/2026/index.html",
  "404.html", "robots.txt", "sitemap.xml",
]) {
  if (!existsSync(join(out, required))) fail(`missing ${required}`);
}
if (files.some((path) => rel(path).startsWith("admin/"))) fail("operator surface present in bundle");
const missingPeople = people.filter((person) => !existsSync(join(out, "people", person.id, "index.html")));
if (missingPeople.length > 0) fail(`${missingPeople.length} public Person pages missing`);

const FORBIDDEN_TOKENS = [
  apiOrigin, "TEL_NO", "E_MAIL", "normalized_payload", "raw_payload", "railway.internal",
  "X-Civic-Operator-Token", "CIVIC_OPERATOR", "DATABASE_URL", "postgresql://", "postgresql+psycopg",
];
const EMAIL = /[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}/;
for (const path of files.filter((file) => /\.(html|txt|js|json|xml)$/.test(file))) {
  const text = readFileSync(path, "utf8");
  const token = FORBIDDEN_TOKENS.find((item) => text.includes(item));
  if (token) fail(`forbidden token ${JSON.stringify(token)} in ${rel(path)}`);
  if (/\.(html|txt)$/.test(path) && EMAIL.test(text)) fail(`email-like text in ${rel(path)}`);
}

// 6. Manifest: what this replaceable snapshot is, where it came from and how to verify it.
const digests = files.map((path) => `${rel(path)}\t${createHash("sha256").update(readFileSync(path)).digest("hex")}`).sort();
const commit = spawnSync("git", ["rev-parse", "HEAD"], { cwd: repoRoot, encoding: "utf8" }).stdout.trim() || "UNKNOWN";
const dirty = spawnSync("git", ["status", "--porcelain"], { cwd: repoRoot, encoding: "utf8" }).stdout.trim() !== "";
const manifest = {
  site_name: "모두의국감",
  semantics: "REPLACEABLE_PUBLIC_READ_SNAPSHOT_NOT_SSOT",
  canonical_store: "Civic Intel PostgreSQL (private); this bundle is regenerated, never edited",
  git_commit: commit,
  git_worktree_dirty: dirty,
  generated_at: generatedAt.toISOString(),
  generated_at_kst: snapshotAt,
  indexing: values.index ? "ENABLED" : "DISABLED",
  public_base_url: values["base-url"] ?? null,
  counts: {
    public_people: people.length,
    public_organizations: Array.isArray(organizations) ? organizations.length : null,
    gukgam_targets: targets.target_count ?? null,
    gukgam_committees: committees.committee_count ?? null,
    files: files.length,
    bytes: bundleBytes,
  },
  bundle_sha256: createHash("sha256").update(digests.join("\n")).digest("hex"),
};
writeFileSync(join(out, "snapshot-manifest.json"), `${JSON.stringify(manifest, null, 2)}\n`);
console.log(JSON.stringify({ status: "PASS", out, ...manifest }, null, 2));

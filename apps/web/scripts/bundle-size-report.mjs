// Size attribution for a built 모두의국감 Sites bundle. The snapshot build embeds the compact
// `sizeReport()` in snapshot-manifest.json; run this file directly for the full audit
// (largest files, per-Person detail bytes, identical-content groups):
//
//   node scripts/bundle-size-report.mjs <bundle-dir> [--top 30]
import { createHash } from "node:crypto";
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join, relative, resolve } from "node:path";
import { parseArgs } from "node:util";

export const SITES_PLATFORM_LIMIT_BYTES = 256 * 1024 * 1024;
// Project budget for the static fallback; this is our policy, not a Sites limit.
export const PROJECT_BUDGET_BYTES = {
  green: 192 * 1024 * 1024,
  warning: 220 * 1024 * 1024,
  critical: 240 * 1024 * 1024,
};

function walk(dir) {
  return readdirSync(dir).flatMap((name) => {
    const path = join(dir, name);
    return statSync(path).isDirectory() ? walk(path) : [path];
  });
}

function category(path) {
  if (/\.html$/.test(path)) return "html";
  if (/\.txt$/.test(path)) return "rsc_txt";
  if (/\.m?js$/.test(path)) return "javascript";
  if (/\.css$/.test(path)) return "css";
  if (/\.(png|jpe?g|webp|gif|svg|ico|avif)$/.test(path)) return "images";
  if (/\.(json|xml)$/.test(path)) return "json_xml";
  return "other";
}

function budgetState(bytes) {
  if (bytes > SITES_PLATFORM_LIMIT_BYTES) return "OVER_PLATFORM_LIMIT";
  if (bytes > PROJECT_BUDGET_BYTES.critical) return "INTERNAL_FAIL";
  if (bytes > PROJECT_BUDGET_BYTES.warning) return "CRITICAL";
  if (bytes > PROJECT_BUDGET_BYTES.green) return "WARNING";
  return "GREEN";
}

function readBundle(outDir) {
  return walk(outDir)
    .map((path) => ({ path: relative(outDir, path).split("\\").join("/"), bytes: statSync(path).size, abs: path }))
    .filter((file) => !file.path.startsWith(".openai/") && file.path !== "snapshot-manifest.json");
}

// Bytes of one detail route (`people/<id>/…`), excluding the directory page itself.
function detailRouteBytes(files, route) {
  const byId = new Map();
  for (const file of files) {
    const parts = file.path.split("/");
    if (parts[0] !== route || parts.length < 3) continue;
    byId.set(parts[1], (byId.get(parts[1]) ?? 0) + file.bytes);
  }
  return [...byId.values()].sort((a, b) => a - b);
}

function quantile(sorted, q) {
  return sorted.length ? sorted[Math.min(sorted.length - 1, Math.floor(q * sorted.length))] : 0;
}

function routeStats(sorted) {
  const total = sorted.reduce((sum, value) => sum + value, 0);
  return {
    count: sorted.length,
    total_bytes: total,
    mean_bytes: sorted.length ? Math.round(total / sorted.length) : 0,
    median_bytes: quantile(sorted, 0.5),
    p95_bytes: quantile(sorted, 0.95),
    max_bytes: sorted.at(-1) ?? 0,
  };
}

// Compact, backward-compatible block for snapshot-manifest.json.
export function sizeReport(outDir, { publicPeople, publicOrganizations, top = 10 } = {}) {
  const files = readBundle(outDir);
  const total = files.reduce((sum, file) => sum + file.bytes, 0);
  const sizeByCategory = { html: 0, rsc_txt: 0, javascript: 0, css: 0, images: 0, json_xml: 0, other: 0 };
  for (const file of files) sizeByCategory[category(file.path)] += file.bytes;
  const people = routeStats(detailRouteBytes(files, "people"));
  return {
    bundle: {
      total_bytes: total,
      files: files.length,
      platform_limit_bytes: SITES_PLATFORM_LIMIT_BYTES,
      project_fail_budget_bytes: PROJECT_BUDGET_BYTES.critical,
      headroom_bytes: SITES_PLATFORM_LIMIT_BYTES - total,
      usage_ratio: Number((total / SITES_PLATFORM_LIMIT_BYTES).toFixed(4)),
      budget_state: budgetState(total),
    },
    size_by_category: sizeByCategory,
    entities: { public_people: publicPeople ?? null, public_organizations: publicOrganizations ?? null },
    density: {
      person_detail_bytes: people.total_bytes,
      bytes_per_public_person: people.count ? Math.round(people.total_bytes / people.count) : 0,
    },
    largest_files: [...files].sort((a, b) => b.bytes - a.bytes).slice(0, top)
      .map(({ path, bytes }) => ({ path, bytes })),
  };
}

// Full audit, including identical-content groups (bytes that a static host stores more than once).
export function fullAudit(outDir, top = 30) {
  const files = readBundle(outDir);
  const groups = new Map();
  for (const file of files) {
    const digest = createHash("sha256").update(readFileSync(file.abs)).digest("hex");
    const group = groups.get(digest) ?? { bytes: file.bytes, paths: [] };
    group.paths.push(file.path);
    groups.set(digest, group);
  }
  const duplicates = [...groups.values()].filter((group) => group.paths.length > 1);
  const topLevel = {};
  for (const file of files) {
    const key = file.path.split("/")[0].includes(".") ? "(root files)" : file.path.split("/")[0];
    topLevel[key] = (topLevel[key] ?? 0) + file.bytes;
  }
  const report = sizeReport(outDir, { top });
  return {
    ...report,
    bytes_by_top_level: Object.fromEntries(Object.entries(topLevel).sort((a, b) => b[1] - a[1])),
    people_detail: routeStats(detailRouteBytes(files, "people")),
    organization_detail: routeStats(detailRouteBytes(files, "organizations")),
    gukgam_bytes: files.filter((file) => file.path.startsWith("gukgam/")).reduce((sum, file) => sum + file.bytes, 0),
    identical_content: {
      groups: duplicates.length,
      wasted_bytes: duplicates.reduce((sum, group) => sum + group.bytes * (group.paths.length - 1), 0),
      largest: duplicates.sort((a, b) => b.bytes * b.paths.length - a.bytes * a.paths.length).slice(0, 5)
        .map((group) => ({ bytes: group.bytes, copies: group.paths.length, example: group.paths.slice(0, 3) })),
    },
  };
}

if (process.argv[1] && resolve(process.argv[1]) === resolve(import.meta.filename)) {
  const { values, positionals } = parseArgs({ allowPositionals: true, options: { top: { type: "string", default: "30" } } });
  if (!positionals[0]) {
    console.error("usage: node scripts/bundle-size-report.mjs <bundle-dir> [--top 30]");
    process.exit(2);
  }
  console.log(JSON.stringify(fullAudit(resolve(positionals[0]), Number(values.top)), null, 2));
}

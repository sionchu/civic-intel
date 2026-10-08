// Export the 모두의국감 public read projection for the D1-backed Sites Worker.
//
// It reads the same private, publication-gated API that the static snapshot build renders from and
// stores each response verbatim (gzip) under the exact API path the pages request. D1 never
// re-decides identity, publication, SourcePolicy or FACT/UNKNOWN; it replays these responses.
// PostgreSQL stays the canonical store and this export is REPLACEABLE_PUBLIC_READ_SNAPSHOT_NOT_SSOT.
//
// Usage: node scripts/export-public-projection.mjs --api http://127.0.0.1:8000 [--out <dir>]
//
// Output (deterministic for the same API state, except the transport fields named below):
//   projection-manifest.json  semantic hash, counts, per-path hashes and bytes
//   load.sql                  STAGED snapshot rows (idempotent: re-running inserts nothing new)
//   activate.sql              STAGED → ACTIVE, ACTIVE → PREVIOUS, older PREVIOUS removed
import { spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import { mkdirSync, writeFileSync } from "node:fs";
import { join, resolve } from "node:path";
import { parseArgs } from "node:util";
import { gzipSync } from "node:zlib";

import { EMAIL, forbiddenToken } from "./public-boundary.mjs";
import { PERSON_RELATIONSHIP_QUERY, personRelationshipPath } from "../app/relationship-path.mjs";

export const PROJECTION_SCHEMA_VERSION = 2;
// RECENT_PLENARY_VOTE_LIMIT in packages/rendering/profile_projection.py: a Person response carries only
// the rendered recent votes; the vote universe stays in PostgreSQL and is never exported.
const MAX_RENDERED_PLENARY_VOTES = 10;
// gzip bytes per public_read row: hex-encoded in one INSERT this stays under D1's 100 KB statement limit.
const PART_BYTES = 40_000;
const MONEY_QUERY = "earlier_fiscal_year=2024&later_fiscal_year=2025"; // data.ts getOrganizationMoney defaults
const UUID = "[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}";
// A path inside one of these scopes that has no row is a public "not found", not a service failure.
export const SCOPES = [
  `^/people/${UUID}$`,
  `^/ontology/people/${UUID}$`,
  `^/relationships/people/${UUID}\\?${PERSON_RELATIONSHIP_QUERY.replace(/[?&]/g, "\\$&")}$`,
  `^/organizations/${UUID}$`,
  `^/ontology/organizations/${UUID}$`,
  `^/organizations/${UUID}/money\\?${MONEY_QUERY.replace(/[?&]/g, "\\$&")}$`,
  `^/sources/${UUID}$`,
];

const appRoot = resolve(import.meta.dirname, "..");
const repoRoot = resolve(appRoot, "..", "..");

function fail(message) {
  console.error(`PROJECTION_EXPORT_FAILED: ${message}`);
  process.exit(1);
}

const sha256 = (bytes) => createHash("sha256").update(bytes).digest("hex");
const sqlText = (value) => `'${String(value).replaceAll("'", "''")}'`;

async function main() {
  const { values } = parseArgs({
    options: {
      api: { type: "string" },
      out: { type: "string", default: resolve(repoRoot, "dist", "moduigukgam-projection") },
      concurrency: { type: "string", default: "4" },
    },
  });
  const api = values.api?.replace(/\/+$/, "");
  if (!api) fail("--api <private Civic Intel API origin on this host> is required");
  const apiUrl = new URL(api);
  if (!['127.0.0.1', 'localhost', '[::1]'].includes(apiUrl.hostname) || apiUrl.username || apiUrl.password) {
    fail("--api must be a credential-free loopback API origin");
  }
  const apiOrigin = apiUrl.origin;
  const concurrency = Number(values.concurrency);
  if (!Number.isInteger(concurrency) || concurrency < 1 || concurrency > 8) fail("concurrency must be an integer from 1 to 8");

  // Detail reads keep a public 4xx answer (e.g. 404, or 422 for a money comparison the record does
  // not support) exactly as the pages would have received it; a 5xx always fails the export.
  async function read(path, { allowedStatuses = [] } = {}) {
    const response = await fetch(`${api}${path}`, { cache: "no-store", redirect: "error", signal: AbortSignal.timeout(120_000) });
    if (response.ok) return { status: response.status, body: await response.json() };
    if (allowedStatuses.includes(response.status)) {
      const body = await response.json().catch(() => null);
      // A request id identifies one private API call, not the public answer; it is not replayed.
      if (body?.error) delete body.error.request_id;
      return { status: response.status, body };
    }
    fail(`${path} returned HTTP ${response.status}`);
  }

  if ((await read("/ready")).body?.status !== "ready") fail("/ready did not report ready");

  const entries = new Map();
  const add = (path, response) => entries.set(path, response);
  const directories = ["/people", "/organizations", "/gukgam/2026/targets", "/gukgam/2026/committees", "/gukgam/2026/witnesses"];
  for (const path of directories) add(path, await read(path));

  const people = entries.get("/people").body;
  const organizations = entries.get("/organizations").body;
  if (!Array.isArray(people) || people.length === 0) fail("/people returned no public Person");
  if (!Array.isArray(organizations)) fail("/organizations did not return a list");
  // The API applies the publication gate; the export only refuses anything that is not RESOLVED.
  const unresolved = people.filter((person) => person.identity_status !== "RESOLVED");
  if (unresolved.length > 0) fail(`${unresolved.length} listed Persons are not RESOLVED`);
  for (const [label, list] of [["people", people], ["organizations", organizations]]) {
    if (new Set(list.map((item) => item.id)).size !== list.length) fail(`duplicate ${label} ids`);
    if (list.some((item) => !new RegExp(`^${UUID}$`).test(item.id))) fail(`non-UUID ${label} id`);
  }

  const detailPaths = [
    ...people.flatMap(({ id }) => [`/people/${id}`, `/ontology/people/${id}`, personRelationshipPath(id)]),
    ...organizations.flatMap(({ id }) => [
      `/organizations/${id}`, `/ontology/organizations/${id}`, `/organizations/${id}/money?${MONEY_QUERY}`,
    ]),
  ];
  async function readAll(paths) {
    const queue = [...paths];
    await Promise.all(Array.from({ length: concurrency }, async () => {
      while (queue.length > 0) {
        const path = queue.shift();
        // Listed records and cited sources must exist. Only the optional money comparison has
        // contract-valid 404/422 answers; auth/rate-limit/provider failures never become snapshots.
        add(path, await read(path, { allowedStatuses: path.includes('/money?') ? [404, 422] : [] }));
      }
    }));
  }
  await readAll(detailPaths);
  // Detail pages render a source card for every source their Claims, Evidence, ontology edges and
  // money comparisons cite; export those Source records too (a superset of what each page reads).
  const sourceIds = new Set();
  const collectSources = (value) => {
    if (Array.isArray(value)) value.forEach(collectSources);
    else if (value && typeof value === "object") {
      for (const [key, item] of Object.entries(value)) {
        if (key === "source_ids" && Array.isArray(item)) item.forEach((id) => sourceIds.add(id));
        else if (key === "source_id" && typeof item === "string") sourceIds.add(item);
        else collectSources(item);
      }
    }
  };
  for (const response of entries.values()) collectSources(response.body);
  if ([...sourceIds].some((id) => !new RegExp(`^${UUID}$`).test(id))) fail("non-UUID source id");
  await readAll([...sourceIds].sort().map((id) => `/sources/${id}`));

  // Bounded Person payloads: the rendered recent votes only, never the vote universe.
  for (const { id } of people) {
    const person = entries.get(`/people/${id}`).body;
    if (person?.id !== id) fail(`/people/${id} returned a different Person`);
    if (person.identity_status !== "RESOLVED") fail(`/people/${id} is not RESOLVED`);
    const votes = (person.profile?.sections ?? []).flatMap((section) => section.entries ?? [])
      .filter((entry) => entry.details?.action === "PLENARY_ROLL_CALL_VOTE").length;
    if (votes > MAX_RENDERED_PLENARY_VOTES) fail(`/people/${id} carries ${votes} plenary votes (max ${MAX_RENDERED_PLENARY_VOTES})`);
  }

  // Serialize, scan the public boundary, hash and compress every row.
  const rows = [...entries.entries()].sort(([a], [b]) => (a < b ? -1 : a > b ? 1 : 0)).map(([path, response]) => {
    const json = JSON.stringify(response.body);
    const token = forbiddenToken(json, apiOrigin);
    if (token) fail(`forbidden token ${JSON.stringify(token)} in ${path}`);
    if (EMAIL.test(json)) fail(`email-like text in ${path}`);
    const bytes = Buffer.from(json, "utf8");
    return { path, status: response.status, sha256: sha256(bytes), bytes: bytes.length, gzip: gzipSync(bytes, { level: 9 }) };
  });

  const semantic = {
    semantics: "REPLACEABLE_PUBLIC_READ_SNAPSHOT_NOT_SSOT",
    projection_schema_version: PROJECTION_SCHEMA_VERSION,
    scopes: SCOPES,
    rows: rows.map(({ path, status, sha256: digest }) => [path, status, digest]),
  };
  const semanticSha256 = sha256(JSON.stringify(semantic));
  const snapshotId = `ps-${semanticSha256.slice(0, 16)}`;
  // Transport fields: they describe this export run and are excluded from the semantic hash.
  const generatedAt = new Date();
  const generatedAtKst = `${new Intl.DateTimeFormat("sv-SE", {
    timeZone: "Asia/Seoul", year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit",
  }).format(generatedAt)} KST`;
  const gitCommit = spawnSync("git", ["rev-parse", "HEAD"], { cwd: repoRoot, encoding: "utf8" }).stdout.trim() || "UNKNOWN";

  const out = resolve(values.out);
  mkdirSync(out, { recursive: true });
  const parts = rows.flatMap((row) => Array.from({ length: Math.ceil(row.gzip.length / PART_BYTES) }, (_, index) => ({
    ...row, part: index, chunk: row.gzip.subarray(index * PART_BYTES, (index + 1) * PART_BYTES),
  })));
  const partCount = parts.length;
  const scopeJson = JSON.stringify({
    patterns: SCOPES,
    paths: Object.fromEntries(rows.map((row) => [row.path, [row.status, row.sha256]])),
  });
  const meta = [
    snapshotId, "STAGED", PROJECTION_SCHEMA_VERSION, generatedAt.toISOString(), generatedAtKst, gitCommit,
    '', rows.length, partCount, people.length, organizations.length,
  ];
  const load = [
    "-- 모두의국감 public read projection (REPLACEABLE_PUBLIC_READ_SNAPSHOT_NOT_SSOT). Generated; never edit.",
    `INSERT INTO snapshot_meta (snapshot_id, status, projection_schema_version, generated_at, generated_at_kst, git_commit, scope_json, path_count, part_count, public_people, public_organizations) VALUES (${meta.map((value) => (typeof value === "number" ? value : sqlText(value))).join(", ")}) ON CONFLICT DO NOTHING;`,
    ...parts.map((row) => `INSERT INTO public_read (snapshot_id, path, part, status, content_sha256, body_gzip) VALUES (${sqlText(snapshotId)}, ${sqlText(row.path)}, ${row.part}, ${row.status}, ${sqlText(row.sha256)}, X'${row.chunk.toString("hex")}') ON CONFLICT DO NOTHING;`),
  ];
  // Keep metadata INSERTs bounded too; manifest chunks resume by committed length and never
  // append again to an already complete STAGED/ACTIVE snapshot.
  for (let offset = 0; offset < scopeJson.length; offset += 20_000) {
    const chunk = scopeJson.slice(offset, offset + 20_000);
    load.push(`UPDATE snapshot_meta SET scope_json = scope_json || ${sqlText(chunk)} WHERE snapshot_id = ${sqlText(snapshotId)} AND status = 'STAGED' AND length(scope_json) = ${offset};`);
  }
  writeFileSync(join(out, "load.sql"), `${load.join("\n")}\n`);

  // Validate exact expected bytes before any status mutation. Each assertion stays below D1's
  // statement limit. Execute the entire file in the local D1 batch; any error aborts activation.
  // The assertions also detect a missing path replaced by an extra row with the same total count.
  const validation = [
    `SELECT CASE WHEN EXISTS (SELECT 1 FROM snapshot_meta WHERE snapshot_id = ${sqlText(snapshotId)} AND projection_schema_version = ${PROJECTION_SCHEMA_VERSION} AND scope_json = ${sqlText(scopeJson)} AND path_count = ${rows.length} AND part_count = ${partCount}) AND (SELECT COUNT(*) FROM public_read WHERE snapshot_id = ${sqlText(snapshotId)}) = ${partCount} THEN 1 ELSE json('INVALID_PROJECTION_METADATA') END;`,
    ...parts.map((row) => `SELECT CASE WHEN EXISTS (SELECT 1 FROM public_read WHERE snapshot_id = ${sqlText(snapshotId)} AND path = ${sqlText(row.path)} AND part = ${row.part} AND status = ${row.status} AND content_sha256 = ${sqlText(row.sha256)} AND body_gzip = X'${row.chunk.toString('hex')}') THEN 1 ELSE json('INCOMPLETE_OR_CORRUPT_PROJECTION') END;`),
  ];
  // The metadata manifest can exceed the statement limit: verify its hash through exact bounded
  // substring assertions, keeping the main assertion constant-size.
  validation[0] = validation[0].replace(`scope_json = ${sqlText(scopeJson)}`, `length(scope_json) = ${[...scopeJson].length}`);
  for (let offset = 0; offset < scopeJson.length; offset += 20_000) {
    const chunk = scopeJson.slice(offset, offset + 20_000);
    validation.push(`SELECT CASE WHEN EXISTS (SELECT 1 FROM snapshot_meta WHERE snapshot_id = ${sqlText(snapshotId)} AND substr(scope_json, ${offset + 1}, ${chunk.length}) = ${sqlText(chunk)}) THEN 1 ELSE json('INVALID_PROJECTION_MANIFEST') END;`);
  }
  writeFileSync(join(out, 'validate.sql'), `${validation.join('\n')}\n`);

  const complete = `(SELECT COUNT(*) FROM public_read WHERE snapshot_id = ${sqlText(snapshotId)}) = ${partCount} AND EXISTS (SELECT 1 FROM snapshot_meta WHERE snapshot_id = ${sqlText(snapshotId)} AND status = 'STAGED')`;
  writeFileSync(join(out, "activate.sql"), `${[
    `-- Activate ${snapshotId}; the current ACTIVE becomes PREVIOUS (the rollback target).`,
    ...validation,
    `UPDATE snapshot_meta SET status = CASE WHEN snapshot_id = ${sqlText(snapshotId)} THEN 'ACTIVE' WHEN status = 'ACTIVE' THEN 'PREVIOUS' ELSE 'RETIRED' END WHERE (snapshot_id = ${sqlText(snapshotId)} OR status IN ('ACTIVE', 'PREVIOUS')) AND ${complete};`,
    "DELETE FROM public_read WHERE snapshot_id IN (SELECT snapshot_id FROM snapshot_meta WHERE status = 'RETIRED');",
    "DELETE FROM snapshot_meta WHERE status = 'RETIRED';",
  ].join("\n")}\n`);
  // Roll back to THIS exported snapshot. Retrying after response loss is a no-op, never a swap back.
  writeFileSync(join(out, "rollback.sql"), `${[
    `-- Restore ${snapshotId} if it is PREVIOUS; current ACTIVE becomes PREVIOUS.`,
    ...validation,
    `UPDATE snapshot_meta SET status = CASE WHEN snapshot_id = ${sqlText(snapshotId)} THEN 'ACTIVE' ELSE 'PREVIOUS' END WHERE status IN ('ACTIVE', 'PREVIOUS') AND EXISTS (SELECT 1 FROM snapshot_meta WHERE snapshot_id = ${sqlText(snapshotId)} AND status = 'PREVIOUS') AND (SELECT COUNT(*) FROM snapshot_meta WHERE status = 'PREVIOUS') = 1 AND (SELECT COUNT(*) FROM snapshot_meta WHERE status = 'ACTIVE') = 1;`,
  ].join("\n")}\n`);

  const manifest = {
    ...semantic,
    rows: undefined,
    snapshot_id: snapshotId,
    semantic_sha256: semanticSha256,
    generated_at: generatedAt.toISOString(),
    generated_at_kst: generatedAtKst,
    git_commit: gitCommit,
    counts: {
      public_people: people.length,
      public_organizations: organizations.length,
      sources: sourceIds.size,
      paths: rows.length,
      parts: partCount,
      client_error_paths: rows.filter((row) => row.status >= 400).length,
      json_bytes: rows.reduce((sum, row) => sum + row.bytes, 0),
      gzip_bytes: rows.reduce((sum, row) => sum + row.gzip.length, 0),
      max_gzip_row_bytes: Math.max(...rows.map((row) => row.gzip.length)),
    },
    paths: rows.map(({ path, status, sha256: digest, bytes, gzip }) => ({ path, status, sha256: digest, bytes, gzip_bytes: gzip.length })),
  };
  writeFileSync(join(out, "projection-manifest.json"), `${JSON.stringify(manifest, null, 2)}\n`);
  console.log(JSON.stringify({ status: "PASS", out, snapshot_id: snapshotId, semantic_sha256: semanticSha256, counts: manifest.counts }, null, 2));
}

await main();

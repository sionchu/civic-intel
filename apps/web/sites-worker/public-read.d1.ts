// D1 transport for the Sites Worker build (copied over app/public-read.ts by
// scripts/build-sites-worker.mjs). It serves the exact publication-gated API DTO that
// scripts/export-public-projection.mjs exported for the ACTIVE snapshot. It makes no identity,
// publication or SourcePolicy decision: unknown UUIDs are 404, invalid UUIDs are 422, and lost
// exported rows are transport failures (never UNKNOWN facts).
import { env } from "cloudflare:workers";
import { cacheForRequest } from "vinext/cache";
// This module is copied to app/public-read.ts by the Worker build.
import { PERSON_RELATIONSHIP_QUERY } from "./relationship-path.mjs";

export type PublicReadResponse = {
  status: number;
  body: unknown;
  requestId: string | null;
};

type ActiveSnapshot = {
  snapshot_id: string; scope_json: string; generated_at_kst: string; projection_schema_version: number;
};
type Scope = { patterns: string[]; paths: Record<string, [number, string]> };
type PublicReadPart = { part: number; status: number; content_sha256: string; body_gzip: ArrayBuffer | number[] };

// Vinext's request cache also covers metadata and layout probes outside React's RSC dispatcher.
// It is deliberately not a process-global cache: the next request sees the current ACTIVE.
const activeSnapshot = cacheForRequest(async () => {
  if (!env.DB) throw new Error("D1 binding DB is not configured");
  const active = await env.DB
    .prepare("SELECT snapshot_id, scope_json, generated_at_kst, projection_schema_version FROM snapshot_meta WHERE status = 'ACTIVE'")
    .all<ActiveSnapshot>();
  if (active.results.length !== 1) throw new Error(`expected one ACTIVE snapshot, found ${active.results.length}`);
  const snapshot = active.results[0];
  if (snapshot.projection_schema_version !== 2) throw new Error("unsupported public projection schema");
  return { ...snapshot, scope: JSON.parse(snapshot.scope_json) as Scope };
});

export async function readSnapshotAt(): Promise<string> {
  return (await activeSnapshot()).generated_at_kst;
}

async function gunzipJson(parts: PublicReadPart[], expected: [number, string]): Promise<unknown> {
  if (parts.some((part, index) => part.part !== index || part.status !== expected[0] || part.content_sha256 !== expected[1])) {
    throw new Error("inconsistent public projection parts");
  }
  const blob = new Blob(parts.map((part) => new Uint8Array(part.body_gzip)));
  const stream = blob.stream().pipeThrough(new DecompressionStream("gzip"));
  const bytes = await new Response(stream).arrayBuffer();
  const digest = [...new Uint8Array(await crypto.subtle.digest("SHA-256", bytes))]
    .map((byte) => byte.toString(16).padStart(2, "0")).join("");
  if (digest !== expected[1]) throw new Error("corrupt public projection response");
  return JSON.parse(new TextDecoder().decode(bytes));
}

// Same signature as the HTTP transport; revalidation hints do not apply to a fixed snapshot.
export async function readPublic(path: string, _options?: { revalidateSeconds?: number }): Promise<PublicReadResponse> {
  const invalidInput = (): PublicReadResponse => ({ status: 422, body: { error: { code: 'INVALID_INPUT', message: 'The request input is invalid.' } }, requestId: null });
  const relationship = path.match(/^\/relationships\/people\/([^/?]+)(?:\?([^#]*))?$/);
  if (relationship) {
    const query = new URLSearchParams(relationship[2] ?? '');
    const expected = new URLSearchParams(PERSON_RELATIONSHIP_QUERY);
    if ([...query].length !== [...expected].length || [...expected].some(([key, value]) => query.getAll(key).length !== 1 || query.get(key) !== value)) return invalidInput();
    let hex = '';
    try { hex = decodeURIComponent(relationship[1]).replace(/^urn:uuid:/, '').replace(/^\{+|\}+$/g, '').replaceAll('-', '').toLowerCase(); } catch { /* Invalid encoded UUID. */ }
    if (!/^[0-9a-f]{32}$/.test(hex)) return invalidInput();
    path = `/relationships/people/${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}?${PERSON_RELATIONSHIP_QUERY}`;
  }
  // The HTTP API parses UUID path inputs before looking up a record. Normalize its common
  // accepted forms to the exported key; this is input parsing, never identity resolution.
  const entity = path.match(/^(\/people|\/organizations|\/sources|\/ontology\/people|\/ontology\/organizations)\/([^/?]+)(\/money\?earlier_fiscal_year=2024&later_fiscal_year=2025)?$/);
  if (entity && (!entity[3] || entity[1] === '/organizations')) {
    let hex = '';
    try { hex = decodeURIComponent(entity[2]).replace(/^urn:uuid:/, '').replace(/^\{+|\}+$/g, '').replaceAll('-', '').toLowerCase(); } catch { /* invalid percent encoding is invalid input */ }
    if (!/^[0-9a-f]{32}$/.test(hex)) {
      return { status: 422, body: { error: { code: 'INVALID_INPUT', message: 'The request input is invalid.' } }, requestId: null };
    }
    path = `${entity[1]}/${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}${entity[3] ?? ''}`;
  }
  const snapshot = await activeSnapshot();
  const db = env.DB;
  if (!db) throw new Error("D1 binding DB is not configured");

  const { results: parts } = await db
    .prepare("SELECT part, status, content_sha256, body_gzip FROM public_read WHERE snapshot_id = ? AND path = ? ORDER BY part")
    .bind(snapshot.snapshot_id, path)
    .all<PublicReadPart>();
  const expected = snapshot.scope.paths[path];
  if (expected) {
    if (parts.length === 0) throw new Error("missing exported public projection response");
    return { status: expected[0], body: await gunzipJson(parts, expected), requestId: null };
  }
  if (parts.length > 0) throw new Error("unexpected public projection response");

  const scopes = snapshot.scope.patterns.map((pattern) => new RegExp(pattern));
  if (scopes.some((scope) => scope.test(path))) return { status: 404, body: null, requestId: null };
  throw new Error(`${path} is outside the exported public projection`);
}

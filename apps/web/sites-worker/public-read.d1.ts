// D1 transport for the Sites Worker build (copied over app/public-read.ts by
// scripts/build-sites-worker.mjs). It serves the exact publication-gated API DTO that
// scripts/export-public-projection.mjs exported for the ACTIVE snapshot. It makes no identity,
// publication or SourcePolicy decision: a missing row inside an exported scope is a public 404,
// and anything else that cannot be read is a transport failure (never an UNKNOWN fact).
import { env } from "cloudflare:workers";

export type PublicReadResponse = {
  status: number;
  body: unknown;
  requestId: string | null;
};

type ActiveSnapshot = { snapshot_id: string; scope_json: string };
type PublicReadPart = { status: number; body_gzip: ArrayBuffer | number[] };

async function gunzipJson(parts: PublicReadPart[]): Promise<unknown> {
  const blob = new Blob(parts.map((part) => new Uint8Array(part.body_gzip)));
  const stream = blob.stream().pipeThrough(new DecompressionStream("gzip"));
  return JSON.parse(await new Response(stream).text());
}

// Same signature as the HTTP transport; revalidation hints do not apply to a fixed snapshot.
export async function readPublic(path: string, _options?: { revalidateSeconds?: number }): Promise<PublicReadResponse> {
  const db = env.DB;
  if (!db) throw new Error("D1 binding DB is not configured");
  const active = await db
    .prepare("SELECT snapshot_id, scope_json FROM snapshot_meta WHERE status = 'ACTIVE'")
    .all<ActiveSnapshot>();
  if (active.results.length !== 1) throw new Error(`expected one ACTIVE snapshot, found ${active.results.length}`);
  const snapshot = active.results[0];

  const { results: parts } = await db
    .prepare("SELECT status, body_gzip FROM public_read WHERE snapshot_id = ? AND path = ? ORDER BY part")
    .bind(snapshot.snapshot_id, path)
    .all<PublicReadPart>();
  if (parts.length > 0) return { status: parts[0].status, body: await gunzipJson(parts), requestId: null };

  const scopes = (JSON.parse(snapshot.scope_json) as string[]).map((pattern) => new RegExp(pattern));
  if (scopes.some((scope) => scope.test(path))) return { status: 404, body: null, requestId: null };
  throw new Error(`${path} is outside the exported public projection`);
}

// Canonical bounded transport metadata for the existing replaceable D1 read snapshot.
// Payload bytes stay in public_read; no publication or identity decision is made here.
import { createHash } from 'node:crypto';

export const digest = (value) => createHash('sha256').update(value).digest('hex');
export const WRITER_VERSION = 1;
export const MAX_METADATA_ROW_BYTES = 1_900_000;

export function snapshotProtocol(manifest, parts) {
  const grouped = new Map();
  for (const part of parts) {
    const list = grouped.get(part.path) ?? [];
    if (part.part !== list.length || part.chunk.length > 40_000 || !part.chunk.length) throw new Error('INVALID_PART_ORDER');
    list.push(digest(part.chunk));
    grouped.set(part.path, list);
  }
  const paths = Object.fromEntries(manifest.paths.map((row) => {
    const hashes = grouped.get(row.path);
    if (!hashes || hashes.length !== Math.ceil(row.gzip_bytes / 40_000)) throw new Error('INVALID_PART_COUNT');
    return [row.path, [row.status, row.sha256, row.bytes, row.gzip_bytes, hashes]];
  }));
  const scope = JSON.stringify({ patterns: manifest.scopes, paths, writer: {
    version: WRITER_VERSION, snapshot_id: manifest.snapshot_id,
    semantic_sha256: manifest.semantic_sha256, projection_schema_version: manifest.projection_schema_version,
    generated_at: manifest.generated_at, generated_at_kst: manifest.generated_at_kst,
    git_commit: manifest.git_commit, counts: manifest.counts,
  } });
  // SQLite's row limit includes all values, not only scope_json. Reserve 100 KB for
  // scalar metadata and protocol state; reject rather than depending on implicit truncation.
  const bytes = Buffer.byteLength(scope);
  if (bytes > MAX_METADATA_ROW_BYTES) throw new Error('PROTOCOL_METADATA_ROW_TOO_LARGE');
  return { version: WRITER_VERSION, snapshot_id: manifest.snapshot_id,
    manifest_sha256: digest(scope), metadata_bytes: bytes, scope_json: scope };
}

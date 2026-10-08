// D1 schema for the 모두의국감 Sites Worker: a REPLACEABLE_PUBLIC_READ_SNAPSHOT_NOT_SSOT.
// PostgreSQL stays the canonical store; D1 only holds publication-gated API responses that
// `scripts/export-public-projection.mjs` exported, keyed by the exact API path the pages read.
// No identity, publication or SourcePolicy decision is made here.
import { sql } from "drizzle-orm";
import { blob, check, integer, primaryKey, sqliteTable, text } from "drizzle-orm/sqlite-core";

export const snapshotMeta = sqliteTable("snapshot_meta", {
  snapshotId: text("snapshot_id").primaryKey(),
  // STAGED → ACTIVE → PREVIOUS → RETIRED. Exactly one ACTIVE snapshot is served.
  // The finite writer retains retired rows for already pinned readers; GC is separate.
  status: text("status").notNull(),
  projectionSchemaVersion: integer("projection_schema_version").notNull(),
  generatedAt: text("generated_at").notNull(),
  generatedAtKst: text("generated_at_kst").notNull(),
  gitCommit: text("git_commit").notNull(),
  // Versioned JSON {patterns, paths}: exact expected paths/status/hashes distinguish corrupt or
  // missing exported rows from unknown UUIDs (404). No additional payload store.
  scopeJson: text("scope_json").notNull(),
  pathCount: integer("path_count").notNull(),
  partCount: integer("part_count").notNull(),
  publicPeople: integer("public_people").notNull(),
  publicOrganizations: integer("public_organizations").notNull(),
  // Finite maintenance protocol state. Legacy local snapshots have no writer manifest;
  // they remain readable but cannot bypass the authenticated upload/seal protocol.
  writerManifestSha256: text("writer_manifest_sha256"),
  writerPhase: text("writer_phase"),
  writerCursor: integer("writer_cursor").notNull().default(0),
  validationCursor: integer("validation_cursor").notNull().default(0),
  pointerEpoch: integer("pointer_epoch").notNull().default(0),
  writerTransitionSha256: text("writer_transition_sha256"),
}, (table) => [
  check("snapshot_meta_status", sql`${table.status} IN ('STAGED', 'ACTIVE', 'PREVIOUS', 'RETIRED')`),
]);

// One API response per path, gzip-compressed and split into ordered parts so that every INSERT stays
// under the D1 SQL statement length limit (SQLITE_TOOBIG at 100 KB, seen in local D1).
export const publicRead = sqliteTable("public_read", {
  snapshotId: text("snapshot_id").notNull(),
  path: text("path").notNull(),
  part: integer("part").notNull(),
  // HTTP status the private API returned for this path (2xx, or a public 4xx such as 404/422).
  status: integer("status").notNull(),
  contentSha256: text("content_sha256").notNull(),
  bodyGzip: blob("body_gzip", { mode: "buffer" }).notNull(),
}, (table) => [primaryKey({ columns: [table.snapshotId, table.path, table.part] })]);

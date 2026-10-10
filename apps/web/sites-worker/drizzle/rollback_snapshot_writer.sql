-- Explicit disposable-database rollback only; never bundled as a forward migration.
ALTER TABLE snapshot_meta DROP COLUMN writer_transition_sha256;
ALTER TABLE snapshot_meta DROP COLUMN pointer_epoch;
ALTER TABLE snapshot_meta DROP COLUMN validation_cursor;
ALTER TABLE snapshot_meta DROP COLUMN writer_cursor;
ALTER TABLE snapshot_meta DROP COLUMN writer_phase;
ALTER TABLE snapshot_meta DROP COLUMN writer_manifest_sha256;

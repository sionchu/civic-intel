ALTER TABLE snapshot_meta ADD COLUMN writer_manifest_sha256 text;
--> statement-breakpoint
ALTER TABLE snapshot_meta ADD COLUMN writer_phase text;
--> statement-breakpoint
ALTER TABLE snapshot_meta ADD COLUMN writer_cursor integer NOT NULL DEFAULT 0;
--> statement-breakpoint
ALTER TABLE snapshot_meta ADD COLUMN validation_cursor integer NOT NULL DEFAULT 0;
--> statement-breakpoint
ALTER TABLE snapshot_meta ADD COLUMN pointer_epoch integer NOT NULL DEFAULT 0;
--> statement-breakpoint
ALTER TABLE snapshot_meta ADD COLUMN writer_transition_sha256 text;

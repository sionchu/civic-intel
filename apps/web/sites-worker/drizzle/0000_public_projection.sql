CREATE TABLE `public_read` (
	`snapshot_id` text NOT NULL,
	`path` text NOT NULL,
	`part` integer NOT NULL,
	`status` integer NOT NULL,
	`content_sha256` text NOT NULL,
	`body_gzip` blob NOT NULL,
	PRIMARY KEY(`snapshot_id`, `path`, `part`)
);
--> statement-breakpoint
CREATE TABLE `snapshot_meta` (
	`snapshot_id` text PRIMARY KEY NOT NULL,
	`status` text NOT NULL,
	`projection_schema_version` integer NOT NULL,
	`generated_at` text NOT NULL,
	`generated_at_kst` text NOT NULL,
	`git_commit` text NOT NULL,
	`scope_json` text NOT NULL,
	`path_count` integer NOT NULL,
	`part_count` integer NOT NULL,
	`public_people` integer NOT NULL,
	`public_organizations` integer NOT NULL,
	CONSTRAINT "snapshot_meta_status" CHECK("snapshot_meta"."status" IN ('STAGED', 'ACTIVE', 'PREVIOUS', 'RETIRED'))
);

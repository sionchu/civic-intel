export type ReviewedPortrait = {
  person_id: string;
  canonical_name: string;
  local_path: string;
  source_kind: string;
  file_title: string;
  source_page_url: string;
  source_original_url: string;
  creator: string;
  license: string;
  license_url: string;
  attribution_text: string;
  commercial_use_allowed: boolean;
  derivatives_allowed: boolean;
  modification_note: string;
  source_sha1: string;
  source_byte_size: number;
  source_width: number;
  source_height: number;
  source_mime: string;
  source_revision_timestamp: string;
  rights_checked_at: string;
  identity_checked_at: string;
  assembly_profile_url: string;
  assembly_mona_cd: string;
  review_status: "ELIGIBLE" | "WITHDRAWN" | "REVIEW_REQUIRED";
};

export type PortraitManifest = { version: 1; portraits: ReviewedPortrait[] };

export function validatePortraitManifest(value: unknown): PortraitManifest;
export function selectReviewedPortrait(
  person: { id: string; identity_status: string },
  manifest: unknown,
): ReviewedPortrait | null;

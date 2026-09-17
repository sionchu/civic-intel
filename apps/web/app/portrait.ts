import { readFile } from "node:fs/promises";
import { join } from "node:path";

import type { Person } from "./types";

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

type PortraitManifest = {
  version: 1;
  portraits: ReviewedPortrait[];
};

const LOCAL_PORTRAIT_PREFIX = "/portraits/";

function isSafeLocalPortraitPath(value: string): boolean {
  return value.startsWith(LOCAL_PORTRAIT_PREFIX) && !value.includes("..") && !value.includes("\\");
}

/**
 * Presentation-only lookup. Canonical identity comes from the API Person; the manifest
 * contributes a portrait only after an exact resolved Person ID match.
 */
export async function getReviewedPortrait(person: Person): Promise<ReviewedPortrait | null> {
  if (person.identity_status !== "RESOLVED") return null;

  try {
    const manifestPath = join(process.cwd(), "public", "portraits", "manifest.json");
    const manifest = JSON.parse(await readFile(manifestPath, "utf8")) as PortraitManifest;
    const portrait = manifest.portraits.find((candidate) => (
      candidate.person_id === person.id
      && candidate.review_status === "ELIGIBLE"
      && isSafeLocalPortraitPath(candidate.local_path)
    ));
    return portrait ?? null;
  } catch {
    return null;
  }
}

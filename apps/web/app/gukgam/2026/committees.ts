// Presentation helpers for the Claim-backed Gukgam committee projection.
// The anchor is derived from the official committee name only; it never merges or renames names.

export const GUKGAM_COMMITTEE_SECTION_ID = "gukgam-committees";

export function committeeAnchor(committeeName: string): string {
  return `committee-${committeeName.trim().replace(/\s+/g, "-")}`;
}

export function committeeHref(committeeName: string): string {
  return `/gukgam/2026#${committeeAnchor(committeeName)}`;
}

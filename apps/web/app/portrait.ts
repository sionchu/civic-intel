// Bundled with the code (not read from disk at request time) so the lookup also works in the
// Sites Worker runtime, which has no project filesystem.
import portraitManifest from "../public/portraits/manifest.json";
import { selectReviewedPortrait } from "./portrait-contract.mjs";
import type { ReviewedPortrait } from "./portrait-contract.mjs";
import type { Person } from "./types";

export type { ReviewedPortrait } from "./portrait-contract.mjs";

/**
 * Presentation-only lookup. Canonical identity comes from the API Person; the manifest
 * contributes a portrait only after an exact resolved Person ID match.
 */
export async function getReviewedPortrait(person: Person): Promise<ReviewedPortrait | null> {
  return selectReviewedPortrait(person, portraitManifest);
}

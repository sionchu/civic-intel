// Pure manifest rules shared by the bundled lookup and the local asset build check.
// The manifest records an existing review; these rules never grant rights or identity.
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/;
const STATUSES = new Set(["ELIGIBLE", "WITHDRAWN", "REVIEW_REQUIRED"]);
const REQUIRED_TEXT = [
  "person_id", "canonical_name", "local_path", "source_kind", "file_title",
  "source_page_url", "source_original_url", "creator", "license", "license_url",
  "attribution_text", "modification_note", "source_sha1", "source_mime",
  "source_revision_timestamp", "rights_checked_at", "identity_checked_at",
  "assembly_profile_url", "assembly_mona_cd", "review_status",
];

export function validatePortraitManifest(value) {
  if (!value || value.version !== 1 || !Array.isArray(value.portraits)) {
    throw new Error("Portrait manifest must declare version 1 and a portraits array.");
  }
  const personIds = new Set();
  const paths = new Set();
  for (const [index, portrait] of value.portraits.entries()) {
    if (!portrait || typeof portrait !== "object" || Array.isArray(portrait)) {
      throw new Error(`Portrait ${index} is not a record.`);
    }
    for (const field of REQUIRED_TEXT) {
      if (typeof portrait[field] !== "string" || portrait[field].trim() === "") {
        throw new Error(`Portrait ${index} is missing ${field}.`);
      }
    }
    if (!UUID.test(portrait.person_id) || personIds.has(portrait.person_id)) {
      throw new Error(`Portrait ${index} has an invalid or duplicate Person ID.`);
    }
    // One reviewed local file per exact Person; no traversal, encodings, URL suffixes,
    // alternate person's filename or path alias can redirect this binding.
    const file = portrait.local_path.match(/^\/portraits\/([0-9a-f-]+)\.(jpg|jpeg|png|webp)$/);
    if (!file || file[1] !== portrait.person_id || paths.has(portrait.local_path)) {
      throw new Error(`Portrait ${index} has an invalid or duplicate local path.`);
    }
    if (!STATUSES.has(portrait.review_status)) {
      throw new Error(`Portrait ${index} has an invalid review status.`);
    }
    if (!/^[0-9a-f]{40}$/i.test(portrait.source_sha1)) {
      throw new Error(`Portrait ${index} has an invalid SHA-1.`);
    }
    for (const field of ["source_byte_size", "source_width", "source_height"]) {
      if (!Number.isInteger(portrait[field]) || portrait[field] <= 0) {
        throw new Error(`Portrait ${index} has invalid ${field}.`);
      }
    }
    for (const field of ["commercial_use_allowed", "derivatives_allowed"]) {
      if (typeof portrait[field] !== "boolean") {
        throw new Error(`Portrait ${index} has invalid ${field}.`);
      }
    }
    personIds.add(portrait.person_id);
    paths.add(portrait.local_path);
  }
  return value;
}

export function selectReviewedPortrait(person, manifest) {
  if (person.identity_status !== "RESOLVED") return null;
  try {
    const reviewed = validatePortraitManifest(manifest);
    return reviewed.portraits.find((candidate) => (
      candidate.person_id === person.id && candidate.review_status === "ELIGIBLE"
    )) ?? null;
  } catch {
    // Build validation explains the error; runtime must never select an ambiguous file.
    return null;
  }
}

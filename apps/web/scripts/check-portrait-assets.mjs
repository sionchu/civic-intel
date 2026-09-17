import { createHash } from "node:crypto";
import { readFile, stat } from "node:fs/promises";
import { dirname, isAbsolute, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const appRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const portraitsRoot = resolve(appRoot, "public", "portraits");
const manifestPath = resolve(portraitsRoot, "manifest.json");
const manifest = JSON.parse(await readFile(manifestPath, "utf8"));

if (manifest.version !== 1 || !Array.isArray(manifest.portraits) || manifest.portraits.length === 0) {
  throw new Error("Portrait manifest must declare version 1 and at least one portrait.");
}

const requiredStringFields = [
  "person_id",
  "canonical_name",
  "local_path",
  "source_kind",
  "file_title",
  "source_page_url",
  "source_original_url",
  "creator",
  "license",
  "license_url",
  "attribution_text",
  "modification_note",
  "source_sha1",
  "source_mime",
  "source_revision_timestamp",
  "rights_checked_at",
  "identity_checked_at",
  "assembly_profile_url",
  "assembly_mona_cd",
  "review_status",
];

for (const [index, portrait] of manifest.portraits.entries()) {
  for (const field of requiredStringFields) {
    if (typeof portrait[field] !== "string" || portrait[field].trim() === "") {
      throw new Error(`Portrait ${index} is missing ${field}.`);
    }
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
  if (portrait.review_status !== "ELIGIBLE") {
    throw new Error(`Portrait ${portrait.person_id} is not eligible for publication.`);
  }
  if (!portrait.local_path.startsWith("/portraits/") || portrait.local_path.includes("..") || portrait.local_path.includes("\\")) {
    throw new Error(`Portrait ${portrait.person_id} must use a local /portraits path.`);
  }

  const relativePath = portrait.local_path.slice("/portraits/".length);
  const filePath = resolve(portraitsRoot, relativePath);
  const relativeToRoot = relative(portraitsRoot, filePath);
  if (!relativeToRoot || relativeToRoot.startsWith("..") || isAbsolute(relativeToRoot)) {
    throw new Error(`Portrait ${portrait.person_id} escapes the portraits directory.`);
  }
  const file = await readFile(filePath);
  const metadata = await stat(filePath);
  const sha1 = createHash("sha1").update(file).digest("hex");
  if (metadata.size !== portrait.source_byte_size) {
    throw new Error(`Portrait ${portrait.person_id} byte size does not match the manifest.`);
  }
  if (sha1 !== portrait.source_sha1.toLowerCase()) {
    throw new Error(`Portrait ${portrait.person_id} SHA-1 does not match the manifest.`);
  }
}

console.log(`Portrait asset integrity verified: ${manifest.portraits.length} record(s).`);

import { createHash } from "node:crypto";
import { readFile, readdir } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { validatePortraitManifest } from "../app/portrait-contract.mjs";

const appRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");

export async function checkPortraitAssets(portraitsRoot = resolve(appRoot, "public", "portraits")) {
  const manifest = validatePortraitManifest(JSON.parse(
    await readFile(resolve(portraitsRoot, "manifest.json"), "utf8"),
  ));
  const eligible = manifest.portraits.filter((portrait) => portrait.review_status === "ELIGIBLE");
  const expectedFiles = new Set([
    "manifest.json", "README.md", ...eligible.map((portrait) => portrait.local_path.slice("/portraits/".length)),
  ]);
  // public/ is served directly, independently of the Person page lookup. Withdrawing
  // a record is only safe after its bytes are removed from this served directory.
  for (const entry of await readdir(portraitsRoot, { withFileTypes: true })) {
    if (!entry.isFile() || !expectedFiles.has(entry.name)) {
      throw new Error("Portrait directory contains unreviewed, inactive or non-regular files.");
    }
  }
  for (const portrait of eligible) {
    const file = await readFile(resolve(portraitsRoot, portrait.local_path.slice("/portraits/".length)));
    const sha1 = createHash("sha1").update(file).digest("hex");
    if (file.byteLength !== portrait.source_byte_size) {
      throw new Error("Portrait byte size does not match the manifest.");
    }
    if (sha1 !== portrait.source_sha1.toLowerCase()) {
      throw new Error("Portrait SHA-1 does not match the manifest.");
    }
  }
  return {
    eligible: eligible.length,
    withdrawn: manifest.portraits.filter((portrait) => portrait.review_status === "WITHDRAWN").length,
    reviewRequired: manifest.portraits.filter((portrait) => portrait.review_status === "REVIEW_REQUIRED").length,
  };
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const coverage = await checkPortraitAssets();
  console.log(`Portrait asset integrity verified: ${coverage.eligible} eligible, ${coverage.withdrawn} withdrawn, ${coverage.reviewRequired} review required.`);
}

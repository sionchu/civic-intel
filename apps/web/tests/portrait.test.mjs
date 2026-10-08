import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { mkdir, mkdtemp, readFile, rm, unlink, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import test from "node:test";

import { selectReviewedPortrait, validatePortraitManifest } from "../app/portrait-contract.mjs";
import { checkPortraitAssets } from "../scripts/check-portrait-assets.mjs";

const PERSON = "11111111-1111-4111-8111-111111111111";
const OTHER = "22222222-2222-4222-8222-222222222222";
const BYTES = Buffer.from("synthetic portrait integrity fixture");
const BASE = {
  person_id: PERSON,
  canonical_name: "합성 인물",
  local_path: `/portraits/${PERSON}.jpg`,
  source_kind: "SYNTHETIC_TEST_ONLY",
  file_title: "Synthetic fixture",
  source_page_url: "https://example.org/fixture",
  source_original_url: "https://example.org/fixture.jpg",
  creator: "Synthetic creator",
  license: "SYNTHETIC_TEST_ONLY",
  license_url: "https://example.org/license",
  attribution_text: "Synthetic test fixture, never published",
  commercial_use_allowed: false,
  derivatives_allowed: false,
  modification_note: "Synthetic integrity bytes, not a person's image",
  source_sha1: createHash("sha1").update(BYTES).digest("hex"),
  source_byte_size: BYTES.byteLength,
  source_width: 1,
  source_height: 1,
  source_mime: "image/jpeg",
  source_revision_timestamp: "2099-01-01T00:00:00Z",
  rights_checked_at: "2099-01-01",
  identity_checked_at: "2099-01-01",
  assembly_profile_url: "https://example.org/person",
  assembly_mona_cd: "SYNTH001",
  review_status: "ELIGIBLE",
};
const manifest = (overrides = {}) => ({ version: 1, portraits: [{ ...BASE, ...overrides }] });
const resolved = (id = PERSON) => ({ id, canonical_name: BASE.canonical_name, identity_status: "RESOLVED" });

async function directory(t, data = manifest(), includeBytes = true) {
  const root = await mkdtemp(join(tmpdir(), "civic-portrait-test-"));
  t.after(async () => {
    assert.equal(dirname(resolve(root)), resolve(tmpdir()));
    assert.ok(root.startsWith(join(tmpdir(), "civic-portrait-test-")));
    await rm(root, { recursive: true, force: true });
  });
  await writeFile(join(root, "manifest.json"), JSON.stringify(data));
  if (includeBytes) await writeFile(join(root, `${PERSON}.jpg`), BYTES);
  return root;
}

test("portrait selection requires exact resolved identity, not a matching name", () => {
  assert.equal(selectReviewedPortrait(resolved(), manifest())?.person_id, PERSON);
  assert.equal(selectReviewedPortrait(resolved(OTHER), manifest()), null);
  assert.equal(selectReviewedPortrait({ ...resolved(), identity_status: "UNRESOLVED" }, manifest()), null);
  assert.equal(selectReviewedPortrait(resolved(), manifest({ review_status: "WITHDRAWN" })), null);
  assert.equal(selectReviewedPortrait(resolved(), manifest({ review_status: "REVIEW_REQUIRED" })), null);
});

test("duplicate or malformed bindings fail closed instead of selecting the first record", () => {
  const duplicate = { version: 1, portraits: [{ ...BASE }, { ...BASE, review_status: "WITHDRAWN" }] };
  assert.throws(() => validatePortraitManifest(duplicate), /duplicate Person ID/);
  assert.equal(selectReviewedPortrait(resolved(), duplicate), null);
  for (const local_path of [
    `/portraits/${OTHER}.jpg`, `/portraits/../${PERSON}.jpg`, `/portraits/%2e%2e/${PERSON}.jpg`,
    `/portraits/${PERSON}.jpg?file=other`, `/portraits/${PERSON}.jpg#fragment`,
    `/portraits/\\${PERSON}.jpg`, `https://example.org/${PERSON}.jpg`,
  ]) {
    assert.throws(() => validatePortraitManifest(manifest({ local_path })), /local path/);
    assert.equal(selectReviewedPortrait(resolved(), manifest({ local_path })), null);
  }
  assert.equal(selectReviewedPortrait(resolved(), { version: 2, portraits: [{ ...BASE }] }), null);
});

test("reviewed pilot bytes and exact canonical binding remain intact", async () => {
  const actual = JSON.parse(await readFile(new URL("../public/portraits/manifest.json", import.meta.url), "utf8"));
  const pilot = selectReviewedPortrait(resolved("44745d09-398c-46ce-bc38-81f0f606c1d7"), actual);
  assert.ok(pilot);
  assert.equal(pilot.source_sha1, "46f16ce27199a761bb472cb0f68a763a3afa16db");
  assert.equal(pilot.source_byte_size, 38558);
  const coverage = await checkPortraitAssets();
  assert.ok(coverage.eligible >= 1);
});

test("integrity check refuses changed bytes even when their length is unchanged", async (t) => {
  const root = await directory(t);
  assert.deepEqual(await checkPortraitAssets(root), { eligible: 1, withdrawn: 0, reviewRequired: 0 });
  await writeFile(join(root, `${PERSON}.jpg`), Buffer.alloc(BYTES.byteLength, 1));
  await assert.rejects(checkPortraitAssets(root), /SHA-1/);
  await writeFile(join(root, `${PERSON}.jpg`), "changed size");
  await assert.rejects(checkPortraitAssets(root), /byte size/);
});

test("withdrawal succeeds only after inactive bytes leave the served directory", async (t) => {
  const data = manifest({ review_status: "WITHDRAWN" });
  const root = await directory(t, data);
  assert.equal(selectReviewedPortrait(resolved(), data), null);
  await assert.rejects(checkPortraitAssets(root), /inactive/);
  await unlink(join(root, `${PERSON}.jpg`));
  assert.deepEqual(await checkPortraitAssets(root), { eligible: 0, withdrawn: 1, reviewRequired: 0 });
});

test("zero eligible and pending review remain valid only without public image bytes", async (t) => {
  const root = await directory(t, { version: 1, portraits: [] }, false);
  assert.deepEqual(await checkPortraitAssets(root), { eligible: 0, withdrawn: 0, reviewRequired: 0 });
  await writeFile(join(root, "manifest.json"), JSON.stringify(manifest({ review_status: "REVIEW_REQUIRED" })));
  assert.deepEqual(await checkPortraitAssets(root), { eligible: 0, withdrawn: 0, reviewRequired: 1 });
  await writeFile(join(root, `${OTHER}.jpg`), BYTES);
  await assert.rejects(checkPortraitAssets(root), /unreviewed/);
});

test("served portrait directory cannot hide unregistered files in subdirectories", async (t) => {
  const root = await directory(t);
  await mkdir(join(root, "unreviewed"));
  await assert.rejects(checkPortraitAssets(root), /non-regular/);
});

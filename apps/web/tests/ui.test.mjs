import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

test("profile preserves epistemic labels and traceability", async () => {
  const page = await readFile(new URL("../app/people/[id]/page.tsx", import.meta.url), "utf8");
  assert.match(page, /epistemic_status/);
  assert.match(page, /evidence\.map/);
  assert.match(page, /source_ids/);
  assert.match(page, /UNKNOWN/);
  assert.match(page, /resolution_note/);
  assert.match(page, /asserted_as_true/);
  assert.match(page, /publication_status/);
});

test("UI does not implement publication decisions", async () => {
  const files = await Promise.all(["../app/page.tsx", "../app/people/[id]/page.tsx"].map((path) => readFile(new URL(path, import.meta.url), "utf8")));
  assert.ok(files.every((body) => !body.includes("validate_claim_publication")));
});

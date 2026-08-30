import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

test("profile renders section coverage and evidence traceability", async () => {
  const page = await readFile(new URL("../app/people/[id]/page.tsx", import.meta.url), "utf8");
  assert.match(page, /person\.profile\.sections\.map/);
  assert.match(page, /section\.status/);
  assert.match(page, /entry\.epistemic_status/);
  assert.match(page, /entry\.evidence_ids/);
  assert.match(page, /entry\.source_ids/);
  assert.match(page, /UNKNOWN/);
  assert.match(page, /Evidence & audit/);
});

test("UI does not implement publication decisions", async () => {
  const files = await Promise.all(
    ["../app/page.tsx", "../app/people/[id]/page.tsx"].map((path) =>
      readFile(new URL(path, import.meta.url), "utf8"),
    ),
  );
  assert.ok(files.every((body) => !body.includes("validate_claim_publication")));
});

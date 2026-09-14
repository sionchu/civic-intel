import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

test("profile renders section coverage and evidence traceability", async () => {
  const page = await readFile(new URL("../app/people/[id]/page.tsx", import.meta.url), "utf8");
  assert.match(page, /profile\.sections\.map/);
  assert.match(page, /section\.status/);
  assert.match(page, /entry\.epistemic_status/);
  assert.match(page, /entry\.evidence/);
  assert.match(page, /entry\.source_ids/);
  assert.match(page, /DERIVED · CHANGE/);
  assert.match(page, /changeDetails\.earlier/);
  assert.match(page, /method_version/);
  assert.match(page, /correction_semantics/);
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

test("public roster keeps name filtering client-side and identity-scoped", async () => {
  const page = await readFile(new URL("../app/page.tsx", import.meta.url), "utf8");
  const roster = await readFile(new URL("../app/components/roster-grid.tsx", import.meta.url), "utf8");
  const layout = await readFile(new URL("../app/layout.tsx", import.meta.url), "utf8");
  assert.match(page, /<RosterGrid people=\{people\} \/>/);
  assert.match(roster, /type=\"search\"/);
  assert.match(roster, /canonical_name/);
  assert.match(roster, /href=\{`\/people\/\$\{person\.id\}`\}/);
  assert.match(layout, /lang=\"ko\"/);
  assert.match(layout, /skip-link/);
});

test("UI exposes explicit provenance and a read-only review surface", async () => {
  const profile = await readFile(new URL("../app/people/[id]/page.tsx", import.meta.url), "utf8");
  const review = await readFile(new URL("../app/admin/review/page.tsx", import.meta.url), "utf8");
  const layout = await readFile(new URL("../app/layout.tsx", import.meta.url), "utf8");
  assert.match(profile, /SOURCE CONFLICT/);
  assert.match(profile, /trace\.stance/);
  assert.match(profile, /snapshot_id/);
  assert.match(profile, /policy_summary/);
  assert.match(review, /getReviewReport/);
  assert.match(review, /item\.action/);
  assert.match(review, /item\.status/);
  assert.doesNotMatch(review, /<button|onClick/);
  assert.doesNotMatch(layout, /admin\/review/);
});

test("organization page consumes the existing direct-ID evidence contract", async () => {
  const page = await readFile(new URL("../app/organizations/[id]/page.tsx", import.meta.url), "utf8");
  const data = await readFile(new URL("../app/data.ts", import.meta.url), "utf8");
  assert.match(page, /getOrganization\(id\)/);
  assert.match(page, /getOrganizationMoney\(id\)/);
  assert.match(page, /Published claims/);
  assert.match(page, /DERIVED · MONEY/);
  assert.match(page, /moneyResult\.error/);
  assert.match(page, /ReadState/);
  assert.match(page, /SourceSnapshot/);
  assert.match(page, /FeederObservation/);
  assert.match(page, /policy_summary/);
  assert.match(data, /organizations\/\$\{id\}/);
  assert.match(data, /earlier_fiscal_year/);
});

test("public reads preserve distinct error states without blanket fallbacks", async () => {
  const data = await readFile(new URL("../app/data.ts", import.meta.url), "utf8");
  const state = await readFile(new URL("../app/components/read-state.tsx", import.meta.url), "utf8");
  const types = await readFile(new URL("../app/types.ts", import.meta.url), "utf8");
  assert.match(data, /CIVIC_API_URL/);
  assert.match(data, /ACCESS_DENIED/);
  assert.match(data, /SERVICE_UNAVAILABLE/);
  assert.doesNotMatch(data, /fallback/);
  assert.match(types, /INSUFFICIENT_ELIGIBLE_INPUTS/);
  assert.match(types, /SOURCE_VERSION_CONFLICT/);
  assert.match(state, /ACCESS_DENIED/);
  assert.match(state, /자료 없음이나 UNKNOWN으로 처리하지 않았습니다/);
});

test("organization page does not add binding or organization enumeration controls", async () => {
  const page = await readFile(new URL("../app/organizations/[id]/page.tsx", import.meta.url), "utf8");
  const layout = await readFile(new URL("../app/layout.tsx", import.meta.url), "utf8");
  assert.doesNotMatch(page, /<button|onClick|create|bind|enumerate/i);
  assert.doesNotMatch(layout, /organizations/);
});

test("UI stays within the directory scope", async () => {
  const files = await Promise.all(
    ["../app/page.tsx", "../app/people/[id]/page.tsx", "../app/organizations/[id]/page.tsx", "../app/admin/review/page.tsx"].map((path) =>
      readFile(new URL(path, import.meta.url), "utf8"),
    ),
  );
  const unsupportedSurface = /confidence|faction|influence|probability|OpenWatch|roll-call|asset dashboard/i;
  assert.ok(files.every((body) => !unsupportedSurface.test(body)));
});

import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const read = (path) => readFile(new URL(path, import.meta.url), "utf8");

test("Gukgam witnesses component is a server component with source-listed flat rows", async () => {
  const component = await read("../app/components/gukgam-witnesses.tsx");
  assert.doesNotMatch(component, /^\s*"use client"/m);
  assert.match(component, /getGukgamWitnesses\(\)/);
  assert.match(component, /item\.source_url/);
  assert.match(component, /item\.affiliation_title/);
  assert.match(component, /위법 판단이 아닙니다/);
  assert.match(component, /아직 공개된 명단이 없습니다/);
});

test("Gukgam witness names never link to Person pages", async () => {
  const component = await read("../app/components/gukgam-witnesses.tsx");
  assert.doesNotMatch(component, /next\/link|\/people\/|person_id/);
});

test("Gukgam witness data helper targets the published-only route", async () => {
  const data = await read("../app/data.ts");
  assert.match(data, /getJson\("\/gukgam\/2026\/witnesses"\)/);
  const types = await read("../app/types.ts");
  assert.match(types, /SOURCE_LISTED_TEXT_NO_PERSON_LINK/);
});

test("Gukgam witness component labels owner-supplied copies and HWP table locators", async () => {
  const component = await read("../app/components/gukgam-witnesses.tsx");
  assert.match(component, /item\.provenance_label/);
  assert.match(component, /item\.attendance_date_text/);
  assert.match(component, /item\.page_number === null/);
  assert.match(component, /item\.source_url \? \(/);
  const types = await read("../app/types.ts");
  assert.match(types, /page_number: number \| null/);
  assert.match(types, /source_url: string \| null/);
  assert.match(types, /"OWNER_SUPPLIED_COPY"/);
});

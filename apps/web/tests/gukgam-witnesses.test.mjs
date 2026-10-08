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

test("Gukgam witness names link to a Person only through a reviewed published link", async () => {
  const component = await read("../app/components/gukgam-witnesses.tsx");
  // The only Person link is the API's reviewed linked_person; never a name lookup or person_id.
  assert.match(component, /item\.linked_person \? \(/);
  assert.equal(component.match(/\/people\//g)?.length, 1);
  assert.doesNotMatch(component, /person_id|getPeople|canonical_name/);
  assert.match(component, /사람이 검토해 공개한 행만/);
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

test("Gukgam witness lists start collapsed per committee and stay reachable by deep link", async () => {
  const [component, opener, css] = await Promise.all([
    read("../app/components/gukgam-witnesses.tsx"),
    read("../app/components/hash-disclosure.tsx"),
    read("../app/components/gukgam-witnesses.css"),
  ]);
  // Every row is still rendered (no pagination or ranking); each committee is a native disclosure.
  assert.match(component, /<details className="gukgam-witnesses-committee" key=\{committee\}>/);
  assert.match(component, /<summary>\s*<h3>\{committee\}<\/h3>\s*<span>\{committeeSummary\(committeeItems\)\}<\/span>/);
  assert.doesNotMatch(component, /<details[^>]*\bopen\b/);
  assert.doesNotMatch(component, /\.slice\(|page=|sort\(\(a, b\) => b\./);
  // The closed summary still states counts and source state.
  assert.match(component, /`\$\{category\} \$\{count\}명`/);
  assert.match(component, /`아직 공식 발표 아님 \$\{supplied\}명`/);
  // #witness-{claim_id} opens its closed ancestors; the opener is the only client code involved.
  assert.match(component, /<HashDisclosure prefix="witness-" \/>/);
  assert.match(opener, /^"use client";/);
  assert.match(opener, /node instanceof HTMLDetailsElement\) node\.open = true/);
  assert.match(opener, /addEventListener\("hashchange", reveal\)/);
  assert.match(opener, /return null;/);
  // A malformed hash (e.g. #%E0) is ignored instead of throwing inside the effect.
  assert.match(opener, /try \{\s*id = decodeURIComponent\(window\.location\.hash\.slice\(1\)\);\s*\} catch \{\s*return;/);
  // Row-level labels survive the collapse; the summary counts only known official channels.
  assert.match(component, /위법 판단이 아닙니다/);
  assert.match(component, /OWNER_SUPPLIED_COPY" \? " · 아직 공식 발표 아님"/);
  assert.match(component, /"OFFICIAL_SITE" \|\| item\.acquisition_channel === "OFFICIAL_MINUTES"/);
  assert.match(css, /\.gukgam-witnesses-category li:target/);
  assert.match(css, /summary:focus-visible/);
});

test("Gukgam schedule rows keep evidence one interaction away with audit IDs behind a disclosure", async () => {
  const page = await read("../app/gukgam/2026/page.tsx");
  assert.match(page, /이 일정의 근거 보기/);
  assert.match(page, /href=\{`\/organizations\/\$\{item\.organization\.id\}#claim-\$\{item\.claim_id\}`\}/);
  assert.match(page, /<details className="audit-details">\s*<summary>Claim·Evidence 확인 경로<\/summary>/);
  assert.match(page, /공식 계획서 · \{item\.source_published_date\} 공개 · \{item\.section\} · p\.\{item\.page_number\}/);
  // The long committee list moves into a disclosure; it is not dropped.
  assert.match(page, /<summary>포함 위원회 \{coveredCommittees\.length\}곳<\/summary>/);
  assert.match(page, /coveredCommittees\.join\(" · "\)/);
});

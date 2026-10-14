import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import vm from "node:vm";
import { webcrypto } from "node:crypto";
import ts from "typescript";
import { createRequire } from "node:module";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";

const compiled = ts.transpileModule(readFileSync(new URL("../app/compare/votes/comparison.ts", import.meta.url), "utf8"), { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } }).outputText;
const exports = {};
vm.runInNewContext(compiled, { exports, TextEncoder, crypto: webcrypto, Date, Map, Set, Error });
const { compareVotes, calendarDate, evidenceHref } = exports;
const vote = (person, bill, choice, overrides = {}) => ({ id: `${person}-${bill}`, person_id: person, predicate: "ASSEMBLY_PLENARY_VOTE", object_text: `검증용 의안 ${bill}`, publication_status: "PUBLISHED", epistemic_status: "CLAIM", asserted_as_true: false, qualifiers: { source_contract: "assembly_plenary_roll_call_vote", assembly_age: "22", bill_id: bill, vote_datetime: "2026-10-01T14:00:00", vote_value_published: choice }, evidence: [{ id: "e", source_id: "s", stance: "SUPPORT" }], source_ids: ["s"], ...overrides });
const person = (id, claims) => ({ id, canonical_name: `검증용 ${id}`, identity_status: "RESOLVED", claims });
const run = (a, b) => compareVotes(person("a", a), person("b", b), "2026-10-01", "2026-10-02");

test("common exact vote events preserve abstention/nonparticipation and both evidence paths", async () => {
  const r = await run([vote("a", "1", "찬성"), vote("a", "2", "불참"), vote("a", "3", "찬성")], [vote("b", "1", "반대"), vote("b", "2", "기권")]);
  assert.equal(r.common, 2); assert.equal(r.leftOnly, 1); assert.equal(r.rightOnly, 0);
  assert.equal(r.rows.find((x) => x.left.billId === "2").left.choice, "불참");
  assert.equal(r.rows.find((x) => x.left.billId === "2").right.choice, "기권");
  assert.match(evidenceHref("a", r.rows[0].left), /claim=a-1#claim-a-1/);
});

test("period, identity, nonpublication, UNKNOWN, refutation and duplicate keys fail closed", async () => {
  const base = vote("a", "1", "찬성");
  for (const changed of [{ person_id: "other" }, { publication_status: "DRAFT" }, { epistemic_status: "UNKNOWN" }, { source_conflict: true }, { evidence: [...base.evidence, { id: "r", source_id: "s", stance: "REFUTE" }] }, { evidence: [] }]) {
    assert.equal((await run([{ ...base, ...changed }], [vote("b", "1", "찬성")])).common, 0);
  }
  const duplicated = await run([base, { ...base, id: "duplicate" }], [vote("b", "1", "찬성")]);
  assert.equal(duplicated.common, 0); assert.equal(duplicated.leftExcluded.duplicate, 2);
  const disputedDuplicate = await run([base, { ...base, id: "disputed", source_conflict: true }], [vote("b", "1", "찬성")]);
  assert.equal(disputedDuplicate.common, 0);
  assert.equal(disputedDuplicate.leftExcluded.conflict, 1);
  assert.equal(disputedDuplicate.leftExcluded.duplicate, 1);
  await assert.rejects(compareVotes(person("a", []), person("a", []), "2026-10-01", "2026-10-02"));
  await assert.rejects(compareVotes(person("a", []), person("b", []), "2026-02-30", "2026-10-02"));
  assert.equal(calendarDate("2026-02-30"), false);
});

test("same bill with different term/event never joins and absent records never become no-votes", async () => {
  const left = vote("a", "1", "찬성"), right = vote("b", "1", "찬성");
  for (const qualifiers of [{ ...right.qualifiers, assembly_age: "21" }, { ...right.qualifiers, vote_datetime: "2026-10-01T15:00:00" }, { ...right.qualifiers, assembly_age: "" }]) {
    assert.equal((await run([left], [{ ...right, qualifiers }])).common, 0);
  }
  const empty = await run([left], []);
  assert.equal(empty.common, 0); assert.equal(empty.leftOnly, 1);
});

test("input pin is stable under claim order and changes for corrected evidence", async () => {
  const a = [vote("a", "1", "찬성"), vote("a", "2", "기권")], b = [vote("b", "1", "반대")];
  const first = await run(a, b), reordered = await run([...a].reverse(), b);
  assert.equal(first.version, reordered.version);
  assert.notEqual(first.version, (await run([{ ...a[0], source_ids: ["s", "corrected"] }, a[1]], b)).version);
});

test("server comparison page bounds rows and renders drift, invalid and empty states distinctly", async () => {
  const require = createRequire(import.meta.url);
  const a = person("a", Array.from({ length: 45 }, (_, n) => vote("a", String(n), "찬성")));
  const b = person("b", Array.from({ length: 45 }, (_, n) => vote("b", String(n), "반대")));
  const pageExports = {};
  const output = ts.transpileModule(readFileSync(new URL("../app/compare/votes/page.tsx", import.meta.url), "utf8"), { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.ReactJSX } }).outputText;
  vm.runInNewContext(output, { exports: pageExports, URLSearchParams, Error, require: (id) => {
    if (id === "next/link") return { default: ({ children, ...props }) => createElement("a", props, children) };
    if (id === "../../data") return { getPeople: async () => ({ state: "success", data: [a, b] }), getPerson: async (id) => ({ state: "success", data: id === "a" ? a : b }) };
    if (id === "../../components/read-state") return { default: ({ error }) => createElement("p", { role: "alert" }, `${error.code}: ${error.message}`) };
    if (id === "./comparison") return exports;
    return require(id);
  } });
  const params = { left: "a", right: "b", start: "2026-10-01", end: "2026-10-02" };
  const render = async (changes) => renderToStaticMarkup(await pageExports.default({ searchParams: Promise.resolve({ ...params, ...changes }) }));
  const first = await render({});
  assert.equal((first.match(/class="vote-row"/g) ?? []).length, 20);
  assert.match(first, /공통 비교 대상 45건/);
  assert.match(first, /다음 20건/);
  assert.match(first, /\?claim=/);
  const finalPage = await render({ page: "3" });
  assert.equal((finalPage.match(/class="vote-row"/g) ?? []).length, 5);
  const drift = await render({ v: "stale" });
  assert.match(drift, /SOURCE_VERSION_CONFLICT/); assert.doesNotMatch(drift, /class="vote-row"/);
  assert.match(await render({ start: "2026-10-03", end: "2026-10-01" }), /올바르게/);
  assert.match(await render({ start: "2026-09-01", end: "2026-09-02" }), /공통 표결이 없습니다/);
  assert.match(await render({ page: "999" }), /범위를 벗어났습니다/);
});

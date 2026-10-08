import assert from "node:assert/strict";
import { existsSync, readFileSync, writeFileSync } from "node:fs";
import { createRequire } from "node:module";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import test from "node:test";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import ts from "typescript";

function loadPresentation(path, overrides = {}) {
  const cache = new Map();
  function load(file) {
    if (cache.has(file)) return cache.get(file).exports;
    const compiledModule = { exports: {} };
    cache.set(file, compiledModule);
    const nativeRequire = createRequire(file);
    const requireLocal = (specifier) => {
      if (Object.hasOwn(overrides, specifier)) return overrides[specifier];
      if (specifier.startsWith(".")) {
        const target = resolve(dirname(file), specifier);
        const typed = [target, `${target}.tsx`, `${target}.ts`].find((candidate) => /\.tsx?$/.test(candidate) && existsSync(candidate));
        if (typed) return load(typed);
      }
      return nativeRequire(specifier);
    };
    const { outputText } = ts.transpileModule(readFileSync(file, "utf8"), {
      compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX, target: ts.ScriptTarget.ES2022, esModuleInterop: true },
      fileName: file,
    });
    new Function("require", "module", "exports", outputText)(requireLocal, compiledModule, compiledModule.exports);
    return compiledModule.exports;
  }
  return load(fileURLToPath(new URL(path, import.meta.url)));
}

const { careerPeriodText } = loadPresentation("../app/career-period.ts");
const { officialVoteRecords, selectVoteRecords, recentOfficialActivity } = loadPresentation("../app/person-activity.ts");
const { default: PersonVoteExplorer } = loadPresentation("../app/components/person-vote-explorer.tsx");
const activityPerson = { id: "person-a", identity_status: "RESOLVED" };
const period = { start: "2024-01-01", end: "2024-05-01", start_precision: "MONTH", end_precision: "MONTH" };
const success = (data) => ({ state: "success", data });
const source = (id) => ({ id, title: `공개 출처 ${id}`, url: "https://example.org/public", publisher: "검증용 기관", published_at: null, terms_checked_at: null, source_class: "OFFICIAL", license: null, policy_summary: { collection: "PERMITTED", metadata_storage: "PERMITTED", fulltext_storage: "NOT_PERMITTED", excerpt_display: "NOT_PERMITTED" } });
const claim = (id, predicate) => ({ id, person_id: "person-a", subject: "검증용 인물", predicate, object_text: "검증용 기재", proposition: "검증용 경력 기재", epistemic_status: "CLAIM", publication_status: "PUBLISHED", asserted_as_true: false, qualifiers: predicate === "ASSEMBLY_BIOGRAPHY_CAREER" ? { period_start: "2024-01-01", period_end: "2024-05-01", period_start_precision: "MONTH", period_end_precision: "MONTH" } : {}, evidence: [{ id: `e-${id}`, source_id: "source-a", stance: "SUPPORT" }], source_ids: ["source-a"], recorded_at: "2026-10-08T00:00:00Z" });
const via = { key: "via-a", kind: "COMMITTEE", label: "검증용 위원회", organization_id: null };
const relationships = { person: { id: "person-a", name: "검증용 인물" }, ruleset_version: "fixture-v1", groups: [{ via, layer: "POLITICAL", relation_count: 4, relations: [{ relation_id: "relation-a", relation_type: "SAME_PARLIAMENTARY_COMMITTEE", status: "DERIVED", rule_id: "same-committee", rule_version: "1", subject_person_id: "person-a", object_person_id: "person-b", counterpart: { id: "person-b", name: "비교 인물" }, via, temporal: { overlap: "UNKNOWN", basis: "UNKNOWN", subject_period: { start: null, end: null, as_of: null, precision: "UNKNOWN" }, object_period: { start: null, end: null, as_of: "2026-10-01", precision: "DAY" } }, source_claim_ids: ["affiliation-a", "affiliation-b"], evidence_ids: ["ev-a", "ev-b"], source_ids: ["source-a", "source-b"], source_conflict: true, interpretation_note: "같은 위원회 기재이며 친분을 뜻하지 않습니다." }] }], relation_count: 4, limitations: ["공개된 입력만 비교합니다."] };
const entries = [{ id: "entry-a", kind: "CLAIM", title: "검증용 경력 기재", claim_id: "career-a", source_ids: ["source-a"], evidence_ids: ["e-career-a"], epistemic_status: "CLAIM", asserted_as_true: false, date: null, details: { career_semantics: "SOURCE_ATTRIBUTED_BIOGRAPHY", career_period: period } }];
async function renderPerson(relationshipResult = success(relationships), extraClaims = [], portrait = null, extraSections = []) {
  const requestedSources = [];
  const { default: Page } = loadPresentation("../app/people/[id]/page.tsx", {
    "../../data": {
      getPerson: async () => success({ id: "person-a", canonical_name: "검증용 인물", identity_status: "RESOLVED", claims: [claim("career-a", "ASSEMBLY_BIOGRAPHY_CAREER"), claim("affiliation-a", "ASSEMBLY_COMMITTEE_MEMBERSHIP"), ...extraClaims], profile: { sections: [{ id: "career_timeline", label: "경력", status: "PARTIAL", entries }, { id: "summary", label: "요약", status: "AVAILABLE", entries: [{ ...entries[0], id: "summary-a" }] }, { id: "money", label: "재산", status: "UNKNOWN", reason: "SOURCE_NOT_COLLECTED", entries: [] }, ...extraSections] } }),
      getPersonOntology: async () => success({ edges: [], nodes: [] }),
      getPersonRelationships: async () => relationshipResult,
      getGukgamCommittees: async () => success({ committees: [] }),
      getGukgamTargets: async () => success({ items: [] }),
      getSource: async (id) => { requestedSources.push(id); return success(source(id)); },
    },
    "../../portrait": { getReviewedPortrait: async () => portrait },
  });
  return { html: renderToStaticMarkup(await Page({ params: Promise.resolve({ id: "person-a" }) })), requestedSources };
}

test("declared assets preserve signed/zero thousand-KRW amounts, unknowns and the Claim/Source path", async () => {
  const assetClaim = { ...claim("asset-a", "ASSEMBLY_DECLARED_ASSET_TOTAL"), epistemic_status: "UNKNOWN",
    object_text: "0천원", proposition: "검증용 인물의 공개 재산신고 총계는 0천원이다.",
    evidence: [{ id: "e-asset-a", source_id: "source-a", stance: "SUPPORT", snapshot_id: "synthetic-snapshot", feeder_observation_id: "synthetic-observation" }] };
  const assetEntry = { ...entries[0], id: "asset-entry", claim_id: assetClaim.id, epistemic_status: "UNKNOWN", title: "공개 재산신고 총계", details: {
    source_contract: "peti_public_declared_total_metadata_v1", amount_thousand_krw: 0,
    amount_unit: "THOUSAND_KRW", value_semantics: "DECLARED_VALUE_NOT_MARKET_WEALTH",
    declared_totals_scope: "PRINTED_PUBLIC_DISCLOSURE_TOTAL_NOT_SELF_ONLY", publication_date: "2026-10-09",
    registration_date: "2026-09-01", report_type: "UNKNOWN",
  } };
  const section = (entry) => ({ id: "public_declared_assets", label: "신고재산", status: "AVAILABLE", entries: [entry] });
  const zero = await renderPerson(success(relationships), [assetClaim], null, [section(assetEntry)]);
  assert.match(zero.html, /0천원/); assert.match(zero.html, /UNKNOWN · 원자료에서 확인되지 않음/);
  assert.match(zero.html, /본인만의 재산, 현재 시장가치 또는 순자산으로 해석하지 않습니다/);
  assert.match(zero.html, /<dt>등록일<\/dt><dd>2026-09-01/);
  assert.equal((zero.html.match(/id="claim-asset-a"/g) ?? []).length, 1);
  assert.match(zero.html, /href="#source-source-a"/);
  assert.equal(assetClaim.epistemic_status, "UNKNOWN");
  const signed = await renderPerson(success(relationships), [{ ...assetClaim, object_text: "-1,234,567천원", proposition: "검증용 인물의 공개 재산신고 총계는 -1,234,567천원이다." }], null, [section({ ...assetEntry, details: { ...assetEntry.details, amount_thousand_krw: -1234567 } })]);
  assert.match(signed.html, /-1,234,567천원/);
  const invalid = await renderPerson(success(relationships), [assetClaim], null, [section({ ...assetEntry, details: { ...assetEntry.details, amount_thousand_krw: null } })]);
  assert.match(invalid.html, /금액·단위 확인 불가/); assert.doesNotMatch(invalid.html, /공개 신고 총계<\/dt><dd>0천원/);
  const empty = await renderPerson(success(relationships), [], null, [{ ...section(assetEntry), status: "UNKNOWN", reason: "SOURCE_NOT_COLLECTED", entries: [] }]);
  assert.match(empty.html, /재산이 없거나 0원이라는 뜻은 아닙니다/);
  if (process.env.CIVIC_QA_ASSET_HTML === "1") {
    const css = readFileSync(new URL("../app/styles.css", import.meta.url), "utf8");
    writeFileSync(new URL("../../../dist/full-goal-evidence/followup/browser/asset-ui-synthetic.html", import.meta.url), `<!doctype html><html lang="ko"><head><meta charset="utf-8"><style>${css}</style></head><body><p>LOCAL_SYNTHETIC_RENDER_FIXTURE · 실제 인물·공개 재산 데이터 아님</p>${signed.html}</body></html>`);
  }
});

test("portrait markup preserves each reviewed original's intrinsic dimensions", async () => {
  for (const [width, height] of [[400, 534], [4032, 2268]]) {
    const { html } = await renderPerson(success(relationships), [], {
      local_path: "/portraits/synthetic.jpg", source_width: width, source_height: height,
      source_page_url: "https://example.org/source", creator: "Synthetic fixture",
      license_url: "https://example.org/license", license: "SYNTHETIC_TEST_ONLY",
    });
    assert.match(html, new RegExp(`<img[^>]+width="${width}"[^>]+height="${height}"`));
  }
  const css = readFileSync(new URL("../app/styles.css", import.meta.url), "utf8");
  const rule = css.match(/\.profile-portrait img\s*\{([^}]+)\}/)[1];
  assert.match(rule, /height:\s*auto/);
  assert.doesNotMatch(rule, /aspect-ratio/);
});

function bill(id, date) {
  return { ...claim(id, "ASSEMBLY_BILL_PARTICIPATION"), object_text: `공식 의안 ${id}`, qualifiers: { source_contract: "assembly_term_bill_participation", participation_role: "CO_PROPOSER", proposed_date: date } };
}

function vote(id, overrides = {}) {
  return { ...claim(id, "ASSEMBLY_PLENARY_VOTE"), object_text: `기후 법안 ${id}`,
    qualifiers: { source_contract: "assembly_plenary_roll_call_vote", bill_id: `bill-${id}`,
      vote_datetime: "2026-10-02T12:00:00+09:00", vote_value_published: "찬성", committee: "원자료 위원회", ...overrides } };
}

test("vote retrieval uses exact source committees and titles and preserves unresolved fields and choices", () => {
  const inputs = [vote("yes"), vote("no", { vote_value_published: "반대" }),
    vote("abstain", { vote_value_published: "기권" }),
    { ...vote("absent", { vote_value_published: "불참", committee: "", vote_datetime: "2026-02-30T12:00:00" }), epistemic_status: "UNKNOWN" },
    { ...vote("different"), object_text: "복지 법안", qualifiers: { ...vote("different").qualifiers, committee: "보건 위원회" } },
    { ...vote("wrong-person"), person_id: "person-b" },
    { ...vote("draft"), publication_status: "DRAFT" },
    { ...vote("cross-claim"), evidence: [{ claim_id: "other", source_id: "source-a", stance: "SUPPORT" }] },
    vote("bad-contract", { source_contract: "other" }), vote("no-id", { bill_id: "" }),
  ];
  const before = JSON.stringify(inputs);
  const rows = officialVoteRecords(activityPerson, inputs);
  assert.equal(rows.length, 5);
  assert.equal(selectVoteRecords(rows, "기후", "보건 위원회").length, 0);
  assert.equal(selectVoteRecords(rows, " 복지 ", "ALL")[0].title, "복지 법안");
  assert.equal(selectVoteRecords(rows, "", "원자료 위원회").length, 3);
  const absent = selectVoteRecords(rows, "", "UNKNOWN")[0];
  assert.equal(absent.choice, "불참"); assert.equal(absent.status, "UNKNOWN"); assert.equal(absent.date, null);
  assert.deepEqual(new Set(rows.map((row) => row.choice)), new Set(["찬성", "반대", "기권", "불참"]));
  assert.equal(JSON.stringify(inputs), before);
  assert.deepEqual(officialVoteRecords({ ...activityPerson, identity_status: "REVIEW_REQUIRED" }, inputs), []);
});

test("vote panel bounds initial rows without duplicating Claim anchors and discloses coverage", async () => {
  const inputs = Array.from({ length: 25 }, (_, i) => vote(String(i)));
  const rows = officialVoteRecords(activityPerson, inputs);
  const panel = renderToStaticMarkup(createElement(PersonVoteExplorer, { records: rows }));
  assert.equal((panel.match(/<li class="vote-row"/g) ?? []).length, 20);
  assert.match(panel, /표결 기록 더 보기/); assert.match(panel, /25건/);
  assert.match(panel, /DERIVED/); assert.match(panel, /소관위원회 미기재 \(0건\)/);
  assert.doesNotMatch(panel, /id="claim-/);
  const { html } = await renderPerson(success(relationships), inputs);
  for (const input of inputs) assert.equal((html.match(new RegExp(`id="claim-${input.id}"`, "g")) ?? []).length, 1);
  const empty = renderToStaticMarkup(createElement(PersonVoteExplorer, { records: [] }));
  assert.match(empty, /미수집·미공개 기록의 수는 알 수 없습니다/);
});

test("vote panel more action reveals remaining records and changing the query resets its window", () => {
  const state = []; let cursor = 0;
  const { default: Explorer } = loadPresentation("../app/components/person-vote-explorer.tsx", {
    react: { useState: (initial) => { const index = cursor++; if (!(index in state)) state[index] = initial;
      return [state[index], (value) => { state[index] = value; }]; } },
  });
  const records = officialVoteRecords(activityPerson, Array.from({ length: 25 }, (_, i) => vote(String(i))));
  const draw = () => { cursor = 0; return Explorer({ records }); };
  const find = (node, predicate) => {
    if (!node || typeof node !== "object") return null;
    if (predicate(node)) return node;
    for (const child of [node.props?.children].flat(Infinity)) { const result = find(child, predicate); if (result) return result; }
    return null;
  };
  let tree = draw();
  find(tree, (node) => node.type === "button").props.onClick();
  tree = draw();
  assert.equal((renderToStaticMarkup(tree).match(/<li class="vote-row"/g) ?? []).length, 25);
  assert.equal(find(tree, (node) => node.type === "button"), null);
  find(tree, (node) => node.type === "input").props.onChange({ target: { value: "기후" } });
  tree = draw();
  assert.equal((renderToStaticMarkup(tree).match(/<li class="vote-row"/g) ?? []).length, 20);
});

test("recent official activity uses actual event dates and excludes wrong identity, contract and unsupported records", () => {
  const missing = bill("undated", undefined);
  const invalid = bill("invalid-day", "2026-02-30");
  const vote = { ...claim("vote", "ASSEMBLY_PLENARY_VOTE"), epistemic_status: "UNKNOWN", qualifiers: { source_contract: "assembly_plenary_roll_call_vote", vote_datetime: "2026-10-01T15:00:00+09:00", vote_value_published: "반대" } };
  const inputs = [bill("older", "2026-09-01"), bill("newer", "2026-09-20"), missing, invalid, vote,
    { ...bill("wrong-person", "2026-10-05"), person_id: "person-b" },
    { ...bill("unpublished", "2026-10-05"), publication_status: "DRAFT" },
    { ...bill("unresolved", "2026-10-05"), epistemic_status: "ENTITY_UNRESOLVED" },
    { ...bill("no-support", "2026-10-05"), evidence: [{ source_id: "source-a", stance: "REFUTE" }] },
    { ...bill("cross-claim", "2026-10-05"), evidence: [{ claim_id: "another-claim", source_id: "source-a", stance: "SUPPORT" }] },
    { ...bill("wrong-contract", "2026-10-05"), qualifiers: { source_contract: "other", proposed_date: "2026-10-05" } },
  ];
  const before = JSON.stringify(inputs);
  const result = recentOfficialActivity(activityPerson, inputs);
  assert.deepEqual(result.items.map((item) => item.claim.id), ["vote", "newer", "older"]);
  assert.equal(result.items[0].claim.epistemic_status, "UNKNOWN");
  assert.equal(result.items[0].action, "본회의 표결 · 반대");
  assert.equal(result.undatedCount, 2);
  assert.equal(result.datedCount, 3);
  assert.equal(JSON.stringify(inputs), before);
  assert.deepEqual(recentOfficialActivity({ ...activityPerson, identity_status: "REVIEW_REQUIRED" }, inputs), { items: [], datedCount: 0, undatedCount: 0 });
});

test("recent activity is bounded while the complete Claim anchors and source paths remain available", async () => {
  const inputs = Array.from({ length: 12 }, (_, index) => bill(`activity-${index}`, `2026-09-${String(index + 1).padStart(2, "0")}`));
  assert.equal(recentOfficialActivity(activityPerson, inputs).items.length, 8);
  const { html } = await renderPerson(success(relationships), inputs);
  assert.match(html, /id="recent-activity"/);
  assert.match(html, /12건 중 최근 8건/);
  assert.match(html, /dateTime="2026-09-12"/);
  assert.match(html, /href="#claim-activity-11"/);
  assert.match(html, /href="#source-source-a"/);
  for (const item of inputs) assert.equal((html.match(new RegExp(`id="claim-${item.id}"`, "g")) ?? []).length, 1);
  assert.doesNotMatch(html, /정치성향|최근 뉴스|발언 기록/);
  const empty = await renderPerson();
  assert.doesNotMatch(empty.html, /id="recent-activity"/);
});

test("career periods retain day/month/year precision and missing dates", () => {
  assert.equal(careerPeriodText(period), "2024년 1월 – 2024년 5월");
  assert.equal(careerPeriodText({ start: "1999-01-01", start_precision: "YEAR" }), "1999년 – 종료 미기재");
  assert.equal(careerPeriodText({ point: "2024-03-12", point_precision: "DAY" }), "2024.03.12");
  assert.equal(careerPeriodText({}), "기간 미기재");
  assert.equal(careerPeriodText({ start: "2024-01-01", start_precision: "UNKNOWN" }), "기간 미기재");
});

test("Person page places career before coverage and closes both relationship source/Claim paths", async () => {
  const { html, requestedSources } = await renderPerson();
  assert.match(html, /2024년 1월 – 2024년 5월/);
  assert.doesNotMatch(html, /2024[.-]01[.-]01|2024[.-]05[.-]01/);
  assert.match(html, /국회 약력 기재/);
  assert.match(html, /class="status PARTIAL"/);
  assert.match(html, /class="status CLAIM"/);
  assert.ok(html.indexOf('id="career"') < html.indexOf("자료 범위와 한계"));
  assert.equal((html.match(/id="claim-career-a"/g) ?? []).length, 1);
  assert.equal((html.match(/id="claim-affiliation-a"/g) ?? []).length, 1);
  assert.match(html, /href="#claim-affiliation-a"/);
  assert.match(html, /href="\/people\/person-b#claim-affiliation-b"/);
  assert.match(html, /id="source-source-b"/);
  assert.deepEqual(requestedSources, ["source-a", "source-b"]);
  assert.match(html, /시간 겹침 미확인/);
  assert.doesNotMatch(html, /표시할 공개 기록이 아직 없습니다/);
  assert.match(html, /SOURCE CONFLICT/);
  assert.match(html, /공개 연결 4건 중 1건/);
  assert.doesNotMatch(html, /공개된 연결이 없습니다|공개 직접 연결 기록이 없습니다/);
  assert.doesNotMatch(html, /재산 0원/);
});

test("relationship outage remains an error instead of an empty connection verdict", async () => {
  const { html } = await renderPerson({ state: "error", error: { code: "SERVICE_UNAVAILABLE", message: "잠시 사용할 수 없습니다.", request_id: null } });
  assert.match(html, /SERVICE_UNAVAILABLE/);
  assert.doesNotMatch(html, /현재 공개 기록에서 표시할 인물 간 연결이 없습니다/);
});

test("relationship empty and unknown time remain explicit without false currentness", () => {
  const { default: View } = loadPresentation("../app/components/person-relationships.tsx");
  const html = renderToStaticMarkup(createElement(View, { data: { ...relationships, groups: [], relation_count: 0 } }));
  assert.match(html, /현재 공개 기록에서 표시할 인물 간 연결이 없습니다/);
  assert.doesNotMatch(html, /영향력 없음|친분 없음|시간 겹침 확인/);
});

test("relationship bounds are labelled as calculation bounds, never source month precision", () => {
  const { default: View } = loadPresentation("../app/components/person-relationships.tsx");
  const data = structuredClone(relationships);
  data.groups[0].relations[0].temporal.subject_period = { start: "2010-05-31", end: "2012-01-01", precision: "MONTH", as_of: null };
  data.groups[0].relations[0].relation_type = "SAME_CAMPAIGN_OVERLAP";
  const html = renderToStaticMarkup(createElement(View, { data }));
  assert.match(html, /비교 경계 2010.05.31 – 2012.01.01/);
  assert.doesNotMatch(html, /2012년 1월/);
  assert.match(html, /선거 캠프 기간 겹침/);
});

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
      getSources: async (ids) => ids.map((id) => { requestedSources.push(id); return success(source(id)); }),
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
  assert.match(zero.html, /0천원/); assert.match(zero.html, /미확인 · 원자료에서 확인되지 않음/);
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
  assert.equal((html.match(/id="claim-vote-/g) ?? []).length, 0);
  assert.equal((html.match(/<li class="vote-row"/g) ?? []).length, 28);
  const empty = renderToStaticMarkup(createElement(PersonVoteExplorer, { records: [] }));
  assert.match(empty, /미수집·미공개 기록의 수는 알 수 없습니다/);
});

test("vote panel more action reveals remaining records and changing the query resets its window", () => {
  const state = []; let cursor = 0;
  const { default: Explorer } = loadPresentation("../app/components/person-vote-explorer.tsx", {
    react: { ...createRequire(import.meta.url)("react"), useContext: () => null, useEffect: () => {}, useState: (initial) => { const index = cursor++; if (!(index in state)) state[index] = initial;
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
  assert.match(html, /출처 충돌/);
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


test("Korean display labels preserve unresolved and evidence semantics without changing contract codes", () => {
  const { statusLabel, sourceClassLabel } = loadPresentation("../app/display-labels.ts");
  assert.equal(statusLabel("UNKNOWN"), "미확인");
  assert.notEqual(statusLabel("UNKNOWN"), statusLabel("SERVICE_UNAVAILABLE"));
  assert.notEqual(statusLabel("CLAIM"), statusLabel("FACT"));
  assert.notEqual(statusLabel("SUPPORT"), statusLabel("REFUTE"));
  assert.equal(sourceClassLabel("official_public_declared_asset_metadata"), "공개 재산신고 자료");
  const { SourceCard } = loadPresentation("../app/components/evidence-panel.tsx");
  const html = renderToStaticMarkup(createElement(SourceCard, { source: source("source-localized") }));
  assert.match(html, /이용 조건 미기재/);
  assert.match(html, /id="source-source-localized"/);
  assert.doesNotMatch(html, /License not specified/);
});


test("evidence localizes known fields, keeps exact quotations and places technical codes in optional audit", () => {
  const { default: EvidencePanel } = loadPresentation("../app/components/evidence-panel.tsx");
  const record = { ...claim("localized", "ASSEMBLY_BILL_PARTICIPATION"), epistemic_status: "UNKNOWN", proposition: "Source quotation stays EXACT", qualifiers: { participation_role: "REPRESENTATIVE_PROPOSER", source_contract: "assembly_term_bill_participation", parser_revision: "REVISION_EXACT", proposed_date: "2026-10-08" } };
  const before = JSON.stringify(record);
  const html = renderToStaticMarkup(createElement(EvidencePanel, { claim: record, sourceById: new Map([["source-a", source("source-a")]]) }));
  const main = html.slice(0, html.indexOf('<details class="audit-details evidence-audit"'));
  assert.match(main, /미확인/); assert.match(main, /대표 발의/); assert.match(main, /Source quotation stays EXACT/);
  assert.doesNotMatch(main, /REPRESENTATIVE_PROPOSER|assembly_term_bill_participation|parser_revision/);
  assert.match(html, /기록 속성 식별값 parser_revision: REVISION_EXACT/);
  assert.match(html, /기록 localized/); assert.match(html, /href="#source-source-a"/);
  assert.equal(JSON.stringify(record), before);
});


test("all vote metadata remains bounded and selected canonical evidence is rendered once", () => {
  const state = []; let cursor = 0;
  const react = createRequire(import.meta.url)("react");
  const { default: Explorer } = loadPresentation("../app/components/person-vote-explorer.tsx", {
    react: { ...react, useContext: () => null, useEffect: () => {}, useState(initial) { const index = cursor++; if (!(index in state)) state[index] = initial; return [state[index], (value) => { state[index] = value; }]; } },
  });
  const claims = Array.from({ length: 1890 }, (_, index) => vote(String(index)));
  const records = officialVoteRecords(activityPerson, claims);
  const props = { records, claims, sources: [source("source-a")], existingClaimIds: [] };
  const render = () => { cursor = 0; return Explorer(props); };
  let tree = render(); let html = renderToStaticMarkup(tree);
  assert.equal((html.match(/<li class="vote-row"/g) ?? []).length, 20);
  assert.doesNotMatch(html, /class="claim evidence-panel"/);
  function find(node) { if (!node || typeof node !== "object") return null; if (node.type === "a" && node.props.href === `#claim-${records[0].claimId}`) return node; for (const child of [node.props?.children].flat(Infinity)) { const result = find(child); if (result) return result; } return null; }
  find(tree).props.onClick(); html = renderToStaticMarkup(render());
  assert.equal((html.match(/class="claim evidence-panel"/g) ?? []).length, 1);
  assert.equal((html.match(new RegExp(`id="claim-${records[0].claimId}"`, "g")) ?? []).length, 1);
  assert.match(html, /href="#source-source-a"/);
  assert.equal(records.length, 1890);
});


test("official press and self-housing sections preserve unknowns and exact evidence paths", async () => {
  const housing = { ...claim("housing-a", "PETI_DECLARED_SELF_HOUSING"), epistemic_status: "UNKNOWN" };
  const press = claim("press-a", "ASSEMBLY_OFFICIAL_PRESS_RECORD");
  const section = (id, label, record, details) => ({ id, label, status: "AVAILABLE", entries: [{ ...entries[0], id: `${id}-entry`, title: label, claim_id: record.id, details }] });
  const { html } = await renderPerson(success(relationships), [housing, press], null, [
    section("public_self_housing", "본인 소유 주택 신고", housing, { source_contract: "peti_public_self_housing_metadata_v1", value_semantics: "DECLARED_OWNERSHIP_NOT_RESIDENCE", housing_status: "UNKNOWN", owned_housing_count: "UNKNOWN", shared_housing_count: "UNKNOWN", self_scope_coverage: "PARTIAL", publication_date: "2026-10-08" }),
    section("official_press_records", "국회 공식 보도자료", press, { source_contract: "national_assembly_press_release_metadata_v1", written_date: "2026-10-08", attribution: "국회사무처", coverage: "REVIEWED_SELECTED_RECORD" }),
  ]);
  assert.match(html, /현재 거주지나 실거주 여부를 뜻하지 않습니다/);
  assert.match(html, /소유 주택 건수<\/dt><dd>미확인/);
  assert.doesNotMatch(html, /소유 주택 건수<\/dt><dd>0/);
  assert.match(html, /개인의 직접 발언이나 언론기사 전체를 뜻하지 않습니다/);
  assert.match(html, /검토된 해당 기록/);
  assert.match(html, /id="claim-housing-a"/); assert.match(html, /id="claim-press-a"/);
  assert.match(html, /href="#source-source-a"/);
  const empty = await renderPerson(success(relationships), [], null, [
    { id: "official_press_records", label: "국회 공식 보도자료", status: "UNKNOWN", reason: "SOURCE_NOT_COLLECTED", note: "공개 보도자료가 연결되지 않았습니다.", entries: [] },
    { id: "public_self_housing", label: "본인 소유 주택 신고", status: "UNKNOWN", reason: "SOURCE_NOT_COLLECTED", note: "주택이 없다는 뜻은 아닙니다.", entries: [] },
  ]);
  assert.match(empty.html, /id="section-official_press_records"/);
  assert.match(empty.html, /id="section-public_self_housing"/);
  assert.match(empty.html, /주택이 없다는 뜻은 아닙니다/);
});


test("vote coverage distinguishes legacy loaded records from a complete eligible set", () => {
  const records = officialVoteRecords(activityPerson, Array.from({ length: 10 }, (_, i) => vote(String(i))));
  const render = (eligibleCount) => renderToStaticMarkup(createElement(PersonVoteExplorer, { records, eligibleCount, inputScope: "PUBLISHED_SOURCE_VALIDATED_SUBJECT_VOTES" }));
  assert.match(render(undefined), /전체가 포함되었는지는 확인되지 않았습니다/);
  assert.match(render(1910), /공개 대상 1,910건과 이 화면의 연결 기록 10건이 일치하지 않습니다/);
  assert.doesNotMatch(render(1910), /모두 연결되었습니다/);
  assert.match(render(10), /10건이 모두 연결되었습니다/);
  assert.doesNotMatch(renderToStaticMarkup(createElement(PersonVoteExplorer, { records, eligibleCount: 10, inputScope: "UNVERIFIED" })), /모두 연결되었습니다/);
  assert.doesNotMatch(render(-1), /모두 연결되었습니다/);
});


test("large source library bounds cards and reveals one exact off-window source without duplicates", () => {
  const state = []; let cursor = 0; const effects = [];
  const react = createRequire(import.meta.url)("react");
  const { default: Library } = loadPresentation("../app/components/source-library.tsx", {
    react: { ...react, useContext: () => null, useEffect: (fn) => effects.push(fn), useState(initial) { const index = cursor++; if (!(index in state)) state[index] = initial; return [state[index], (value) => { state[index] = value; }]; } },
  });
  const sources = Array.from({ length: 1936 }, (_, i) => source(`bounded-${i}`));
  const render = () => { cursor = 0; effects.length = 0; return Library({ sources }); };
  let tree = render(); let html = renderToStaticMarkup(tree);
  assert.equal((html.match(/<article class="source"/g) ?? []).length, 20);
  const oldWindow = globalThis.window, oldDocument = globalThis.document, oldFrame = globalThis.requestAnimationFrame;
  try {
    globalThis.window = { location: { hash: "#source-bounded-1935" }, addEventListener() {}, removeEventListener() {} };
    globalThis.document = { getElementById: () => null, addEventListener() {}, removeEventListener() {} };
    globalThis.requestAnimationFrame = (fn) => fn();
    effects[0](); tree = render(); html = renderToStaticMarkup(tree);
    assert.equal((html.match(/<article class="source"/g) ?? []).length, 21);
    assert.equal((html.match(/id="source-bounded-1935"/g) ?? []).length, 1);
    function button(node) { if (!node || typeof node !== "object") return null; if (node.type === "button") return node; for (const child of [node.props?.children].flat(Infinity)) { const found = button(child); if (found) return found; } return null; }
    button(tree).props.onClick(); html = renderToStaticMarkup(render());
    assert.equal((html.match(/<article class="source"/g) ?? []).length, 41);
    globalThis.window.location.hash = "#source-bounded-0"; effects[0](); html = renderToStaticMarkup(render());
    assert.equal((html.match(/<article class="source"/g) ?? []).length, 40);
    assert.equal((html.match(/id="source-bounded-0"/g) ?? []).length, 1);
  } finally { globalThis.window = oldWindow; globalThis.document = oldDocument; globalThis.requestAnimationFrame = oldFrame; }
});


test("large Claim library preserves source order, bounded cards, search and exact hash access", () => {
  const state = []; let cursor = 0; const effects = [];
  const react = createRequire(import.meta.url)("react");
  const claims = Array.from({ length: 2341 }, (_, i) => ({ ...claim(`bill-${i}`, "ASSEMBLY_BILL_PARTICIPATION"), object_text: `검증법안 ${i} [정확]` }));
  const { default: Library } = loadPresentation("../app/components/person-claim-library.tsx", {
    "./person-evidence-context": { usePersonEvidence: () => ({ claims, sources: [source("source-a")] }) },
    react: { ...react, useEffect: (fn) => effects.push(fn), useState(initial) { const index = cursor++; if (!(index in state)) state[index] = initial; return [state[index], (value) => { state[index] = value; }]; } },
  });
  const ids = [...claims].reverse().map((item) => item.id);
  const draw = () => { cursor = 0; effects.length = 0; return Library({ claimIds: ids, legislative: true }); };
  let tree = draw(); let html = renderToStaticMarkup(tree);
  assert.equal((html.match(/class="claim evidence-panel"/g) ?? []).length, 20);
  assert.ok(html.indexOf('id="claim-bill-2340"') < html.indexOf('id="claim-bill-2339"'));
  assert.match(html, /2,341건/);
  const oldWindow = globalThis.window, oldDocument = globalThis.document;
  try {
    globalThis.window = { location: { hash: "#claim-bill-0" }, addEventListener() {}, removeEventListener() {} };
    globalThis.document = { addEventListener() {}, removeEventListener() {} };
    effects[0](); html = renderToStaticMarkup(draw());
    assert.equal((html.match(/class="claim evidence-panel"/g) ?? []).length, 21);
    assert.equal((html.match(/id="claim-bill-0"/g) ?? []).length, 1);
  } finally { globalThis.window = oldWindow; globalThis.document = oldDocument; }
  function find(node, type) { if (!node || typeof node !== "object") return null; if (node.type === type) return node; for (const child of [node.props?.children].flat(Infinity)) { const found = find(child, type); if (found) return found; } return null; }
  state[2] = null; tree = draw(); find(tree, "button").props.onClick(); html = renderToStaticMarkup(draw());
  assert.equal((html.match(/class="claim evidence-panel"/g) ?? []).length, 40);
  find(draw(), "input").props.onChange({ target: { value: "검증법안 2000 [정확]" } }); html = renderToStaticMarkup(draw());
  assert.equal((html.match(/class="claim evidence-panel"/g) ?? []).length, 1);
  assert.match(html, /id="claim-bill-2000"/); assert.match(html, /href="#source-source-a"/);
});

test("operator dynamic fields localize closed arrays without modifying original identifiers", () => {
 const { fieldDisplayText, FIELD_LABELS, catalogDisplay } = loadPresentation("../app/admin/review/operator-types.ts");
 const values = ["FACT", "UNKNOWN"];
 assert.equal(fieldDisplayText("epistemic_status", values), "확인된 사실 · 미확인");
 assert.deepEqual(values, ["FACT", "UNKNOWN"]);
 assert.equal(fieldDisplayText("node_kind", "PERSON"), "인물");
 for (const [code, label] of Object.entries({ EDUCATIONAL_INSTITUTION: "교육기관", COMPANY: "기업", COMMITTEE: "위원회", HEARING: "청문회", ISSUE: "쟁점" })) {
   assert.equal(fieldDisplayText("node_kind", code), label);
 }
 assert.equal(fieldDisplayText("status", "CANONICAL"), "정본 등록 기록");
 assert.equal(fieldDisplayText("status", "SOURCE_RECORD_NOT_PERSON"), "출처상 기록 · 인물 미연결");
 assert.equal(fieldDisplayText("relation_types", ["WORKED_AT"]), "경력");
 assert.equal(fieldDisplayText("source_ids", ["source-original"]), "source-original");
 assert.equal(FIELD_LABELS.recorded_at, "저장 시각");
 assert.equal(FIELD_LABELS.source_id, "출처 식별자");
 const catalog = { name: "original", source: "source", scope: "scope", mode: "API", maturity: "L3 FULL_ENUMERATION; blocked" };
 assert.equal(catalogDisplay(catalog).mode, "공개 자료 연동");
 assert.match(catalogDisplay(catalog).maturity, /지정 범위 전체 수집 · 제약 있음/);
 assert.equal(catalog.name, "original");
});

test("operator graph inspector and keyboard labels share the canvas closed-kind adapter", () => {
 const { default: View, operatorNodeLabel } = loadPresentation("../app/admin/review/operator-graph.tsx");
 for (const [kind, label] of Object.entries({ EDUCATIONAL_INSTITUTION: "교육기관", COMPANY: "기업", COMMITTEE: "위원회", HEARING: "청문회", ISSUE: "쟁점" })) {
   const record = { id: "node-a", record_id: "record-a", kind, label: "검증 대상", status: "CANONICAL", fields: {} };
   const detail = { record, graph: { center: "node-a", nodes: [record], edges: [], max_depth: 1, max_nodes: 80, truncated: false, semantics: "PUBLIC_CANONICAL_CLAIM_EVIDENCE_RELATIONS" } };
   const html = renderToStaticMarkup(createElement(View, { detail, contextQuery: "" }));
   assert.equal(operatorNodeLabel(kind), label);
   assert.ok(html.split(label).length >= 3, "inspector and keyboard both display the known label");
   assert.doesNotMatch(html.replace(/href="[^"]*"/g, ""), new RegExp(kind));
 }
 assert.equal(operatorNodeLabel("people"), "인물");
 assert.equal(operatorNodeLabel("UNRECOGNIZED"), "대상 유형 미확인");
 const graphSource = readFileSync(new URL("../app/admin/review/operator-graph.tsx", import.meta.url), "utf8");
 assert.match(graphSource, /caption:.*operatorNodeLabel\(node.kind\)/);
});

test("every operator manifest emitted status has a precise Korean presentation", () => {
 const { statusLabel } = loadPresentation("../app/display-labels.ts");
 const producer = readFileSync(new URL("../../api/operator_review.py", import.meta.url), "utf8");
 const codes = [...new Set([...producer.matchAll(/"status": "([A-Z_]+)"/g)].map((match) => match[1]).concat("CURRENT_REVIEW_BLOCKED"))];
 assert.equal(codes.length, 11);
 for (const code of codes) {
   assert.notEqual(statusLabel(code), "상태 미확인", code);
   assert.match(statusLabel(code), /[가-힣]/);
 }
 assert.notEqual(statusLabel("CURRENT_SOURCE_UNAVAILABLE"), statusLabel("CURRENT_SOURCE_CONFLICT"));
 assert.notEqual(statusLabel("CURRENT_REVIEW_DRIFT"), statusLabel("CURRENT_REVIEW_BLOCKED"));
 assert.equal(statusLabel("UNKNOWN"), "미확인");
});

test("money role presentation distinguishes institution heads from unknown scope", () => {
 const { moneyRoleLabel } = loadPresentation("../app/display-labels.ts");
 assert.equal(moneyRoleLabel("INSTITUTION_HEAD"), "기관장");
 assert.equal(moneyRoleLabel("UNKNOWN"), "대상 직위 미확인");
 assert.equal(moneyRoleLabel("UNRECOGNIZED"), "대상 직위 미확인");
 assert.equal(moneyRoleLabel(null), "대상 직위 미확인");
 const page = readFileSync(new URL("../app/organizations/[id]/page.tsx", import.meta.url), "utf8");
 assert.match(page, /moneyRoleLabel\(money.details.organization.role_scope\)/);
});


test("single-text evidence transport preserves canonical Claim and Source values for every consumer", () => {
  const { default: Provider, usePersonEvidence } = loadPresentation("../app/components/person-evidence-context.tsx");
  const original = { claims: [{ ...claim("text-transport", "ASSEMBLY_PLENARY_VOTE"),
    epistemic_status: "UNKNOWN", asserted_as_true: false,
    object_text: "원문 <script> & \"따옴표\" · 한글", resolution_note: "원자료 미확인",
    qualifiers: { source_contract: "assembly_plenary_roll_call_vote", vote_value_published: "불참" },
    evidence: [{ id: "e-original", claim_id: "text-transport", source_id: "source-a", stance: "SUPPORT", excerpt: null, quote_hash: "exact-hash", snapshot_id: "snapshot-a" }],
  }], sources: [source("source-a")] };
  let restored;
  function Consumer() { restored = usePersonEvidence(); return createElement("span", null, restored.claims[0].object_text); }
  const html = renderToStaticMarkup(createElement(Provider, { dataJson: JSON.stringify(original) }, createElement(Consumer)));
  assert.deepEqual(restored, original);
  assert.equal(restored.claims[0].asserted_as_true, false);
  assert.equal(restored.claims[0].evidence[0].quote_hash, "exact-hash");
  assert.match(html, /&lt;script&gt;/);
  assert.doesNotMatch(html, /<script>/);
});

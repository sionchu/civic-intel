import assert from "node:assert/strict";
import { createHash } from "node:crypto";
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
  assert.match(page, /이 프로필의 출처/);
});

test("Portrait Pilot v0 binds one reviewed local asset by canonical Person ID", async () => {
  const manifest = JSON.parse(await readFile(new URL("../public/portraits/manifest.json", import.meta.url), "utf8"));
  const portrait = manifest.portraits.find((item) => item.person_id === "44745d09-398c-46ce-bc38-81f0f606c1d7");
  const loader = await readFile(new URL("../app/portrait.ts", import.meta.url), "utf8");
  const profile = await readFile(new URL("../app/people/[id]/page.tsx", import.meta.url), "utf8");
  const roster = await readFile(new URL("../app/components/roster-grid.tsx", import.meta.url), "utf8");
  assert.ok(portrait);
  assert.equal(portrait.canonical_name, "안철수");
  assert.equal(portrait.review_status, "ELIGIBLE");
  assert.equal(portrait.local_path, "/portraits/44745d09-398c-46ce-bc38-81f0f606c1d7.jpg");
  const bytes = await readFile(new URL(`../public${portrait.local_path}`, import.meta.url));
  assert.equal(bytes.byteLength, 38558);
  assert.equal(createHash("sha1").update(bytes).digest("hex"), "46f16ce27199a761bb472cb0f68a763a3afa16db");
  assert.match(loader, /person\.identity_status !== "RESOLVED"/);
  assert.match(loader, /candidate\.person_id === person\.id/);
  assert.doesNotMatch(loader, /canonical_name\s*===|person\.canonical_name\s*===/);
  assert.match(profile, /getReviewedPortrait\(person\)/);
  assert.match(profile, /src=\{portrait\.local_path\}/);
  assert.match(profile, /alt=\{`\$\{person\.canonical_name\} 공개 사진`\}/);
  assert.match(profile, /Wikimedia Commons/);
  assert.match(profile, /portrait\.license_url/);
  assert.doesNotMatch(profile, /src=\{portrait\.source_original_url\}/);
  assert.doesNotMatch(profile + roster, /profile-stamp|row-avatar/);
  assert.doesNotMatch(roster, /portrait/);
});

test("UI does not implement publication decisions", async () => {
  const files = await Promise.all(
    ["../app/page.tsx", "../app/people/[id]/page.tsx"].map((path) =>
      readFile(new URL(path, import.meta.url), "utf8"),
    ),
  );
  assert.ok(files.every((body) => !body.includes("validate_claim_publication")));
});

test("People is the canonical identity-scoped discovery route", async () => {
  const home = await readFile(new URL("../app/page.tsx", import.meta.url), "utf8");
  const page = await readFile(new URL("../app/people/page.tsx", import.meta.url), "utf8");
  const loading = await readFile(new URL("../app/people/loading.tsx", import.meta.url), "utf8");
  const roster = await readFile(new URL("../app/components/roster-grid.tsx", import.meta.url), "utf8");
  const layout = await readFile(new URL("../app/layout.tsx", import.meta.url), "utf8");
  const profile = await readFile(new URL("../app/people/[id]/page.tsx", import.meta.url), "utf8");
  const notFound = await readFile(new URL("../app/not-found.tsx", import.meta.url), "utf8");
  assert.doesNotMatch(home, /<RosterGrid/);
  assert.match(home, /href="\/people"/);
  assert.match(page, /getPeople/);
  assert.match(page, /<RosterGrid people=\{peopleResult\.data\} initialQuery=\{initialQuery\} witnesses=\{witnesses\} \/>/);
  assert.match(roster, /type=\"search\"/);
  assert.match(roster, /canonical_name/);
  assert.match(roster, /href=\{`\/people\/\$\{person\.id\}`\}/);
  assert.match(roster, /person\.discovery/);
  assert.match(roster, /FACETS/);
  assert.match(roster, /<select/);
  assert.match(roster, /sameNameCounts/);
  assert.match(roster, /key=\{person\.id\}/);
  assert.doesNotMatch(roster, /FeederObservation|normalized/);
  assert.match(loading, /aria-busy="true"/);
  assert.match(profile, /href="\/people"/);
  assert.match(notFound, /href="\/people"/);
  assert.match(layout, /lang=\"ko\"/);
  assert.match(layout, /skip-link/);
  assert.match(layout, /href="\/people"/);
});

test("Visual System v2 keeps Home editorial and People content-first", async () => {
  const home = await readFile(new URL("../app/page.tsx", import.meta.url), "utf8");
  const people = await readFile(new URL("../app/people/page.tsx", import.meta.url), "utf8");
  const roster = await readFile(new URL("../app/components/roster-grid.tsx", import.meta.url), "utf8");
  const styles = await readFile(new URL("../app/styles.css", import.meta.url), "utf8");

  assert.match(home, /국정감사 인물 기록 검색/);
  assert.match(home, /action="\/people"/);
  assert.match(home, /공식 기록으로 확인된 내용만/);
  assert.doesNotMatch(home, /<RosterGrid|hero-panel|signal-strip/);
  assert.match(people, /인물 목록 \{peopleResult\.data\.length\}명/);
  assert.doesNotMatch(people, /profile-stamp/);
  assert.match(roster, /className="roster-row"/);
  assert.match(roster, /className="row-proof"/);
  assert.match(roster, /key=\{person\.id\}/);
  assert.doesNotMatch(roster, /person-card|FeederObservation|normalized/);
  assert.doesNotMatch(styles, /\.hero-panel|\.panel-visual|\.panel-ring|\.panel-dot|\.panel-cross|\.person-card|\.signal-dot/);
});

test("UI exposes explicit provenance and a read-only review surface", async () => {
  const profile = await readFile(new URL("../app/people/[id]/page.tsx", import.meta.url), "utf8")
    + await readFile(new URL("../app/components/evidence-panel.tsx", import.meta.url), "utf8");
  const review = await readFile(new URL("../app/admin/review/page.tsx", import.meta.url), "utf8");
  const throughput = await readFile(new URL("../app/admin/review/gukgam-review-throughput.tsx", import.meta.url), "utf8");
  const actions = await readFile(new URL("../app/admin/review/actions/route.ts", import.meta.url), "utf8");
  const layout = await readFile(new URL("../app/layout.tsx", import.meta.url), "utf8");
  assert.match(profile, /SOURCE CONFLICT/);
  assert.match(profile, /item\.stance|trace\.stance/);
  assert.match(profile, /snapshot_id/);
  assert.match(profile, /policy_summary/);
  assert.match(review, /requireOperator/);
  assert.match(review, /operatorRead/);
  assert.match(review, /claim_commit_authorized/);
  assert.match(review, /materialization_authorized/);
  assert.match(throughput, /item\.match_class/);
  assert.match(throughput, /IDLE_THRESHOLD_MS = 300_000/);
  assert.match(throughput, /APPROVE/);
  assert.match(throughput, /REJECT/);
  assert.match(throughput, /HOLD/);
  assert.match(throughput, /batch_decided: false/);
  assert.match(actions, /gukgam_review_metric/);
  assert.match(review, /CURRENT HUMAN REVIEW/);
  assert.doesNotMatch(throughput, /adminRequest<[^>]+>\("commit"/);
  assert.doesNotMatch(review, /method="post"|--commit/);
  assert.doesNotMatch(layout, /admin\/review/);
});

test("organization page consumes the existing direct-ID evidence contract", async () => {
  const page = await readFile(new URL("../app/organizations/[id]/page.tsx", import.meta.url), "utf8")
    + await readFile(new URL("../app/components/evidence-panel.tsx", import.meta.url), "utf8");
  const data = await readFile(new URL("../app/data.ts", import.meta.url), "utf8");
  assert.match(page, /getOrganization\(id\)/);
  assert.match(page, /getOrganizationMoney\(id\)/);
  assert.match(page, /핵심 기록/);
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

test("organization page stays read-only while the directory is navigable", async () => {
  const page = await readFile(new URL("../app/organizations/[id]/page.tsx", import.meta.url), "utf8");
  const layout = await readFile(new URL("../app/layout.tsx", import.meta.url), "utf8");
  assert.doesNotMatch(page, /<button|onClick|create|bind|enumerate/i);
  assert.match(layout, /organizations/);
});

test("UI stays within the directory scope", async () => {
  const files = await Promise.all(
    ["../app/page.tsx", "../app/people/page.tsx", "../app/people/[id]/page.tsx", "../app/components/roster-grid.tsx", "../app/organizations/page.tsx", "../app/organizations/[id]/page.tsx", "../app/admin/review/page.tsx"].map((path) =>
      readFile(new URL(path, import.meta.url), "utf8"),
    ),
  );
  const unsupportedSurface = /confidence|faction|influence|probability|OpenWatch|roll-call|asset dashboard/i;
  assert.ok(files.every((body) => !unsupportedSurface.test(body)));
});

test("production build prepares a self-contained standalone asset contract", async () => {
  const packageJson = JSON.parse(await readFile(new URL("../package.json", import.meta.url), "utf8"));
  const prepare = await readFile(new URL("../scripts/prepare-standalone.mjs", import.meta.url), "utf8");
  const check = await readFile(new URL("../scripts/check-standalone.mjs", import.meta.url), "utf8");

  assert.match(packageJson.scripts.build, /prepare-standalone\.mjs/);
  assert.match(prepare, /staticTarget/);
  assert.match(prepare, /cpSync/);
  assert.match(check, /Standalone runtime contract verified/);
});


test("Gukgam 2026 is an event surface inside Civic Intel, not a parallel product", async () => {
  const layout = await readFile(new URL("../app/layout.tsx", import.meta.url), "utf8");
  const home = await readFile(new URL("../app/page.tsx", import.meta.url), "utf8");
  const page = await readFile(new URL("../app/gukgam/2026/page.tsx", import.meta.url), "utf8");
  assert.match(layout, /href="\/gukgam\/2026"/);
  assert.match(home, /국감 일정/);
  assert.match(page, /<h1>국감 2026<\/h1>/);
  assert.match(page, /getPeople/);
  assert.match(page, /getOrganizations/);
  assert.match(page, /증인·참고인 명단/);
  assert.doesNotMatch(page, /오늘의 국감|공격 의원|옹호 의원|인맥|친분|배후/);
});

test("Person detail renders a read-only accessible ontology local view", async () => {
  const page = await readFile(new URL("../app/people/[id]/page.tsx", import.meta.url), "utf8");
  const graph = await readFile(new URL("../app/components/ontology-local-graph.tsx", import.meta.url), "utf8");
  const data = await readFile(new URL("../app/data.ts", import.meta.url), "utf8");
  const types = await readFile(new URL("../app/types.ts", import.meta.url), "utf8");
  assert.match(page, /getPersonOntology/);
  assert.match(page, /OntologyLocalGraph/);
  assert.match(page, /공식 기록상 연결/);
  assert.match(data, /\/ontology\/people\/\$\{id\}/);
  assert.match(types, /READ_ONLY_PROJECTION_FROM_CANONICAL_CLAIM_EVIDENCE/);
  assert.match(graph, /aria-label="공식 기록상 연결 목록"/);
  assert.match(graph, /source_conflict/);
  assert.match(graph, /Claim\/Evidence/);
  assert.doesNotMatch(graph, /"use client"|onClick|confidence|score|probability/);
});


test("Gukgam search filters existing public records without creating identity matches", async () => {
  const page = await readFile(new URL("../app/gukgam/2026/page.tsx", import.meta.url), "utf8");
  const search = await readFile(new URL("../app/components/gukgam-search.tsx", import.meta.url), "utf8");
  assert.match(page, /<GukgamSearch/);
  assert.match(page, /canonical_name, discovery/);
  assert.match(search, /type="search"/);
  assert.match(search, /person\.canonical_name/);
  assert.match(search, /facets\?\.committees\?\.value/);
  assert.match(search, /organization\.name/);
  assert.match(search, /href=\{"\/people\/" \+ person\.id\}/);
  assert.match(search, /href=\{"\/organizations\/" \+ organization\.id\}/);
  assert.doesNotMatch(search, /fetch\(|axios|confidence|probability|score|rank/i);
});


test("Organization detail renders source-listed executive ontology without Person promotion", async () => {
  const page = await readFile(new URL("../app/organizations/[id]/page.tsx", import.meta.url), "utf8");
  const graph = await readFile(new URL("../app/components/ontology-local-graph.tsx", import.meta.url), "utf8");
  const data = await readFile(new URL("../app/data.ts", import.meta.url), "utf8");
  const types = await readFile(new URL("../app/types.ts", import.meta.url), "utf8");
  assert.match(page, /getOrganizationOntology/);
  assert.match(page, /OntologyLocalGraph/);
  assert.match(data, /\/ontology\/organizations\/\$\{id\}/);
  assert.match(types, /SOURCE_LISTED_ROLE_HOLDER/);
  assert.match(types, /LISTS_EXECUTIVE/);
  assert.match(graph, /공식 공시상 임원/);
  assert.match(graph, /인물 기록이 아닙니다/);
  assert.doesNotMatch(graph, /href=.*people.*target|confidence|probability|score/i);
});


test("Ontology local graph collapses repeated relation labels for cleaner dense views", async () => {
  const graph = await readFile(new URL("../app/components/ontology-local-graph.tsx", import.meta.url), "utf8");
  assert.match(graph, /const relationKinds = new Set/);
  assert.match(graph, /const singleRelationType =/);
  assert.match(graph, /!singleRelationType/);
  assert.match(graph, /RELATION_LABELS\[singleRelationType\]/);
});


test("SEO gate defaults staging to noindex and requires explicit public base activation", async () => {
  const layout = await readFile(new URL("../app/layout.tsx", import.meta.url), "utf8");
  const site = await readFile(new URL("../app/site-metadata.ts", import.meta.url), "utf8");
  const robots = await readFile(new URL("../app/robots.ts", import.meta.url), "utf8");
  const sitemap = await readFile(new URL("../app/sitemap.ts", import.meta.url), "utf8");
  assert.match(layout, /buildRootMetadata/);
  assert.match(site, /CIVIC_PUBLIC_BASE_URL/);
  assert.match(site, /CIVIC_INDEXING_ENABLED/);
  assert.match(site, /indexingEnabled/);
  assert.match(robots, /disallow: "\/"/);
  assert.match(robots, /disallow: \["\/admin\/"\]/);
  assert.match(robots, /sitemap\.xml/);
  assert.match(sitemap, /getPeople/);
  assert.match(sitemap, /getOrganizations/);
  assert.match(sitemap, /\/gukgam\/2026/);
  assert.doesNotMatch(site + robots + sitemap, /web-staging-efe2|up\.railway\.app/);
});

test("public entity pages expose dynamic neutral metadata without generated likenesses", async () => {
  const person = await readFile(new URL("../app/people/[id]/page.tsx", import.meta.url), "utf8");
  const organization = await readFile(new URL("../app/organizations/[id]/page.tsx", import.meta.url), "utf8");
  const gukgam = await readFile(new URL("../app/gukgam/2026/page.tsx", import.meta.url), "utf8");
  assert.match(person, /generateMetadata/);
  assert.match(person, /buildPageMetadata/);
  assert.match(person, /Claim, Evidence와 출처/);
  assert.match(organization, /generateMetadata/);
  assert.match(organization, /임원 공시, Claim과 Evidence/);
  assert.match(gukgam, /path: "\/gukgam\/2026"/);
  assert.doesNotMatch(person + organization + gukgam, /og:image|generated portrait|AI portrait/i);
});


test("directory list reads use bounded revalidation while detail reads remain request-time", async () => {
  const data = await readFile(new URL("../app/data.ts", import.meta.url), "utf8");
  assert.match(data, /DIRECTORY_REVALIDATE_SECONDS = 60/);
  assert.match(data, /getJson\("\/people", \{ revalidateSeconds: DIRECTORY_REVALIDATE_SECONDS \}\)/);
  assert.match(data, /getJson\("\/organizations", \{/);
  assert.match(data, /revalidateSeconds: DIRECTORY_REVALIDATE_SECONDS/);
  assert.match(data, /getJson\(`\/people\/\$\{id\}`\)/);
  assert.match(data, /getJson\(`\/organizations\/\$\{id\}`\)/);
});


test("Gukgam search deep-links the current query without changing the canonical page", async () => {
  const page = await readFile(new URL("../app/gukgam/2026/page.tsx", import.meta.url), "utf8");
  const search = await readFile(new URL("../app/components/gukgam-search.tsx", import.meta.url), "utf8");
  assert.match(page, /searchParams: Promise<\{ q\?: string \| string\[\] \}>/);
  assert.match(page, /params\.q\.slice\(0, 80\)/);
  assert.match(page, /initialQuery=\{initialQuery\}/);
  assert.match(search, /useQueryState\(initialQuery\)/);
  assert.match(search, /url\.searchParams\.set\("q", trimmed\.slice\(0, 80\)\)/);
  assert.match(search, /window\.history\.replaceState/);
  assert.match(search, /maxLength=\{80\}/);
});


test("Gukgam deep-link search exposes an accessible copy action", async () => {
  const search = await readFile(new URL("../app/components/gukgam-search.tsx", import.meta.url), "utf8");
  const styles = await readFile(new URL("../app/styles.css", import.meta.url), "utf8");
  assert.match(search, /navigator\.clipboard\.writeText\(window\.location\.href\)/);
  assert.match(search, /공유 링크 복사/);
  assert.match(search, /복사됨/);
  assert.match(search, /role="status"/);
  assert.match(search, /aria-live="polite"/);
  assert.match(search, /setCopyStatus\("idle"\)/);
  assert.match(styles, /\.gukgam-search-copy/);
  assert.match(styles, /\.gukgam-search-share-row/);
});


test("Gukgam broad search expands deterministically without ranking", async () => {
  const search = await readFile(new URL("../app/components/gukgam-search.tsx", import.meta.url), "utf8");
  assert.match(search, /INITIAL_RESULT_LIMIT = 6/);
  assert.match(search, /RESULT_PAGE_SIZE = 12/);
  assert.match(search, /peopleMatches\.slice\(0, peopleLimit\)/);
  assert.match(search, /organizationMatches\.slice\(0, organizationLimit\)/);
  assert.match(search, /setPeopleLimit\(INITIAL_RESULT_LIMIT\)/);
  assert.match(search, /setOrganizationLimit\(INITIAL_RESULT_LIMIT\)/);
  assert.match(search, /인물 \{Math\.min\(RESULT_PAGE_SIZE/);
  assert.match(search, /기관 \{Math\.min/);
  assert.doesNotMatch(search, /\.sort\(|score|rank|probability|confidence/i);
});


test("Gukgam published targets stay Claim-backed and separate from review candidates", async () => {
  const page = await readFile(new URL("../app/gukgam/2026/page.tsx", import.meta.url), "utf8");
  const data = await readFile(new URL("../app/data.ts", import.meta.url), "utf8");
  const types = await readFile(new URL("../app/types.ts", import.meta.url), "utf8");

  assert.match(page, /getGukgamTargets/);
  assert.match(page, /공개된 피감대상/);
  assert.match(page, /전체 감사대상 목록이 아닙니다/);
  assert.match(page, /이 일정의 근거 보기/);
  assert.match(page, /Claim·Evidence 확인 경로/);
  assert.match(page, /organizations\/\$\{item\.organization\.id\}#claim-\$\{item\.claim_id\}/);
  assert.match(data, /getJson\("\/gukgam\/2026\/targets"\)/);
  assert.match(types, /PUBLIC_CLAIM_BACKED_GUKGAM_AUDIT_TARGETS_V1/);
  assert.match(types, /BOUNDED_INCOMPLETE_PUBLISHED_CLAIMS_ONLY/);
  assert.doesNotMatch(page, /review_key|match_class|candidate_relationship/);
  assert.doesNotMatch(data, /admin\/gukgam\/2026\/organization-binding/);
});


test("operator console is opt-in, bounded, read-only and keeps tokens server-only", async () => {
  const read = async (name) => readFile(new URL(`../app/admin/review/${name}`, import.meta.url), "utf8");
  const data = await read("operator-data.ts");
  const page = await read("page.tsx");
  const graph = await read("operator-graph.tsx");
  assert.match(data, /import "server-only"/);
  assert.match(data, /CIVIC_OPERATOR_ENABLED/);
  assert.match(data, /notFound/);
  assert.match(data, /127\.0\.0\.1/);
  assert.match(data, /X-Civic-Operator-Token/);
  assert.match(data, /cache: "no-store"/);
  assert.match(page, /await requireOperator\(\)/);
  assert.match(page, /method="get"/);
  assert.match(page, /limit: "25"/);
  assert.match(graph, /import\("cytoscape"\)/);
  assert.match(graph, /graph\.truncated/);
  assert.match(graph, /키보드용 노드/);
  assert.doesNotMatch(graph, /CIVIC_OPERATOR_TOKEN|NEXT_PUBLIC|fetch\(|axios/);
});


test("admin workflows use confirmed server receipts and never expose server credentials", async () => {
  const action = await readFile(new URL("../app/admin/review/admin-actions.tsx", import.meta.url), "utf8");
  const route = await readFile(new URL("../app/admin/review/actions/route.ts", import.meta.url), "utf8");
  const queue = await readFile(new URL("../app/admin/review/admin-queue.tsx", import.meta.url), "utf8");
  assert.match(action, /변경 미리보기/);
  assert.match(action, /preview_token/);
  assert.match(action, /confirmed: true/);
  assert.match(action, /await adminRequest<AdminReceipt>/);
  assert.match(route, /origin !== `http:\/\/\$\{host\}`/);
  assert.match(route, /x-civic-admin-intent/);
  assert.match(route, /await requireOperator/);
  assert.match(queue, /named_record_total/);
  assert.match(queue, /동일인 미확정/);
  assert.doesNotMatch(action + queue, /CIVIC_OPERATOR_TOKEN|DATABASE_URL/);
});


test("playbook prepares exact reference drafts and never pretends to dispatch", async () => {
  const load = (name) => readFile(new URL(`../app/admin/review/${name}`, import.meta.url), "utf8");
  const [playbook, page, queue, route] = await Promise.all([load("work-playbook.tsx"), load("page.tsx"), load("admin-queue.tsx"), load("actions/route.ts")]);
  assert.match(playbook, /work_order_draft/);
  assert.match(playbook, /version: item\.version/);
  assert.match(playbook, /prepared\?\.signature === signature/);
  assert.match(playbook, /에이전트 실행 미연동/);
  assert.match(playbook, /source_content_included/);
  assert.match(playbook, /clipboard\.writeText/);
  assert.match(playbook, /Markdown 내려받기/);
  assert.match(queue, /records=\{selectedItems\}/);
  assert.match(page, /entry\.version/);
  assert.match(route, /work_order_draft: "playbook\/draft"/);
  assert.match(route, /Object\.hasOwn/);
  assert.doesNotMatch(playbook, /CIVIC_OPERATOR_TOKEN|DATABASE_URL|child_process|spawn\(/);
});


test("Gukgam schedule groups published targets by date and committee without adding items", async () => {
  const { focusDate, formatAuditDate, groupByDateAndCommittee, seoulDate } = await import(
    "../app/gukgam/2026/schedule.ts"
  );
  const item = (claim_id, audit_date, committee_name, name, time_text = null) => ({
    claim_id, audit_date, committee_name, time_text, organization: { id: `org-${claim_id}`, name },
  });
  const items = [
    item("c3", "2026-10-07", "국방위원회", "나기관", "10:00"),
    item("c1", "2026-10-06", "행정안전위원회", "가기관", "10:00"),
    item("c4", "2026-10-07", "국방위원회", "가기관", "10:00"),
    item("c2", "2026-10-07", "과학기술정보방송통신위원회", "다기관"),
  ];
  const groups = groupByDateAndCommittee(items, "2026-10-07");
  assert.deepEqual(groups.map((group) => [group.date, group.relation, group.count]), [
    ["2026-10-06", "past", 1],
    ["2026-10-07", "today", 3],
  ]);
  assert.deepEqual(groups[1].committees.map((group) => group.committee), [
    "과학기술정보방송통신위원회",
    "국방위원회",
  ]);
  assert.deepEqual(groups[1].committees[1].items.map((row) => row.claim_id), ["c4", "c3"]);
  assert.equal(groups.flatMap((group) => group.committees.flatMap((c) => c.items)).length, items.length);
  assert.equal(focusDate(groups), "2026-10-07");
  assert.equal(focusDate(groupByDateAndCommittee(items, "2026-10-30")), null);
  assert.equal(formatAuditDate("2026-10-06"), "10월 6일 (화)");
  assert.equal(seoulDate(new Date("2026-10-05T15:30:00Z")), "2026-10-06");
});

test("Gukgam schedule keeps scope limits and evidence links visible", async () => {
  const page = await readFile(new URL("../app/gukgam/2026/page.tsx", import.meta.url), "utf8");
  const schedule = await readFile(new URL("../app/gukgam/2026/schedule.ts", import.meta.url), "utf8");
  assert.match(page, /groupByDateAndCommittee\(targetItems, today\)/);
  assert.match(page, /전체 감사대상 목록이 아닙니다/);
  assert.match(page, /계획서상 일정/);
  assert.match(page, /오늘 \(KST\)/);
  assert.match(page, /근거 계획서 공개일/);
  const kst = await readFile(new URL("../app/components/kst-schedule.tsx", import.meta.url), "utf8");
  assert.match(page, /<AuditDateIndex serverToday=\{today\} days=\{scheduleDays\} \/>/);
  assert.match(kst, /aria-label="감사일별 이동"/);
  const organization = await readFile(new URL("../app/organizations/[id]/page.tsx", import.meta.url), "utf8");
  const panel = await readFile(new URL("../app/components/evidence-panel.tsx", import.meta.url), "utf8");
  assert.match(organization, /<EvidencePanel/);
  assert.match(panel, /id=\{`claim-\$\{claim\.id\}`\}/);
  assert.doesNotMatch(page + schedule, /score|rank|probability|confidence|위험도|의혹/i);
});


test("Gukgam committee anchors derive only from the official committee name", async () => {
  const { committeeAnchor, committeeHref } = await import("../app/gukgam/2026/committees.ts");
  assert.equal(committeeAnchor("국방위원회"), "committee-국방위원회");
  assert.equal(committeeAnchor(" 연금개혁 특별위원회 "), "committee-연금개혁-특별위원회");
  assert.equal(committeeHref("행정안전위원회"), "/gukgam/2026#committee-행정안전위원회");
  assert.notEqual(committeeAnchor("기획재정위원회"), committeeAnchor("재정경제기획위원회"));
});

test("Gukgam committee members stay Claim-backed, roster-scoped and unranked", async () => {
  const page = await readFile(new URL("../app/gukgam/2026/page.tsx", import.meta.url), "utf8");
  const members = await readFile(new URL("../app/components/committee-members.tsx", import.meta.url), "utf8");
  const data = await readFile(new URL("../app/data.ts", import.meta.url), "utf8");
  const types = await readFile(new URL("../app/types.ts", import.meta.url), "utf8");
  const styles = await readFile(new URL("../app/styles.css", import.meta.url), "utf8");
  assert.match(page, /getGukgamCommittees/);
  assert.match(page, /<CommitteeMembers committee=\{committee\} label="위원 명단" \/>/);
  assert.match(page, /감사 위원 \{committeeByName\.get\(committee\.committee\)!\.member_count\}명/);
  assert.match(page, /위원회별 감사 위원/);
  assert.match(page, /id=\{committeeAnchor\(committee\.committee_name\)\}/);
  assert.match(page, /국회 명부 기준 위원입니다/);
  assert.match(members, /감사 위원/);
  assert.match(members, /href=\{`\/people\/\$\{member\.person\.id\}`\}/);
  assert.match(members, /href=\{`\/people\/\$\{member\.person\.id\}#claim-\$\{member\.claim_id\}`\}/);
  assert.match(members, /member\.epistemic_status/);
  assert.match(members, /key=\{member\.person\.id\}/);
  assert.doesNotMatch(members, /\.sort\(|score|rank|probability|confidence|"use client"|onClick/i);
  assert.match(data, /getJson\("\/gukgam\/2026\/committees"\)/);
  assert.match(types, /PUBLIC_CLAIM_BACKED_GUKGAM_COMMITTEE_MEMBERS_V1/);
  assert.match(types, /MEMBER_ROSTER_SNAPSHOT_NOT_AUDIT_DAY_ATTENDANCE/);
  assert.match(styles, /\.committee-member-list/);
  assert.match(styles, /\.committee-index/);
});

test("Committees without published targets show only a roster note, never invented schedule rows", async () => {
  const read = (path) => readFile(new URL(path, import.meta.url), "utf8");
  const [page, person, types, styles] = await Promise.all([
    read("../app/gukgam/2026/page.tsx"),
    read("../app/people/[id]/page.tsx"),
    read("../app/types.ts"),
    read("../app/styles.css"),
  ]);
  assert.match(types, /target_claim_coverage: "PUBLISHED" \| "NOT_YET_PUBLISHED"/);
  for (const source of [page, person]) {
    assert.match(source, /committee\.target_claim_coverage === "NOT_YET_PUBLISHED"/);
    assert.match(source, /피감대상 공개 기록 준비 중 — 위원 명단만 표시/);
  }
  // The committee index lists every committee returned by the API, with no target filter.
  assert.match(page, /\{committees\.map\(\(committee\) => \(\s*<li key=\{committee\.committee_name\}/);
  assert.doesNotMatch(page, /committees\.filter\(/);
  // The person section keys on roster membership, and dates still come only from published targets.
  assert.match(person, /committee\.members\.find\(\(item\) => item\.person\.id === person\.id\)/);
  assert.match(person, /targetItems\.filter\(\(item\) => item\.committee_name === committee\.committee_name\)/);
  assert.match(person, /공개된 일정 없음/);
  assert.match(styles, /\.committee-targets-pending/);
});

test("Organization detail shows the 2026 Gukgam section without linking executives to People", async () => {
  const page = await readFile(new URL("../app/organizations/[id]/page.tsx", import.meta.url), "utf8");
  assert.match(page, /getGukgamTargets\(\)/);
  assert.match(page, /getGukgamCommittees\(\)/);
  assert.match(page, /item\.organization\.id === organization\.id/);
  assert.match(page, /id="gukgam-2026"/);
  assert.match(page, /2026 국정감사/);
  assert.match(page, /<CommitteeMembers committee=\{committee\} \/>/);
  assert.match(page, /#executives/);
  assert.match(page, /gukgamItems\.length > 0/);
  assert.doesNotMatch(page, /href=\{`\/people\/\$\{(claim|qualifiers)/);
});

test("Person ontology links a committee to Gukgam only when it is a Gukgam committee", async () => {
  const graph = await readFile(new URL("../app/components/ontology-local-graph.tsx", import.meta.url), "utf8");
  const person = await readFile(new URL("../app/people/[id]/page.tsx", import.meta.url), "utf8");
  assert.match(graph, /gukgamCommittees = \[\]/);
  assert.match(graph, /new Set\(gukgamCommittees\)/);
  assert.match(graph, /target\?\.kind === "COMMITTEE" && gukgamCommitteeNames\.has\(target\.label\)/);
  assert.match(graph, /committeeHref\(target\.label\)/);
  assert.match(graph, /edge\.relation_type === "SERVED_ON"/);
  assert.match(graph, /`claim-\$\{edge\.claim_id\}`/);
  assert.match(person, /getGukgamCommittees\(\)/);
  assert.match(person, /gukgamCommittees=\{gukgamCommittees\}/);
  assert.doesNotMatch(graph, /"use client"|onClick|confidence|score|probability/);
});


test("one shared evidence panel renders every Claim on Person and Organization pages", async () => {
  const read = (path) => readFile(new URL(path, import.meta.url), "utf8");
  const [person, organization, panel, opener, factBox, state] = await Promise.all([
    read("../app/people/[id]/page.tsx"),
    read("../app/organizations/[id]/page.tsx"),
    read("../app/components/evidence-panel.tsx"),
    read("../app/components/open-target-details.tsx"),
    read("../app/components/fact-box.tsx"),
    read("../app/components/read-state.tsx"),
  ]);
  for (const page of [person, organization]) {
    assert.match(page, /<EvidencePanel/);
    assert.match(page, /<OpenTargetDetails \/>/);
    assert.match(page, /<FactBox rows=\{factRows\} \/>/);
    assert.match(page, /<PendingLanes/);
    assert.match(page, /className="page-anchors"/);
    assert.doesNotMatch(page, /Evidence trace|Audit trace|className="evidence-trace"/);
  }
  assert.match(person, /<aside className="profile-index"/);
  assert.match(panel, /id=\{`claim-\$\{claim\.id\}`\}/);
  assert.match(panel, /<details className="evidence-disclosure">/);
  assert.match(panel, /근거 열기/);
  assert.match(panel, /SOURCE CONFLICT/);
  assert.match(panel, /종료일 없음/);
  assert.match(panel, /공개일 미기재/);
  assert.match(panel, /현실 세계의 사건 시각이 아닙니다/);
  assert.match(panel, /출처가 말한 범위까지만 표시합니다/);
  assert.match(panel, /terms_checked_at/);
  assert.match(panel, /policy_summary/);
  assert.match(panel, /snapshot_id/);
  for (const label of ["기록", "상태", "유효 기간", "기록 시각", "근거", "출처", "원문 값", "처리 방식", "출처 정책", "한계", "감사 ID"]) {
    assert.ok(panel.includes(label), label);
  }
  // Ordered definition list; IDs only inside the nested audit disclosure, never in the summary line.
  assert.ok(panel.indexOf("<dt>기록</dt>") < panel.indexOf("<dt>유효 기간</dt>"));
  assert.ok(panel.indexOf("<dt>출처 정책</dt>") < panel.indexOf("<dt>한계</dt>"));
  assert.ok(panel.indexOf("<dt>한계</dt>") < panel.indexOf("evidence-audit"));
  const summary = panel.slice(panel.indexOf("<summary>"), panel.indexOf("</summary>"));
  assert.doesNotMatch(summary, /claim\.id|source\.id|evidence\.id|item\.id|_id|snapshot|observation/);
  assert.match(opener, /"use client"/);
  assert.match(opener, /hashchange/);
  assert.match(opener, /details\.evidence-disclosure/);
  assert.match(factBox, /href=\{`#claim-\$\{row\.claim\.id\}`\}/);
  assert.match(factBox, /집계/);
  assert.match(state, /<summary>요청 ID<\/summary>/);
  assert.doesNotMatch(state, /<small>Request ID/);
});

test("Person page adds Gukgam committee context and drops empty lanes into one line", async () => {
  const person = await readFile(new URL("../app/people/[id]/page.tsx", import.meta.url), "utf8");
  const lanes = await readFile(new URL("../app/components/pending-lanes.tsx", import.meta.url), "utf8");
  const org = await readFile(new URL("../app/organizations/[id]/page.tsx", import.meta.url), "utf8");
  assert.match(person, /getGukgamTargets\(\)/);
  assert.match(person, /id="gukgam-2026"/);
  assert.match(person, /\/gukgam\/2026#audit-\$\{date\}/);
  assert.match(person, /\/organizations\/\$\{organization\.id\}/);
  assert.match(person, /memberCommittees\.length > 0/);
  assert.match(person, /section\.entries\.length === 0/);
  assert.match(person, /section\.entries\.length === 0 \? null/);
  assert.match(lanes, /아직 수집되지 않은 기록/);
  // Empty profile sections are grouped by the projection reason instead of one "not collected" line.
  for (const reason of ["SOURCE_NOT_COLLECTED", "INSUFFICIENT_EVIDENCE", "DERIVATION_NOT_AVAILABLE", "NOT_APPLICABLE"]) {
    assert.match(person, new RegExp(`reason: "${reason}"`));
  }
  assert.match(person, /<PendingLanes key=\{group\.reason\} title=\{group\.title\}/);
  assert.match(org, /pendingLanes/);
  assert.doesNotMatch(org + person, /현재 임원 이름 공개 기록이 없습니다|검토된 항목이 없습니다/);
});

test("Gukgam schedule links to the single committee member list instead of repeating it per date", async () => {
  const page = await readFile(new URL("../app/gukgam/2026/page.tsx", import.meta.url), "utf8");
  assert.equal((page.match(/<CommitteeMembers/g) ?? []).length, 1);
  assert.match(page, /gukgam-committee-members-link/);
  assert.match(page, /href=\{`#\$\{committeeAnchor\(committee\.committee\)\}`\}/);
  assert.match(page, /id=\{committeeAnchor\(committee\.committee_name\)\}/);
});

test("evidence panel and fact box keep status chips readable and avoid unsupported surfaces", async () => {
  const styles = await readFile(new URL("../app/styles.css", import.meta.url), "utf8");
  const panel = await readFile(new URL("../app/components/evidence-panel.tsx", import.meta.url), "utf8");
  const factBox = await readFile(new URL("../app/components/fact-box.tsx", import.meta.url), "utf8");
  assert.match(styles, /\.evidence-panel \.status, \.fact-table \.status[^{]*\{ font-size: 13px; \}/);
  assert.match(styles, /\.evidence-panel:target/);
  assert.doesNotMatch(panel + factBox, /confidence|faction|influence|probability|score|rank/i);
});


test("Gukgam search receives only displayed facet values, not evidence IDs", async () => {
  const page = await readFile(new URL("../app/gukgam/2026/page.tsx", import.meta.url), "utf8");
  const search = await readFile(new URL("../app/components/gukgam-search.tsx", import.meta.url), "utf8");
  assert.match(page, /facets: searchFacets\(discovery\.facets\)/);
  assert.match(page, /return facet \? \{ value: facet\.value \} : null;/);
  assert.match(search, /export type GukgamSearchFacets/);
});

test("모두의국감 public brand replaces developer-facing names without renaming internals", async () => {
  const read = (path) => readFile(new URL(path, import.meta.url), "utf8");
  const [layout, site, home, people, roster, notFound, icon, data] = await Promise.all([
    read("../app/layout.tsx"),
    read("../app/site-metadata.ts"),
    read("../app/page.tsx"),
    read("../app/people/page.tsx"),
    read("../app/components/roster-grid.tsx"),
    read("../app/not-found.tsx"),
    read("../app/icon.svg"),
    read("../app/data.ts"),
  ]);
  assert.match(site, /SITE_NAME = "모두의국감"/);
  assert.match(site, /siteName: SITE_NAME/);
  assert.match(site, /template: `%s — \$\{SITE_NAME\}`/);
  assert.match(layout, /\{SITE_NAME\}/);
  for (const label of ["인물 찾기", "국감 일정", "기관", "자료 범위"]) assert.ok(layout.includes(label), label);
  assert.match(layout, /href="\/#coverage"/);
  assert.match(home, /id="coverage"/);
  assert.match(icon, /aria-label="모두의국감"/);
  for (const body of [layout, home, people, notFound, icon]) {
    assert.doesNotMatch(body, /Civic Intel|Evidence Directory|>CI<|Return to People/);
  }
  // Root search is a plain GET into the canonical People route; no new search backend.
  assert.match(home, /<form className="home-search-form" action="\/people" method="get" role="search">/);
  assert.match(home, /name="q"/);
  assert.match(home, /maxLength=\{80\}/);
  assert.doesNotMatch(home, /fetch\(|score|rank|probability|confidence/i);
  assert.match(people, /params\.q\.slice\(0, 80\)/);
  assert.match(roster, /useQueryState\(initialQuery\)/);
  // Scope language stays bounded and the schedule copy is source-gated.
  assert.match(home, /모든 국감 참여자나 전체 증인 명단은 아닙니다/);
  const kst = await read("../app/components/kst-schedule.tsx");
  assert.match(kst, /오늘은 공개된 감사 일정이 없습니다/);
  assert.doesNotMatch(home, /모든 공직자|완전한 이력|전체 국감 참여자/);
  // Internal API/env naming is unchanged by the public rename.
  assert.match(data, /CIVIC_API_URL/);
});

test("Sites snapshot export keeps reader-time dates and ?q= correct without a server", async () => {
  const read = (path) => readFile(new URL(path, import.meta.url), "utf8");
  const [kst, query, person, organization, layout, home, script, eslint] = await Promise.all([
    read("../app/components/kst-schedule.tsx"),
    read("../app/components/query-param.ts"),
    read("../app/people/[id]/page.tsx"),
    read("../app/organizations/[id]/page.tsx"),
    read("../app/layout.tsx"),
    read("../app/page.tsx"),
    read("../scripts/build-sites-snapshot.mjs"),
    read("../eslint.config.mjs"),
  ]);
  // "Today" is computed in the reader's browser (KST) after hydration, never frozen at build time.
  assert.match(kst, /useSyncExternalStore\(subscribe, \(\) => seoulDate\(new Date\(\)\), \(\) => serverToday\)/);
  assert.match(home, /<TodayAuditLine serverToday=\{today\} days=\{scheduleDays\} \/>/);
  assert.match(query, /useSyncExternalStore\(subscribe, readQueryParam, \(\) => initialQuery\)/);
  assert.match(query, /\.slice\(0, 80\)/);
  // Server builds keep per-request detail pages; only the staged snapshot copy prerenders them.
  for (const page of [person, organization]) assert.doesNotMatch(page, /generateStaticParams/);
  assert.match(script, /export async function generateStaticParams/);
  assert.match(script, /Snapshot export cannot list/);
  assert.match(layout, /CIVIC_SNAPSHOT_AT/);
  // The export build reads only the public API, drops the operator surface and fails closed.
  assert.match(script, /\/ready/);
  assert.match(script, /rmSync\(join\(stage, "app", "admin"\)/);
  assert.match(script, /output: "export"/);
  assert.match(script, /FORBIDDEN_TOKENS/);
  assert.match(script, /snapshot-manifest\.json/);
  assert.doesNotMatch(script, /process\.env\.(DATABASE_URL|CIVIC_OPERATOR_TOKEN|[A-Z_]+_API_KEY)/);
  assert.match(eslint, /\.sites-build/);
});

test("Official 국감 witness lists are shown and searchable as source text, never as People", async () => {
  const read = (path) => readFile(new URL(path, import.meta.url), "utf8");
  const [gukgam, people, roster, witnesses] = await Promise.all([
    read("../app/gukgam/2026/page.tsx"),
    read("../app/people/page.tsx"),
    read("../app/components/roster-grid.tsx"),
    read("../app/components/gukgam-witnesses.tsx"),
  ]);
  assert.match(gukgam, /<GukgamWitnesses \/>/);
  assert.match(gukgam, /href="#gukgam-witnesses-title"/);
  assert.match(witnesses, /id=\{`witness-\$\{item\.claim_id\}`\}/);
  assert.match(witnesses, /전체 명단이 아니며/);
  assert.doesNotMatch(witnesses, /projection\.limitations/);
  assert.match(people, /getGukgamWitnesses\(\)/);
  assert.match(people, /witnesses=\{witnesses\}/);
  assert.match(roster, /export type WitnessListing/);
  assert.match(roster, /href=\{`\/gukgam\/2026#witness-\$\{row\.claimId\}`\}/);
  assert.match(roster, /같은 사람인지는 확인하지 않았습니다/);
  // A witness row never links to a Person page and carries no Person identifier.
  const section = roster.slice(roster.indexOf("witness-matches"));
  assert.doesNotMatch(section, /\/people\/|person\.id|person_id/);
});

test("Witness rows carry the owner source tag and mark supplied copies as not yet official", async () => {
  const read = (path) => readFile(new URL(path, import.meta.url), "utf8");
  const [witnesses, roster, people, types] = await Promise.all([
    read("../app/components/gukgam-witnesses.tsx"),
    read("../app/components/roster-grid.tsx"),
    read("../app/people/page.tsx"),
    read("../app/types.ts"),
  ]);
  assert.match(types, /source_tag: "#공식게시" \| "#공식회의록" \| "#제공사본_HWP" \| "#제공사본_비HWP"/);
  assert.match(witnesses, /\{item\.source_tag\}/);
  assert.match(witnesses, /OWNER_SUPPLIED_COPY" \? " · 아직 공식 발표 아님"/);
  assert.match(people, /officiallyPublished: item\.acquisition_channel !== "OWNER_SUPPLIED_COPY"/);
  assert.match(roster, /아직 공식 발표 아님/);
});

test("Sites snapshot fits the 256 MiB limit by dropping only never-requested duplicates", async () => {
  const script = await readFile(new URL("../scripts/build-sites-snapshot.mjs", import.meta.url), "utf8");
  assert.match(script, /SITES_MAX_BYTES = 256 \* 1024 \* 1024/);
  assert.match(script, /"__next\._full\.txt"/);
  assert.match(script, /readFileSync\(sibling\)\.equals\(readFileSync\(path\)\)/);
  assert.match(script, /bundleBytes > SITES_MAX_BYTES/);
  assert.match(script, /bytes: bundleBytes/);
  // Detail-route page segments go only when the sibling index.txt that navigation uses exists.
  assert.ok(script.includes(String.raw`\$d\$id\.__PAGE__\.txt$/`));
  assert.match(script, /has no sibling index\.txt; refusing to drop it/);
});


test("public design floor: readable sizes, 48px controls, Korean labels, status not by color alone", async () => {
  const read = (path) => readFile(new URL(path, import.meta.url), "utf8");
  const css = (await read("../app/styles.css")) + (await read("../app/components/gukgam-witnesses.css"));
  for (const match of css.matchAll(/font-size:\s*(\d+(?:\.\d+)?)px/g)) {
    assert.ok(Number(match[1]) >= 13, `font-size ${match[1]}px is below the 13px floor`);
  }
  assert.doesNotMatch(css, /text-transform:\s*uppercase/);
  assert.match(css, /body \{[^}]*font: 17px\/1\.65/);
  assert.match(css, /body \{[^}]*font-variant-numeric: tabular-nums/);
  assert.match(css, /--color-ink-muted: #5c6862/);
  assert.match(css, /\.status:is\([^)]*\.FACT[^)]*\)::before \{ content: "✓"/);
  assert.match(css, /\.status:is\([^)]*\.UNKNOWN[^)]*\)::before \{ content: "\?"/);
  assert.doesNotMatch(css, /eyebrow-mark|row-index/);
  const pages = await Promise.all([
    "../app/page.tsx", "../app/gukgam/2026/page.tsx", "../app/people/[id]/page.tsx",
    "../app/organizations/[id]/page.tsx", "../app/organizations/page.tsx", "../app/components/roster-grid.tsx",
    "../app/people/page.tsx", "../app/people/loading.tsx", "../app/components/gukgam-search.tsx",
  ].map(read));
  for (const page of pages) {
    assert.doesNotMatch(page, /<em>|eyebrow-mark|row-index|Evidence & audit|Published claims|Methodology & coverage/);
    // Plain public layout: no label-above-heading eyebrows, decorative avatars, arrow badges or KPI tiles.
    assert.doesNotMatch(page, /className="eyebrow"|row-avatar|organization-avatar|gukgam-search-avatar|row-arrow|profile-stamp|entry-index|coverage-strip|signal-strip/);
  }
  // One sans family, flat surfaces, no gradients on cards.
  assert.doesNotMatch(css, /Serif|Georgia|Batang/);
  assert.match(css, /--shadow-card: none/);
  assert.doesNotMatch(css, /linear-gradient\(145deg/);
});

test("Sites snapshot fails instead of freezing a temporary read failure into a page", async () => {
  const script = await readFile(new URL("../scripts/build-sites-snapshot.mjs", import.meta.url), "utf8");
  assert.match(script, /read-state SERVICE_UNAVAILABLE/);
  assert.match(script, /captured a service failure/);
  assert.match(script, /experimental: \{ cpus: 2 \}/);
});

test("Plenary votes render as compact rows with the evidence trace one disclosure away", async () => {
  const person = await readFile(new URL("../app/people/[id]/page.tsx", import.meta.url), "utf8");
  assert.match(person, /entry\.details\.action === "PLENARY_ROLL_CALL_VOTE"/);
  assert.match(person, /<ol className="vote-rows">/);
  assert.match(person, /<details className="audit-details vote-trace">/);
  assert.match(person, /FeederObservation \{trace\?\.feeder_observation_id/);
});

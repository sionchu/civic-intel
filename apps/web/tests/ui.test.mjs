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
  assert.match(page, /Evidence & audit/);
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
  assert.match(profile, /profile-stamp/);
  assert.match(roster, /className="row-avatar"/);
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
  assert.match(page, /<RosterGrid people=\{peopleResult\.data\} \/>/);
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

  assert.match(home, /공개 기록을/);
  assert.match(home, /사람 기록 탐색/);
  assert.match(home, /Identity/);
  assert.match(home, /Evidence/);
  assert.match(home, /Source/);
  assert.doesNotMatch(home, /<RosterGrid|hero-panel|signal-strip/);
  assert.match(people, /명의 공개 기록/);
  assert.doesNotMatch(people, /profile-stamp/);
  assert.match(roster, /className="roster-row"/);
  assert.match(roster, /className="row-proof"/);
  assert.match(roster, /key=\{person\.id\}/);
  assert.doesNotMatch(roster, /person-card|FeederObservation|normalized/);
  assert.doesNotMatch(styles, /\.hero-panel|\.panel-visual|\.panel-ring|\.panel-dot|\.panel-cross|\.person-card|\.signal-dot/);
});

test("UI exposes explicit provenance and a read-only review surface", async () => {
  const profile = await readFile(new URL("../app/people/[id]/page.tsx", import.meta.url), "utf8");
  const review = await readFile(new URL("../app/admin/review/page.tsx", import.meta.url), "utf8");
  const layout = await readFile(new URL("../app/layout.tsx", import.meta.url), "utf8");
  assert.match(profile, /SOURCE CONFLICT/);
  assert.match(profile, /trace\.stance/);
  assert.match(profile, /snapshot_id/);
  assert.match(profile, /policy_summary/);
  assert.match(review, /requireOperator/);
  assert.match(review, /operatorRead/);
  assert.match(review, /item\.action/);
  assert.match(review, /item\.status/);
  assert.doesNotMatch(review, /method="post"|--commit/);
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
  assert.match(home, /국감 2026/);
  assert.match(page, /Civic Intel \/ Event surface/);
  assert.match(page, /getPeople/);
  assert.match(page, /getOrganizations/);
  assert.match(page, /검증된 만큼만/);
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
  assert.match(search, /새로운 identity 연결을 만들지 않습니다/);
  assert.doesNotMatch(search, /fetch\(|axios|confidence|probability|score|rank/i);
});


test("Organization detail renders source-listed executive ontology without Person promotion", async () => {
  const page = await readFile(new URL("../app/organizations/[id]/page.tsx", import.meta.url), "utf8");
  const graph = await readFile(new URL("../app/components/ontology-local-graph.tsx", import.meta.url), "utf8");
  const data = await readFile(new URL("../app/data.ts", import.meta.url), "utf8");
  const types = await readFile(new URL("../app/types.ts", import.meta.url), "utf8");
  assert.match(page, /getOrganizationOntology/);
  assert.match(page, /OntologyLocalGraph/);
  assert.match(page, /source-listed record/);
  assert.match(page, /canonical Person으로 자동 연결하지 않습니다/);
  assert.match(data, /\/ontology\/organizations\/\$\{id\}/);
  assert.match(types, /SOURCE_LISTED_ROLE_HOLDER/);
  assert.match(types, /LISTS_EXECUTIVE/);
  assert.match(graph, /공식 공시상 임원/);
  assert.match(graph, /canonical Person이 아닙니다/);
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
  assert.match(search, /useState\(initialQuery\)/);
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
  assert.match(search, /People \{Math\.min\(RESULT_PAGE_SIZE/);
  assert.match(search, /Organizations \{Math\.min/);
  assert.doesNotMatch(search, /\.sort\(|score|rank|probability|confidence/i);
});


test("Gukgam published targets stay Claim-backed and separate from review candidates", async () => {
  const page = await readFile(new URL("../app/gukgam/2026/page.tsx", import.meta.url), "utf8");
  const data = await readFile(new URL("../app/data.ts", import.meta.url), "utf8");
  const types = await readFile(new URL("../app/types.ts", import.meta.url), "utf8");

  assert.match(page, /getGukgamTargets/);
  assert.match(page, /공개된 피감대상/);
  assert.match(page, /전체 감사대상 목록이 아닙니다/);
  assert.match(page, /기관 Claim \/ Evidence 보기/);
  assert.match(page, /Claim \/ Evidence audit trace/);
  assert.match(page, /organizations\/\$\{item\.organization\.id\}#claims/);
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

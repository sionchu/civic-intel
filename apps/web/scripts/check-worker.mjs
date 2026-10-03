import assert from "node:assert/strict";
import { createServer } from "node:http";
import { readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { unstable_dev } from "wrangler";

process.env.WRANGLER_SEND_METRICS = "false";
process.env.CLOUDFLARE_CF_FETCH_ENABLED = "false";
process.env.WRANGLER_WRITE_LOGS = "false";

const root = new URL("../", import.meta.url);
const config = JSON.parse(await readFile(new URL("dist/server/wrangler.json", root), "utf8"));
assert.equal(config.main, "index.js");
assert.equal(config.no_bundle, true);
assert.equal(config.assets.directory, "../client");
assert.deepEqual(config.vars, {});

const organizationId = "11111111-1111-4111-8111-111111111111";
const portraitId = "44745d09-398c-46ce-bc38-81f0f606c1d7";
const proofId = "22222222-2222-4222-8222-222222222222";
const sourceId = "33333333-3333-4333-8333-333333333333";
const evidenceId = "44444444-4444-4444-8444-444444444444";
const snapshotId = "55555555-5555-4555-8555-555555555555";
const observationId = "66666666-6666-4666-8666-666666666666";
const empty = {
  semantics: "PUBLIC_CLAIM_BACKED_GUKGAM_AUDIT_TARGETS_V1",
  coverage: "BOUNDED_INCOMPLETE_PUBLISHED_CLAIMS_ONLY", year: 2026,
  target_count: 0, committee_count: 0, items: [], limitations: [],
};
const item = {
  organization: { id: organizationId, name: "테스트 피감기관" },
  committee_name: "테스트 위원회", audit_date: "2026-10-10", time_text: null,
  venue: null, section: "테스트 계획", page_number: 1, source_published_date: "2026-10-01",
  claim_id: proofId, evidence_ids: [evidenceId], source_ids: [sourceId],
  snapshot_ids: [snapshotId], observation_ids: [observationId],
};
const organization = {
  id: organizationId, name: item.organization.name, valid_from: "2026-10-01T00:00:00Z",
  valid_to: null, recorded_at: "2026-10-01T00:00:00Z", superseded_at: null,
  claims: [{
    id: proofId, organization_id: organizationId,
    proposition: "테스트 피감기관은 테스트 위원회 감사계획의 피감대상으로 기재되어 있다.",
    subject: item.organization.name, predicate: "LISTED_AS_GUKGAM_AUDIT_TARGET",
    object_text: "테스트 위원회 · 2026-10-10 피감대상", epistemic_status: "FACT",
    publication_status: "PUBLISHED", asserted_as_true: true, resolution_note: null,
    qualifiers: { committee_name: item.committee_name, audit_date: item.audit_date,
      event_semantics: "OFFICIAL_PLAN_LISTING_NOT_COMPLETED_AUDIT" },
    evidence: [{ id: evidenceId, source_id: sourceId, snapshot_id: snapshotId,
      feeder_observation_id: observationId, stance: "SUPPORT", excerpt: null }],
    source_ids: [sourceId],
  }],
};
const annualClaim = { ...organization.claims[0],
  id: "77777777-7777-4777-8777-777777777777",
  predicate: "SYNTHETIC_ANNUAL_DISCLOSURE", proposition: "테스트 연간 공시 기록",
  qualifiers: { fiscal_year: "2025" },
  evidence: [{ ...organization.claims[0].evidence[0],
    id: "88888888-8888-4888-8888-888888888888" }],
};
const source = {
  id: sourceId, url: "https://evidence.example.test/audit-plan",
  title: "테스트 감사계획 출처", publisher: "합성 테스트 발행기관",
  published_at: "2026-10-01T00:00:00Z", source_class: "OFFICIAL_PRIMARY",
  license: "Synthetic fixture only", terms_checked_at: "2026-10-01T00:00:00Z",
  policy_summary: { collection: "PERMITTED", metadata_storage: "PERMITTED",
    fulltext_storage: "NOT_PERMITTED", excerpt_display: "NOT_PERMITTED" },
};
let mode = "empty";
const calls = [];
const api = createServer((request, response) => {
  calls.push({ path: request.url, method: request.method });
  response.setHeader("Content-Type", "application/json");
  if (mode === "redirect" && request.url === "/gukgam/2026/targets") {
    response.writeHead(307, { Location: "/redirect-leak-canary" }).end();
  } else if (mode === "error") {
    response.writeHead(503).end(JSON.stringify({ error: {
      code: "SERVICE_UNAVAILABLE", message: "Synthetic outage", request_id: "fixture-outage",
    } }));
  } else if (request.url === "/gukgam/2026/targets") {
    response.end(JSON.stringify(mode === "populated"
      ? { ...empty, target_count: 1, committee_count: 1, items: [item] } : empty));
  } else if (request.url === "/people" || request.url === "/organizations") {
    response.end("[]");
  } else if (request.url === `/organizations/${organizationId}`) {
    response.end(JSON.stringify(mode === "annual"
      ? { ...organization, claims: [...organization.claims, annualClaim] } : organization));
  } else if (request.url === `/ontology/organizations/${organizationId}`) {
    response.end(JSON.stringify({ center_node_id: organizationId, nodes: [], edges: [],
      semantics: "READ_ONLY_PROJECTION_FROM_CANONICAL_CLAIM_EVIDENCE", limitations: [] }));
  } else if (request.url === `/organizations/${organizationId}/money?earlier_fiscal_year=2024&later_fiscal_year=2025`) {
    response.writeHead(422).end(JSON.stringify({ error: {
      code: "INSUFFICIENT_ELIGIBLE_INPUTS", message: "Synthetic input shortage", request_id: null,
    } }));
  } else if (request.url === `/sources/${sourceId}`) {
    if (mode === "source_error" || mode === "source_conflict") {
      response.writeHead(mode === "source_error" ? 503 : 409).end(JSON.stringify({ error: {
        code: mode === "source_error" ? "SERVICE_UNAVAILABLE" : "SOURCE_VERSION_CONFLICT",
        message: "Synthetic source failure", request_id: "fixture-source-state",
      } }));
    } else response.end(JSON.stringify(source));
  } else if (request.url === `/people/${portraitId}`) {
    // Public portrait fixture; no operational Person row is read or changed.
    response.end(JSON.stringify({ id: portraitId, canonical_name: "Portrait fixture",
      identity_status: "RESOLVED", claims: [] }));
  } else {
    response.writeHead(404).end(JSON.stringify({ error: {
      code: "PUBLIC_RECORD_NOT_FOUND", message: "Fixture not found", request_id: null,
    } }));
  }
});
await new Promise((resolve, reject) => {
  api.once("error", reject);
  api.listen(0, "127.0.0.1", resolve);
});
const apiOrigin = `http://127.0.0.1:${api.address().port}`;
let worker;
let checks = 0;
const canary = "WORKER_SYNTHETIC_TOKEN_NEVER_IN_CLIENT_1234567890";
try {
  worker = await unstable_dev(fileURLToPath(new URL("dist/server/index.js", root)), {
    config: fileURLToPath(new URL("dist/server/wrangler.json", root)),
    envFiles: [], ip: "127.0.0.1", port: 0, local: true, bundle: false,
    persist: false, inspect: false, logLevel: "error",
    vars: { CIVIC_API_URL: apiOrigin, CIVIC_OPERATOR_ENABLED: "1",
      CIVIC_OPERATOR_API_URL: apiOrigin, CIVIC_OPERATOR_TOKEN: canary },
    experimental: { disableExperimentalWarning: true, disableDevRegistry: true,
      forceLocal: true, watch: false, enableContainers: false },
  });
  async function get(path, options = {}) {
    return worker.fetch(`http://127.0.0.1:${worker.port}${path}`, options);
  }
  const response = await get("/gukgam/2026");
  assert.equal(response.status, 200);
  const html = await response.text();
  assert.match(html, /공개된 피감기관/);
  assert.doesNotMatch(html, /Synthetic outage|WORKER_SYNTHETIC_TOKEN/);
  checks++;

  const assetPaths = [...html.matchAll(/(?:src|href)="([^"?]+\.(?:js|css))"/g)]
    .map((match) => match[1]).filter((path) => path.startsWith("/"));
  assert.ok(assetPaths.some((path) => path.endsWith(".css")));
  assert.ok(assetPaths.some((path) => path.endsWith(".js")));
  for (const path of new Set(assetPaths)) {
    const asset = await get(path);
    assert.equal(asset.status, 200);
    assert.doesNotMatch(await asset.text(), /WORKER_SYNTHETIC_TOKEN|CIVIC_ACCESS_CLIENT_SECRET|CIVIC_OPERATOR_TOKEN/);
  }
  checks++;

  mode = "populated";
  const populated = await get("/gukgam/2026");
  assert.equal(populated.status, 200);
  const populatedHtml = await populated.text();
  assert.ok(populatedHtml.includes("테스트 피감기관"), "Worker must use the configured synthetic API");
  assert.match(populatedHtml, new RegExp(`/organizations/${organizationId}`));
  assert.match(populatedHtml, /Claim/);
  checks++;

  async function readOrganization() {
    const response = await get(`/organizations/${organizationId}`);
    assert.equal(response.status, 200);
    return response.text();
  }
  const organizationHtml = await readOrganization();
  assert.ok(organizationHtml.includes(organization.claims[0].proposition));
  assert.ok(organizationHtml.includes("감사계획 일정") && organizationHtml.includes(item.audit_date));
  assert.ok(organizationHtml.includes(item.committee_name));
  assert.doesNotMatch(organizationHtml, /위원회 정보 없음|일정 정보 없음/);
  assert.doesNotMatch(organizationHtml, /연도 미기재.*?회계연도/);
  for (const id of [proofId, evidenceId, sourceId, snapshotId, observationId]) {
    assert.ok(organizationHtml.includes(id), "Distinct provenance IDs must survive Worker rendering");
  }
  assert.match(organizationHtml, new RegExp(`href="#source-${sourceId}"`));
  assert.match(organizationHtml, new RegExp(`id="source-${sourceId}"`));
  assert.ok(organizationHtml.includes(source.title));
  assert.ok(organizationHtml.includes(source.url));
  assert.match(organizationHtml, /Fulltext.*?NOT_PERMITTED/);
  assert.match(organizationHtml, /INSUFFICIENT_ELIGIBLE_INPUTS/);
  assert.ok(organizationHtml.includes("현재 공개 가능한 임원 연결이 없습니다."));
  assert.doesNotMatch(organizationHtml, /SERVICE_UNAVAILABLE|PUBLIC_RECORD_NOT_FOUND/);
  assert.ok(calls.some((call) => call.path === `/sources/${sourceId}`));
  checks++;

  for (const [state, code] of [["source_error", "SERVICE_UNAVAILABLE"],
    ["source_conflict", "SOURCE_VERSION_CONFLICT"]]) {
    mode = state;
    const html = await readOrganization();
    assert.ok(html.includes(organization.claims[0].proposition));
    assert.ok(html.includes(code));
    assert.match(html, /Source unavailable/);
    assert.doesNotMatch(html, new RegExp(`id="source-${sourceId}"`));
    checks++;
  }
  mode = "populated";
  const recovered = await readOrganization();
  assert.match(recovered, new RegExp(`id="source-${sourceId}"`));
  assert.doesNotMatch(recovered, /SERVICE_UNAVAILABLE|SOURCE_VERSION_CONFLICT/);
  checks++;

  mode = "annual";
  const mixed = await readOrganization();
  assert.ok(mixed.includes(annualClaim.proposition));
  assert.match(mixed, /2025(?:<!-- -->)? 회계연도/);
  assert.ok(mixed.includes("감사계획 일정"));
  assert.doesNotMatch(mixed, /연도 미기재|위원회 정보 없음|일정 정보 없음/);
  checks++;

  mode = "redirect";
  const redirect = await get("/gukgam/2026");
  assert.equal(redirect.status, 200);
  assert.match(await redirect.text(), /SERVICE_UNAVAILABLE/);
  assert.ok(calls.every((call) => call.path !== "/redirect-leak-canary"));
  checks++;

  mode = "error";
  const failure = await get("/gukgam/2026");
  assert.equal(failure.status, 200);
  assert.match(await failure.text(), /SERVICE_UNAVAILABLE/);
  checks++;

  mode = "empty";
  const portrait = await get(`/people/${portraitId}`);
  assert.equal(portrait.status, 200);
  assert.match(await portrait.text(), new RegExp(`/portraits/${portraitId}\\.jpg`));
  const image = await get(`/portraits/${portraitId}.jpg`);
  assert.equal(image.status, 200);
  assert.equal((await image.arrayBuffer()).byteLength, 38558);
  checks++;

  const before = calls.length;
  for (const path of ["/admin", "/admin/review", "/admin/review/actions", "/%61dmin/review"]) {
    assert.equal((await get(path)).status, 404);
  }
  assert.equal((await get("/gukgam/2026", { method: "POST", body: "fixture" })).status, 405);
  assert.equal(calls.length, before);
  assert.ok(calls.every((call) => call.method === "GET" && !call.path.startsWith("/admin")));
  checks++;
  console.log(JSON.stringify({ worker_http_checks: checks, status: "PASS",
    environment: "LOCAL_WORKER_SYNTHETIC_HTTP_ONLY", source_fetches: 0,
    database_writes: 0, browser_verification: "NOT_RUN", deployment: false }));
} finally {
  if (worker) await worker.stop();
  api.closeAllConnections();
  await new Promise((resolve) => api.close(resolve));
}

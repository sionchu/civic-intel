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
const empty = {
  semantics: "PUBLIC_CLAIM_BACKED_GUKGAM_AUDIT_TARGETS_V1",
  coverage: "BOUNDED_INCOMPLETE_PUBLISHED_CLAIMS_ONLY", year: 2026,
  target_count: 0, committee_count: 0, items: [], limitations: [],
};
const item = {
  organization: { id: organizationId, name: "테스트 피감기관" },
  committee_name: "테스트 위원회", audit_date: "2026-10-10", time_text: null,
  venue: null, section: "테스트 계획", page_number: 1, source_published_date: "2026-10-01",
  claim_id: proofId, evidence_ids: [proofId], source_ids: [proofId],
  snapshot_ids: [proofId], observation_ids: [proofId],
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

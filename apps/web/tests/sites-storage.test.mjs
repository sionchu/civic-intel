import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { spawn } from "node:child_process";
import { existsSync, mkdirSync, mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { createServer } from "node:http";
import { tmpdir } from "node:os";
import { join } from "node:path";
import test from "node:test";
import { DatabaseSync } from 'node:sqlite';
import { gzipSync } from 'node:zlib';
import ts from 'typescript';
import { fileURLToPath, pathToFileURL } from "node:url";

import { sizeReport } from "../scripts/bundle-size-report.mjs";
import { personRelationshipPath } from "../app/relationship-path.mjs";

const exporter = fileURLToPath(new URL("../scripts/export-public-projection.mjs", import.meta.url));
const PERSON_A = "a1111111-1111-4111-8111-11111111111a";
const PERSON_B = "22222222-2222-4222-8222-222222222222";
const ORG = "33333333-3333-4333-8333-333333333333";
const SOURCE = "44444444-4444-4444-8444-444444444444";
const RELATIONSHIP_SOURCE = "55555555-5555-4555-8555-555555555555";
const relationshipModuleUrl = new URL('../app/relationship-path.mjs', import.meta.url).href;

function personRelationships(id) {
  const relations = id === PERSON_A ? [{
    id: 'derived-relation', status: 'DERIVED', relation_type: 'SAME_COMPANY_BOARD',
    subject_person_id: PERSON_A, object_person_id: PERSON_B,
    source_claim_ids: ['66666666-6666-4666-8666-666666666666', '77777777-7777-4777-8777-777777777777'],
    source_ids: [SOURCE, RELATIONSHIP_SOURCE],
    evidence_ids: ['88888888-8888-4888-8888-888888888888'],
    temporal_overlap: 'UNKNOWN', rule_id: 'shared_company_board', rule_version: '1.0',
  }] : [];
  return {
    person: { id, name: id === PERSON_A ? '가' : '나' },
    semantics: 'DETERMINISTIC_READ_TIME_PROJECTION_FROM_PUBLISHED_CLAIMS',
    ruleset_version: '1.0', affiliations: [], career_transitions: [],
    groups: relations.length ? [{ via: { kind: 'COMPANY', label: '기관' }, relations, relation_count: 1 }] : [],
    relation_count: relations.length, limitations: [],
  };
}

function vote(index) {
  return { id: `v${index}`, details: { action: "PLENARY_ROLL_CALL_VOTE" } };
}

function fakeApi(overrides = {}) {
  const person = (id, name, entries = [vote(1)]) => ({
    id, canonical_name: name, identity_status: "RESOLVED", claims: [{ source_ids: [SOURCE] }],
    profile: { sections: [{ key: "decision_episodes", entries }] },
  });
  const routes = {
    "/ready": { status: "ready" },
    "/people": [
      { id: PERSON_A, canonical_name: "가", identity_status: "RESOLVED" },
      { id: PERSON_B, canonical_name: "나", identity_status: "RESOLVED" },
    ],
    "/organizations": [{ id: ORG, canonical_name: "기관" }],
    "/gukgam/2026/targets": { target_count: 0 },
    "/gukgam/2026/committees": { committee_count: 0 },
    "/gukgam/2026/witnesses": { items: [] },
    [`/people/${PERSON_A}`]: person(PERSON_A, "가"),
    [`/people/${PERSON_B}`]: person(PERSON_B, "나"),
    [`/ontology/people/${PERSON_A}`]: { nodes: [] },
    [`/ontology/people/${PERSON_B}`]: { nodes: [] },
    [personRelationshipPath(PERSON_A)]: personRelationships(PERSON_A),
    [personRelationshipPath(PERSON_B)]: personRelationships(PERSON_B),
    [`/organizations/${ORG}`]: { id: ORG },
    [`/ontology/organizations/${ORG}`]: { nodes: [] },
    [`/sources/${SOURCE}`]: { id: SOURCE, title: "출처" },
    [`/sources/${RELATIONSHIP_SOURCE}`]: { id: RELATIONSHIP_SOURCE, title: "관계에만 연결된 출처" },
    ...overrides,
  };
  return createServer((request, response) => {
    const body = routes[request.url];
    if (typeof body === "number") {
      response.writeHead(body, { "content-type": "application/json" });
      response.end(JSON.stringify({ error: { code: "INVALID_INPUT" } }));
    } else if (body === undefined) {
      response.writeHead(422, { "content-type": "application/json" });
      response.end(JSON.stringify({ error: { code: "INVALID_INPUT" } }));
    } else {
      response.writeHead(200, { "content-type": "application/json" });
      response.end(JSON.stringify(body));
    }
  });
}

async function exportWith(overrides = {}) {
  const server = fakeApi(overrides);
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  const out = mkdtempSync(join(tmpdir(), "projection-"));
  try {
    const child = spawn(process.execPath, [exporter, "--api", `http://127.0.0.1:${server.address().port}`, "--out", out]);
    let output = "";
    child.stdout.on("data", (chunk) => { output += chunk; });
    child.stderr.on("data", (chunk) => { output += chunk; });
    const code = await new Promise((resolve) => child.on("close", resolve));
    return { code, output, out };
  } finally {
    server.close();
  }
}

test("projection export is deterministic and keeps public 4xx answers", async () => {
  const first = await exportWith();
  const second = await exportWith();
  assert.equal(first.code, 0, first.output);
  assert.equal(second.code, 0, second.output);
  const [a, b] = [first, second].map(({ out }) => JSON.parse(readFileSync(join(out, "projection-manifest.json"), "utf8")));
  assert.equal(a.semantic_sha256, b.semantic_sha256);
  assert.equal(a.snapshot_id, b.snapshot_id);
  assert.deepEqual(a.paths, b.paths);
  assert.equal(a.semantics, "REPLACEABLE_PUBLIC_READ_SNAPSHOT_NOT_SSOT");
  assert.equal(a.counts.public_people, 2);
  // The counterpart's source is reachable only through the relationship response.
  assert.equal(a.counts.sources, 2);
  assert.ok(a.paths.some((row) => row.path === `/sources/${SOURCE}` && row.status === 200));
  assert.equal(a.paths.filter((row) => row.path === `/sources/${RELATIONSHIP_SOURCE}` && row.status === 200).length, 1);
  for (const id of [PERSON_A, PERSON_B]) {
    assert.ok(a.paths.some((row) => row.path === personRelationshipPath(id) && row.status === 200));
  }
  // The org money comparison answers 422 in this fixture; it is stored as that answer.
  assert.equal(a.counts.client_error_paths, 1);
  const loadSql = (out) => readFileSync(join(out, "load.sql"), "utf8").split("\n").slice(2).join("\n");
  assert.equal(loadSql(first.out), loadSql(second.out));
  assert.match(readFileSync(join(first.out, "load.sql"), "utf8"), /ON CONFLICT DO NOTHING;/);
  const activate = readFileSync(join(first.out, "activate.sql"), "utf8");
  assert.match(activate, /status = 'STAGED'/);
  assert.match(activate, new RegExp(`= ${a.counts.parts} AND`));
  assert.match(readFileSync(join(first.out, "rollback.sql"), "utf8"), /snapshot_id = .* AND status = 'PREVIOUS'/);
});

test("projection export fails closed on the public boundary", async () => {
  const cases = [
    [{ "/people": [{ id: PERSON_A, canonical_name: "가", identity_status: "REVIEW" }] }, /not RESOLVED/],
    [{ [`/people/${PERSON_A}`]: { id: PERSON_A, identity_status: "RESOLVED", profile: { sections: [{ entries: Array.from({ length: 11 }, (_, i) => vote(i)) }] } } }, /11 plenary votes \(max 10\)/],
    [{ [`/organizations/${ORG}`]: { id: ORG, note: "raw_payload" } }, /forbidden token "raw_payload"/],
    [{ [`/organizations/${ORG}`]: { id: ORG, contact: "someone@example.com" } }, /email-like text/],
    [{ [`/people/${PERSON_B}`]: 503 }, /returned HTTP 503/],
    [{ [`/people/${PERSON_B}`]: 404 }, /returned HTTP 404/],
    [{ [`/organizations/${ORG}`]: 404 }, /returned HTTP 404/],
    [{ [`/sources/${SOURCE}`]: 404 }, /returned HTTP 404/],
    [{ [personRelationshipPath(PERSON_A)]: 503 }, /returned HTTP 503/],
    [{ [personRelationshipPath(PERSON_B)]: 404 }, /returned HTTP 404/],
    [{ [`/sources/${RELATIONSHIP_SOURCE}`]: 404 }, /returned HTTP 404/],
    [{ [`/ontology/people/${PERSON_A}`]: 401 }, /returned HTTP 401/],
    [{ [`/organizations/${ORG}`]: 403 }, /returned HTTP 403/],
    [{ [`/organizations/${ORG}/money?earlier_fiscal_year=2024&later_fiscal_year=2025`]: 429 }, /returned HTTP 429/],
  ];
  for (const [overrides, message] of cases) {
    const result = await exportWith(overrides);
    assert.notEqual(result.code, 0);
    assert.match(result.output, message);
  }
});

test('snapshot SQL validates exact data before atomic activation and retry-safe rollback', async () => {
  const a = await exportWith();
  const b = await exportWith({ [`/sources/${SOURCE}`]: { id: SOURCE, title: '변경된 출처' } });
  for (const result of [a, b]) assert.equal(result.code, 0, result.output);
  const manifest = (result) => JSON.parse(readFileSync(join(result.out, 'projection-manifest.json'), 'utf8'));
  const sql = (result, name) => readFileSync(join(result.out, `${name}.sql`), 'utf8');
  const db = new DatabaseSync(':memory:');
  db.exec(readFileSync(new URL('../sites-worker/drizzle/0000_public_projection.sql', import.meta.url), 'utf8'));
  const statuses = () => db.prepare('SELECT snapshot_id, status FROM snapshot_meta ORDER BY snapshot_id').all();
  const active = () => db.prepare("SELECT snapshot_id FROM snapshot_meta WHERE status = 'ACTIVE'").get()?.snapshot_id;
  try {
    db.exec(sql(a, 'load'));
    assert.equal(active(), undefined);
    db.exec(sql(a, 'activate'));
    assert.equal(active(), manifest(a).snapshot_id);
    const before = statuses();
    db.exec(sql(a, 'load')); db.exec(sql(a, 'activate'));
    assert.deepEqual(statuses(), before);
    db.exec(sql(b, 'load'));
    // Same count, wrong path; activation must fail before changing the current ACTIVE.
    db.prepare('UPDATE public_read SET path = ? WHERE snapshot_id = ? AND path = ?').run('/unexpected', manifest(b).snapshot_id, `/sources/${SOURCE}`);
    assert.throws(() => db.exec(sql(b, 'activate')), /malformed JSON/);
    assert.equal(active(), manifest(a).snapshot_id);
    db.prepare('DELETE FROM public_read WHERE snapshot_id = ? AND path = ?').run(manifest(b).snapshot_id, '/unexpected');
    db.exec(sql(b, 'load'));
    db.prepare('UPDATE public_read SET body_gzip = ? WHERE snapshot_id = ? AND path = ?').run(gzipSync(Buffer.from('{}')), manifest(b).snapshot_id, `/sources/${SOURCE}`);
    assert.throws(() => db.exec(sql(b, 'activate')), /malformed JSON/);
    assert.equal(active(), manifest(a).snapshot_id);
    db.prepare('DELETE FROM public_read WHERE snapshot_id = ? AND path = ?').run(manifest(b).snapshot_id, `/sources/${SOURCE}`);
    db.exec(sql(b, 'load')); db.exec(sql(b, 'activate'));
    assert.equal(active(), manifest(b).snapshot_id);
    db.exec(sql(a, 'rollback'));
    assert.equal(active(), manifest(a).snapshot_id);
    const rolledBack = statuses();
    db.exec(sql(a, 'rollback'));
    assert.deepEqual(statuses(), rolledBack);
    // Complete activation SQL queries (including hex bytes) stay under D1's 100 KB limit.
    for (const line of sql(b, 'activate').split('\n')) assert.ok(Buffer.byteLength(line) < 100_000);
  } finally { db.close(); }
});

test('D1 reader checks manifest/hash/parts and distinguishes lost rows from unknown UUIDs', async () => {
  const result = await exportWith();
  assert.equal(result.code, 0, result.output);
  const db = new DatabaseSync(':memory:');
  db.exec(readFileSync(new URL('../sites-worker/drizzle/0000_public_projection.sql', import.meta.url), 'utf8'));
  for (const name of ['load', 'activate']) db.exec(readFileSync(join(result.out, `${name}.sql`), 'utf8'));
  const binding = { prepare(query) {
    let values = [];
    return { bind(...args) { values = args; return this; }, async all() { return { results: db.prepare(query).all(...values) }; } };
  } };
  globalThis.__projectionTestEnv = { DB: binding };
  globalThis.__projectionTestGeneration = 0;
  const source = readFileSync(new URL('../sites-worker/public-read.d1.ts', import.meta.url), 'utf8')
    .replace('import { env } from "cloudflare:workers";', 'const env = globalThis.__projectionTestEnv;')
    .replace('import { cacheForRequest } from "vinext/cache";', 'const cacheForRequest = (fn) => { let value, generation = -1; return () => { if (generation !== globalThis.__projectionTestGeneration) { generation = globalThis.__projectionTestGeneration; value = fn(); } return value; }; };')
    .replace('"./relationship-path.mjs"', JSON.stringify(relationshipModuleUrl));
  const js = ts.transpileModule(source, { compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ESNext } }).outputText;
  const reader = await import(`data:text/javascript;base64,${Buffer.from(js).toString('base64')}`);
  try {
    assert.equal((await reader.readPublic(`/people/${PERSON_A}`)).body.id, PERSON_A);
    for (const id of [PERSON_A.toUpperCase(), PERSON_A.replaceAll('-', ''), `{${PERSON_A}}`, `urn:uuid:${PERSON_A}`]) {
      assert.equal((await reader.readPublic(`/people/${id}`)).body.id, PERSON_A);
    }
    for (const id of [PERSON_A, PERSON_A.toUpperCase(), PERSON_A.replaceAll('-', ''), `{${PERSON_A}}`, encodeURIComponent(`{${PERSON_A}}`), `urn:uuid:${PERSON_A}`]) {
      for (const query of ['include_candidates=false&limit_per_via=3', 'limit_per_via=3&include_candidates=false']) {
        const relationship = await reader.readPublic(`/relationships/people/${id}?${query}`);
        assert.equal(relationship.status, 200);
        assert.deepEqual(relationship.body, personRelationships(PERSON_A));
      }
    }
    assert.deepEqual((await reader.readPublic(personRelationshipPath(PERSON_B))).body, personRelationships(PERSON_B));
    assert.equal((await reader.readPublic(`/sources/${RELATIONSHIP_SOURCE}`)).body.title, '관계에만 연결된 출처');
    for (const query of [
      '', '?include_candidates=false', '?limit_per_via=3',
      '?include_candidates=true&limit_per_via=3', '?include_candidates=false&limit_per_via=50',
      '?include_candidates=false&limit_per_via=3&unknown=value',
      '?include_candidates=false&include_candidates=false&limit_per_via=3',
      '?include_candidates=false&limit_per_via=3&limit_per_via=3',
    ]) {
      const invalid = await reader.readPublic(`/relationships/people/${PERSON_A}${query}`);
      assert.equal(invalid.status, 422, query);
      assert.equal(invalid.body.error.code, 'INVALID_INPUT', query);
    }
    for (const id of ['not-a-uuid', '%invalid']) {
      assert.equal((await reader.readPublic(personRelationshipPath(id))).status, 422);
    }
    for (const prefix of ['/people', '/organizations', '/sources', '/ontology/people', '/ontology/organizations']) {
      const invalid = await reader.readPublic(`${prefix}/not-a-uuid`);
      assert.equal(invalid.status, 422);
      assert.equal(invalid.body.error.code, 'INVALID_INPUT');
    }
    assert.match(await reader.readSnapshotAt(), /KST$/);
    assert.equal((await reader.readPublic('/people/aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa')).status, 404);
    const unknownRelationship = await reader.readPublic(personRelationshipPath('aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa'));
    assert.equal(unknownRelationship.status, 404);
    assert.equal(unknownRelationship.body, null);
    db.prepare('DELETE FROM public_read WHERE path = ?').run(personRelationshipPath(PERSON_B));
    globalThis.__projectionTestGeneration++;
    await assert.rejects(reader.readPublic(personRelationshipPath(PERSON_B)), /missing exported/);
    await assert.rejects(reader.readPublic('/admin/review'), /outside the exported/);
    db.prepare('UPDATE public_read SET body_gzip = ? WHERE path = ?').run(gzipSync(Buffer.from('{}')), `/people/${PERSON_A}`);
    globalThis.__projectionTestGeneration++;
    await assert.rejects(reader.readPublic(`/people/${PERSON_A}`), /corrupt public projection/);
    db.prepare('DELETE FROM public_read WHERE path = ?').run(`/sources/${SOURCE}`);
    globalThis.__projectionTestGeneration++;
    await assert.rejects(reader.readPublic(`/sources/${SOURCE}`), /missing exported/);
  } finally { db.close(); delete globalThis.__projectionTestEnv; delete globalThis.__projectionTestGeneration; }
});

const vinextShims = new URL('../.sites-worker-build/node_modules/vinext/dist/shims/', import.meta.url);
test('installed Vinext cache pins metadata and reads to one snapshot per request', {
  skip: !existsSync(new URL('cache-for-request.js', vinextShims)),
}, async () => {
  const a = await exportWith();
  const b = await exportWith({ [`/sources/${SOURCE}`]: { id: SOURCE, title: '변경된 출처' } });
  for (const result of [a, b]) assert.equal(result.code, 0, result.output);
  const db = new DatabaseSync(':memory:');
  db.exec(readFileSync(new URL('../sites-worker/drizzle/0000_public_projection.sql', import.meta.url), 'utf8'));
  const sql = (result, name) => readFileSync(join(result.out, `${name}.sql`), 'utf8');
  db.exec(sql(a, 'load')); db.exec(sql(a, 'activate')); db.exec(sql(b, 'load'));
  const partReads = new Map();
  const binding = { prepare(query) {
    let values = [];
    return { bind(...args) { values = args; return this; }, async all() {
      if (query.includes('FROM public_read')) partReads.set(values[1], (partReads.get(values[1]) ?? 0) + 1);
      return { results: db.prepare(query).all(...values) };
    } };
  } };
  globalThis.__projectionRequestEnv = { DB: binding };
  const source = readFileSync(new URL('../sites-worker/public-read.d1.ts', import.meta.url), 'utf8')
    .replace('import { env } from "cloudflare:workers";', 'const env = globalThis.__projectionRequestEnv;')
    .replace('"vinext/cache"', JSON.stringify(pathToFileURL(fileURLToPath(new URL('cache-for-request.js', vinextShims))).href))
    .replace('"./relationship-path.mjs"', JSON.stringify(relationshipModuleUrl));
  const js = ts.transpileModule(source, { compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ESNext } }).outputText;
  const reader = await import(`data:text/javascript;base64,${Buffer.from(js).toString('base64')}`);
  const { createRequestContext, runWithRequestContext } = await import(new URL('unified-request-context.js', vinextShims));
  try {
    await runWithRequestContext(createRequestContext(), async () => {
      const before = await reader.readSnapshotAt();
      db.exec(sql(b, 'activate'));
      assert.equal(await reader.readSnapshotAt(), before);
      assert.equal((await reader.readPublic(`/sources/${SOURCE}`)).body.title, '출처');
      const [first, second] = await Promise.all([
        reader.readPublic(`/sources/${SOURCE}`), reader.readPublic(`/sources/${SOURCE.toUpperCase()}`),
      ]);
      assert.equal(partReads.get(`/sources/${SOURCE}`), 1, 'one read/decode for repeated normalized path in metadata/page context');
      assert.strictEqual(first.body, second.body);
      assert.equal((await reader.readPublic(`/sources/${RELATIONSHIP_SOURCE}`)).body.title, '관계에만 연결된 출처');
      assert.equal(partReads.get(`/sources/${RELATIONSHIP_SOURCE}`), 1, 'different paths do not share DTOs');
    });
    await runWithRequestContext(createRequestContext(), async () => {
      assert.equal((await reader.readPublic(`/sources/${SOURCE}`)).body.title, '변경된 출처');
      assert.equal(partReads.get(`/sources/${SOURCE}`), 2, 'next request reads the newly ACTIVE snapshot');
    });
    const path = `/sources/${SOURCE}`;
    const stored = db.prepare("SELECT snapshot_id, body_gzip FROM public_read WHERE path = ? AND snapshot_id = (SELECT snapshot_id FROM snapshot_meta WHERE status = 'ACTIVE')").get(path);
    db.prepare('UPDATE public_read SET body_gzip = ? WHERE snapshot_id = ? AND path = ?').run(gzipSync(Buffer.from('{}')), stored.snapshot_id, path);
    await runWithRequestContext(createRequestContext(), async () => {
      const failures = await Promise.allSettled([reader.readPublic(path), reader.readPublic(path)]);
      assert.ok(failures.every((result) => result.status === 'rejected'));
      assert.equal(partReads.get(path), 3, 'concurrent failed decode is shared');
      db.prepare('UPDATE public_read SET body_gzip = ? WHERE snapshot_id = ? AND path = ?').run(stored.body_gzip, stored.snapshot_id, path);
      assert.equal((await reader.readPublic(path)).body.title, '변경된 출처');
      assert.equal(partReads.get(path), 4, 'failed promise is evicted for retry');
    });
  } finally { db.close(); delete globalThis.__projectionRequestEnv; }
});

test("bundle size report attributes bytes per category and per Person route", () => {
  const out = mkdtempSync(join(tmpdir(), "bundle-"));
  for (const [path, bytes] of [
    ["index.html", 100], [`people/${PERSON_A}/index.html`, 300], [`people/${PERSON_A}/index.txt`, 200],
    [`people/${PERSON_B}/index.html`, 100], ["_next/static/a.js", 50], ["portraits/a.jpg", 10],
  ]) {
    mkdirSync(join(out, path, ".."), { recursive: true });
    writeFileSync(join(out, path), "x".repeat(bytes));
  }
  const report = sizeReport(out, { publicPeople: 2, publicOrganizations: 0 });
  assert.equal(report.bundle.total_bytes, 760);
  assert.equal(report.bundle.budget_state, "GREEN");
  assert.deepEqual(
    [report.size_by_category.html, report.size_by_category.rsc_txt, report.size_by_category.javascript, report.size_by_category.images],
    [500, 200, 50, 10],
  );
  assert.equal(report.density.person_detail_bytes, 600);
  assert.equal(report.density.bytes_per_public_person, 300);
  assert.equal(report.largest_files[0].path, `people/${PERSON_A}/index.html`);
});

test("D1 transport replays exported responses and never decides publication", async () => {
  const transport = readFileSync(new URL("../sites-worker/public-read.d1.ts", import.meta.url), "utf8");
  const schema = readFileSync(new URL("../sites-worker/db/schema.ts", import.meta.url), "utf8");
  assert.match(transport, /status = 'ACTIVE'/);
  assert.match(transport, /expected one ACTIVE snapshot/);
  assert.match(transport, /outside the exported public projection/);
  const code = transport.split("\n").filter((line) => !line.trimStart().startsWith("//")).join("\n");
  assert.doesNotMatch(code, /identity_status|publication_status|epistemic_status|SourcePolicy/);
  assert.match(schema, /REPLACEABLE_PUBLIC_READ_SNAPSHOT_NOT_SSOT/);
  // Both transports expose the same function the data layer calls.
  const http = readFileSync(new URL("../app/public-read.ts", import.meta.url), "utf8");
  for (const source of [http, transport]) assert.match(source, /export async function readPublic\(\s*path: string,/);
});

test('source batch preserves ordered closure with bounded D1 queries, pins and failure eviction', async () => {
 const ids = Array.from({length:1936}, (_,i) => `00000000-0000-4000-8000-${i.toString(16).padStart(12,'0')}`);
 const paths = ids.map(id => `/sources/${id}`);
 const bodies = new Map(paths.map((path,i) => [path, Buffer.from(JSON.stringify({id:ids[i],title:'합성 출처'}))]));
 const scope = {patterns:['^/sources/[0-9a-f-]{36}$'],paths:Object.fromEntries([...bodies].map(([path,b]) => [path,[200,createHash('sha256').update(b).digest('hex')]]))};
 let queries=0, active=0, maxActive=0, maxBindings=0, snapshotReads=0, corrupt=null, missing=null, ordinal=null, badHash=null, pinned='pinned';
 globalThis.__projectionTestGeneration = 0;
 globalThis.__projectionTestEnv = {DB:{prepare(sql){let values=[];return {bind(...v){values=v;maxBindings=Math.max(maxBindings,v.length);return this;},async all(){queries++;if(sql.includes('FROM snapshot_meta')){snapshotReads++;return {results:[{snapshot_id:pinned,projection_schema_version:2,scope_json:JSON.stringify(scope)}]};} assert.equal(values[0],pinned);active++;maxActive=Math.max(maxActive,active);await new Promise(resolve=>setTimeout(resolve,1));const selected=values.slice(1).filter(path=>path!==missing && bodies.has(path));const results=selected.flatMap(path=>{const packed=gzipSync(path===corrupt?Buffer.from('{}'):bodies.get(path));const chunks=path===paths[1]?[packed.subarray(0,8),packed.subarray(8)]:[packed];return chunks.map((chunk,index)=>({path,part:path===ordinal?1:index,status:200,content_sha256:path===badHash?'b'.repeat(64):scope.paths[path][1],body_gzip:chunk}));});active--;return {results};}};}}};
 const source=readFileSync(new URL('../sites-worker/public-read.d1.ts',import.meta.url),'utf8').replace('import { env } from "cloudflare:workers";','const env = globalThis.__projectionTestEnv;').replace('import { cacheForRequest } from "vinext/cache";','const cacheForRequest = fn => { let value, generation=-1; return () => {if(generation!==globalThis.__projectionTestGeneration){generation=globalThis.__projectionTestGeneration;value=fn();}return value;};};').replace('"./relationship-path.mjs"',JSON.stringify(relationshipModuleUrl));
 const js=ts.transpileModule(source,{compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.ESNext}}).outputText;
 const reader=await import(`data:text/javascript;base64,${Buffer.from(js).toString('base64')}`);
 const response=await reader.readPublicSources(paths);
 assert.deepEqual(response.map(r=>r.body.id),ids);
 assert.equal(queries,21);assert.equal(snapshotReads,1);assert.equal(maxBindings,100);assert.ok(maxActive<=6);
 await reader.readPublicSources([paths[1000],paths[0],paths[1000]]);assert.equal(queries,21);
 assert.equal((await reader.readPublic(paths[0])).body.id,ids[0]);assert.equal(queries,21);
 for(const [kind,pattern] of [['missing',/missing exported/],['corrupt',/corrupt public projection/],['ordinal',/inconsistent public projection/],['badHash',/inconsistent public projection/]]){
  globalThis.__projectionTestGeneration++;
  missing=kind==='missing'?paths[0]:null;corrupt=kind==='corrupt'?paths[0]:null;ordinal=kind==='ordinal'?paths[0]:null;badHash=kind==='badHash'?paths[0]:null;
  const partial=await reader.readPublicSources([paths[0],paths[1]]);
  assert.equal(partial[0].status,503);assert.equal(partial[1].status,200);assert.equal(partial[1].body.id,ids[1]);
  await assert.rejects(reader.readPublic(paths[0]),pattern);
  missing=corrupt=ordinal=badHash=null;
  assert.equal((await reader.readPublicSources([paths[0]]))[0].body.id,ids[0]);
 }
 globalThis.__projectionTestGeneration++;pinned='pinned-next';
 await reader.readPublicSources([paths[0]]);assert.equal(snapshotReads,6);
 const outside='/sources/aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa';
 assert.equal((await reader.readPublicSources([outside]))[0].status,404);
 globalThis.__projectionTestEnv.DB=undefined;globalThis.__projectionTestGeneration++;
 const unavailable=await reader.readPublicSources([paths[0],paths[1]]);assert.deepEqual(unavailable.map(result=>result.status),[503,503]);assert.equal(snapshotReads,6);
 delete globalThis.__projectionTestEnv;
});

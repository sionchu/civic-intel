import { test } from 'node:test';
import assert from 'node:assert/strict';
import { DatabaseSync } from 'node:sqlite';
import { readFileSync } from 'node:fs';
import { gzipSync } from 'node:zlib';
import { snapshotProtocol, digest } from '../scripts/snapshot-protocol.mjs';
import { executeSnapshotOperation } from '../sites-worker/snapshot-operations.mjs';
import { SCOPES } from '../scripts/snapshot-scopes.mjs';
import { handleSnapshotWriter } from '../sites-worker/snapshot-writer.mjs';
import { FORBIDDEN_TOKENS, forbiddenToken, EMAIL } from '../scripts/public-boundary.mjs';

function adapter(database) {
  return { prepare(sql) { return { bind(...values) {
    const statement = database.prepare(sql);
    return { sql, values, async first() { return statement.get(...values) ?? null; },
      async all() { return { results: statement.all(...values) }; } };
  } }; }, async batch(statements) {
    database.exec('BEGIN');
    try {
      const results = statements.map(({ sql, values }) => ({ results: database.prepare(sql).all(...values) }));
      database.exec('COMMIT'); return results;
    } catch (error) { database.exec('ROLLBACK'); throw error; }
  } };
}
function fixture(body = { items: [] }) {
  const json = Buffer.from(JSON.stringify(body)); const chunk = gzipSync(json);
  const scopes = SCOPES;
  const semantic = { semantics: 'REPLACEABLE_PUBLIC_READ_SNAPSHOT_NOT_SSOT', projection_schema_version: 2,
    scopes, rows: [['/people', 200, digest(json)]] };
  const semanticSha = digest(JSON.stringify(semantic));
  const manifest = { snapshot_id: `ps-${semanticSha.slice(0,16)}`, semantic_sha256: semanticSha,
    projection_schema_version: 2, scopes, generated_at: '2026-10-08T00:00:00.000Z', generated_at_kst: '2026-10-08 09:00 KST', git_commit: 'a'.repeat(40),
    counts: { paths: 1, parts: 1, public_people: 0, public_organizations: 0 },
    paths: [{ path: '/people', status: 200, sha256: digest(json), bytes: json.length, gzip_bytes: chunk.length }] };
  const protocol = snapshotProtocol(manifest, [{ path: '/people', part: 0, chunk }]);
  const base = { version: 1, snapshot_id: protocol.snapshot_id, manifest_sha256: protocol.manifest_sha256 };
  const metadata = { projection_schema_version: 2, generated_at: manifest.generated_at, generated_at_kst: manifest.generated_at_kst,
    git_commit: manifest.git_commit, path_count: 1, part_count: 1, public_people: 0, public_organizations: 0 };
  return { base, protocol, metadata, chunk };
}
function setup() {
  const database = new DatabaseSync(':memory:');
  database.exec(readFileSync(new URL('../sites-worker/drizzle/0000_public_projection.sql', import.meta.url), 'utf8').replaceAll('--> statement-breakpoint',''));
  database.exec(readFileSync(new URL('../sites-worker/drizzle/0001_snapshot_writer.sql', import.meta.url), 'utf8').replaceAll('--> statement-breakpoint',''));
  return { database, db: adapter(database) };
}
async function stage(db, f) {
  const call = (op, fields = {}) => executeSnapshotOperation({ ...f.base, op, ...fields }, db);
  await call('begin', { metadata: f.metadata });
  await call('metadata', { offset: 0, chunk: f.protocol.scope_json });
  await call('manifest');
  await call('part', { ordinal: 0, path: '/people', part: 0, body_base64: f.chunk.toString('base64') });
  await call('seal'); await call('validate', { ordinal: 0 });
  return call;
}
async function restore(call, expected) {
  const prepared = await call('restore', { ...expected, mode: 'prepare' });
  if (prepared.status === 'ACTIVE') return prepared;
  await call('restore', { ...expected, mode: 'validate', ordinal: 0 });
  return call('restore', { ...expected, mode: 'activate' });
}
test('exact retry, immutable seal, validation and pointer CAS/restore round trip', async () => {
  const { database, db } = setup();
  const a = fixture({ items: ['a'] }), b = fixture({ items: ['b'] });
  const first = await stage(db, a);
  await first('activate', { expected_active: null, expected_epoch: 0 });
  await first('activate', { expected_active: null, expected_epoch: 0 });
  await assert.rejects(first('activate', { expected_active: b.base.snapshot_id, expected_epoch: 0 }));
  const second = await stage(db, b);
  await second('activate', { expected_active: a.base.snapshot_id, expected_epoch: 1 });
  await assert.rejects(first('activate', { expected_active: null, expected_epoch: 0 }));
  await restore(first, { expected_active: b.base.snapshot_id, expected_epoch: 2 });
  await restore(first, { expected_active: b.base.snapshot_id, expected_epoch: 2 });
  assert.equal(database.prepare("SELECT snapshot_id FROM snapshot_meta WHERE status='ACTIVE'").get().snapshot_id, a.base.snapshot_id);
  assert.equal(database.prepare('SELECT COUNT(*) AS count FROM public_read').get().count, 2);
  await assert.rejects(first('metadata', { offset: Buffer.byteLength(a.protocol.scope_json), chunk: 'x' }));
  assert.equal((await first('part', { ordinal: 0, path: '/people', part: 0, body_base64: a.chunk.toString('base64') })).cursor, 1);
  await assert.rejects(first('part', { ordinal: 0, path: '/people', part: 0, body_base64: b.chunk.toString('base64') }));
  database.close();
});
test('corrupt response rolls back validation cursor and cannot activate', async () => {
  const { database, db } = setup(); const f = fixture();
  const call = (op, fields = {}) => executeSnapshotOperation({ ...f.base, op, ...fields }, db);
  await call('begin', { metadata: f.metadata }); await call('metadata', { offset: 0, chunk: f.protocol.scope_json }); await call('manifest');
  await assert.rejects(call('seal'));
  await call('part', { ordinal: 0, path: '/people', part: 0, body_base64: f.chunk.toString('base64') }); await call('seal');
  database.prepare('UPDATE public_read SET body_gzip=?').run(new Uint8Array([1]));
  await assert.rejects(call('validate', { ordinal: 0 }));
  await assert.rejects(call('activate', { expected_active: null, expected_epoch: 0 }));
  assert.equal((await call('state')).validation_cursor, 0);
  database.close();
});
test('empty and populated D1 migration upgrade/downgrade/upgrade retains reader bytes', () => {
  for (const populated of [false, true]) {
    const database = new DatabaseSync(':memory:');
    database.exec(readFileSync(new URL('../sites-worker/drizzle/0000_public_projection.sql', import.meta.url), 'utf8').replaceAll('--> statement-breakpoint',''));
    if (populated) {
      database.prepare(`INSERT INTO snapshot_meta VALUES(?, 'ACTIVE',2,?,?,?,?,1,1,0,0)`).run('ps-0123456789abcdef', '2026-10-08T00:00:00Z', '2026-10-08 09:00 KST', 'a'.repeat(40), '{"patterns":[],"paths":{}}');
      database.prepare('INSERT INTO public_read VALUES(?,?,?,?,?,?)').run('ps-0123456789abcdef', '/people', 0, 200, 'b'.repeat(64), new Uint8Array([1,2,3]));
    }
    const before = JSON.stringify(database.prepare('SELECT * FROM public_read').all());
    const forward = readFileSync(new URL('../sites-worker/drizzle/0001_snapshot_writer.sql', import.meta.url), 'utf8').replaceAll('--> statement-breakpoint','');
    database.exec(forward);
    database.exec(readFileSync(new URL('../sites-worker/drizzle/rollback_snapshot_writer.sql', import.meta.url), 'utf8'));
    database.exec(forward);
    assert.equal(JSON.stringify(database.prepare('SELECT * FROM public_read').all()), before);
    assert.equal(database.prepare("SELECT COUNT(*) AS count FROM snapshot_meta WHERE status='ACTIVE'").get().count, Number(populated));
    database.close();
  }
});
test('authenticated current/previous pins permit exact restore but never previous uploads', async () => {
  const { database, db } = setup();
  const a = fixture({ items: ['approved-a'] }), b = fixture({ items: ['approved-b'] });
  const secret = 'synthetic-authenticated-lifecycle-fixture-secret';
  let environment = { DB: db, CIVIC_SNAPSHOT_WRITER_SECRET: secret, CIVIC_SNAPSHOT_MANIFEST_SHA256: a.base.manifest_sha256 };
  async function call(f, op, fields = {}) {
    return handleSnapshotWriter(new Request('https://example.test/api/maintenance/snapshot', { method: 'POST',
      headers: { authorization: `Bearer ${secret}`, 'content-type': 'application/json' },
      body: JSON.stringify({ ...f.base, op, ...fields }) }), environment, executeSnapshotOperation);
  }
  async function authenticatedStage(f) {
    for (const [op, fields] of [ ['begin',{metadata:f.metadata}], ['metadata',{offset:0,chunk:f.protocol.scope_json}],
      ['manifest',{}], ['part',{ordinal:0,path:'/people',part:0,body_base64:f.chunk.toString('base64')}],
      ['seal',{}], ['validate',{ordinal:0}] ]) assert.equal((await call(f,op,fields)).status,200);
  }
  async function authenticatedRestore(f, expected) {
    const prepared = await call(f,'restore',{...expected,mode:'prepare'});
    assert.equal(prepared.status,200);
    if ((await prepared.json()).status === 'ACTIVE') return;
    assert.equal((await call(f,'restore',{...expected,mode:'validate',ordinal:0})).status,200);
    assert.equal((await call(f,'restore',{...expected,mode:'activate'})).status,200);
  }
  await authenticatedStage(a);
  assert.equal((await call(a,'activate',{expected_active:null,expected_epoch:0})).status,200);
  environment = { ...environment, CIVIC_SNAPSHOT_MANIFEST_SHA256:b.base.manifest_sha256, CIVIC_SNAPSHOT_PREVIOUS_MANIFEST_SHA256:a.base.manifest_sha256 };
  for (const op of ['begin','metadata','manifest','part','seal','validate','activate']) assert.equal((await call(a,op)).status,403);
  await authenticatedStage(b);
  assert.equal((await call(b,'activate',{expected_active:a.base.snapshot_id,expected_epoch:1})).status,200);
  await authenticatedRestore(a,{expected_active:b.base.snapshot_id,expected_epoch:2});
  await authenticatedRestore(a,{expected_active:b.base.snapshot_id,expected_epoch:2});
  await authenticatedRestore(b,{expected_active:a.base.snapshot_id,expected_epoch:3});
  assert.equal((await call(a,'restore',{expected_active:b.base.snapshot_id,expected_epoch:2,mode:'activate'})).status,409);
  const unknown = fixture({items:['not-approved']});
  assert.equal((await call(unknown,'restore',{expected_active:b.base.snapshot_id,expected_epoch:4,mode:'activate'})).status,403);
  database.close();
});
test('PREVIOUS restore revalidates bytes and stale final CAS preserves current ACTIVE', async () => {
  const { database, db }=setup();
  const a=fixture({items:['a']}),b=fixture({items:['b']}),c=fixture({items:['c']});
  const first=await stage(db,a);await first('activate',{expected_active:null,expected_epoch:0});
  const second=await stage(db,b);await second('activate',{expected_active:a.base.snapshot_id,expected_epoch:1});
  const expected={expected_active:b.base.snapshot_id,expected_epoch:2};
  await first('restore',{...expected,mode:'prepare'});
  await first('restore',{...expected,mode:'prepare'});
  database.prepare('UPDATE public_read SET body_gzip=? WHERE snapshot_id=?').run(new Uint8Array([1]),a.base.snapshot_id);
  await assert.rejects(first('restore',{...expected,mode:'validate',ordinal:0}));
  await assert.rejects(first('restore',{...expected,mode:'activate'}));
  assert.equal((await first('state')).validation_cursor,0);
  assert.equal(database.prepare("SELECT snapshot_id FROM snapshot_meta WHERE status='ACTIVE'").get().snapshot_id,b.base.snapshot_id);
  // Fixture-only physical repair lets the test isolate the later pointer race.
  database.prepare('UPDATE public_read SET body_gzip=? WHERE snapshot_id=?').run(a.chunk,a.base.snapshot_id);
  await first('restore',{...expected,mode:'validate',ordinal:0});
  const third=await stage(db,c);await third('activate',{expected_active:b.base.snapshot_id,expected_epoch:2});
  await assert.rejects(first('restore',{...expected,mode:'activate'}));
  assert.equal(database.prepare("SELECT snapshot_id FROM snapshot_meta WHERE status='ACTIVE'").get().snapshot_id,c.base.snapshot_id);
  database.close();
});
test('canonical policy values and response-boundary rejection remain unchanged', async () => {
  const expected=['TEL_NO','E_MAIL','normalized_payload','raw_payload','railway.internal','X-Civic-Operator-Token','CIVIC_OPERATOR','DATABASE_URL','postgresql://','postgresql+psycopg','/admin/review','/operator/','"api_key"','"operator_token"','"private_contact"'];
  assert.deepEqual(FORBIDDEN_TOKENS,expected);
  for(const token of expected)assert.equal(forbiddenToken(`prefix${token}suffix`),token);
  assert.equal(forbiddenToken(JSON.stringify({api_key:'synthetic-value'})),'"api_key"');
  assert.equal(forbiddenToken('http://localhost:8000','http://localhost:8000'),'http://localhost:8000');
  assert.equal(EMAIL.test('synthetic@example.test'),true);
  const{database,db}=setup();const f=fixture({TEL_NO:'synthetic-prohibited-field'});
  await assert.rejects(stage(db,f),{code:'PUBLIC_BOUNDARY_REJECTED'});
  assert.equal(database.prepare("SELECT COUNT(*) AS count FROM snapshot_meta WHERE status='ACTIVE'").get().count,0);
  database.close();
});
test('restore prepare retry cannot report stale ACTIVE across a competing cutover', async () => {
  const{database,db}=setup();const a=fixture({items:['a']}),b=fixture({items:['b']});
  const first=await stage(db,a);await first('activate',{expected_active:null,expected_epoch:0});
  const second=await stage(db,b);await second('activate',{expected_active:a.base.snapshot_id,expected_epoch:1});
  await restore(first,{expected_active:b.base.snapshot_id,expected_epoch:2});
  let changed=false;
  const racing={...db,prepare(sql){const prepared=db.prepare(sql);return{bind(...values){const bound=prepared.bind(...values);return{...bound,async first(){
    const row=await bound.first();
    if(!changed&&sql.startsWith('SELECT snapshot_id,status,')&&row?.snapshot_id===a.base.snapshot_id&&row.status==='ACTIVE'){
      changed=true;
      // Fixture-only deterministic interleaving represents another already-authorized
      // pointer transaction after the first read and before retry confirmation.
      database.prepare("UPDATE snapshot_meta SET status='PREVIOUS' WHERE snapshot_id=?").run(a.base.snapshot_id);
      database.prepare("UPDATE snapshot_meta SET status='ACTIVE',pointer_epoch=4 WHERE snapshot_id=?").run(b.base.snapshot_id);
    }
    return row;
  }}}}}};
  await assert.rejects(executeSnapshotOperation({...a.base,op:'restore',mode:'prepare',expected_active:b.base.snapshot_id,expected_epoch:2},racing),{code:'STATE_CONFLICT'});
  assert.equal(changed,true);
  assert.equal(database.prepare("SELECT snapshot_id FROM snapshot_meta WHERE status='ACTIVE'").get().snapshot_id,b.base.snapshot_id);
  database.close();
});

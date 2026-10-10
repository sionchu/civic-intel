// Executed disposable Miniflare/D1 and exact static-asset smoke; no live credentials.
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { readFileSync, writeFileSync } from 'node:fs';
import { resolve, join } from 'node:path';
import { gzipSync } from 'node:zlib';
import { parseArgs } from 'node:util';
import { SCOPES } from './snapshot-scopes.mjs';
import { digest, snapshotProtocol } from './snapshot-protocol.mjs';
const { values } = parseArgs({ options: { bootstrap: { type: 'string' }, receipt: { type: 'string' } } });
const app = resolve(import.meta.dirname, '..'), bootstrap = resolve(values.bootstrap);
const { Miniflare } = createRequire(join(app, '.sites-worker-build/package.json'))('miniflare');
const bytes = Buffer.from('[]'), gzip = gzipSync(bytes), jsonHash = digest(bytes);
const semantic = { semantics: 'REPLACEABLE_PUBLIC_READ_SNAPSHOT_NOT_SSOT', projection_schema_version: 2, scopes: SCOPES, rows: [['/people',200,jsonHash]] };
const semanticHash = digest(JSON.stringify(semantic));
const manifest = { snapshot_id: `ps-${semanticHash.slice(0,16)}`, semantic_sha256: semanticHash, projection_schema_version: 2,
  scopes: SCOPES, generated_at: '2026-10-08T00:00:00.000Z', generated_at_kst: '2026-10-08 09:00 KST', git_commit: 'a'.repeat(40),
  counts: { paths: 1, parts: 1, public_people: 0, public_organizations: 0 }, paths: [{ path: '/people',status:200,sha256:jsonHash,bytes:bytes.length,gzip_bytes:gzip.length }] };
const protocol = snapshotProtocol(manifest,[{path:'/people',part:0,chunk:gzip}]);
const secret = 'synthetic-disposable-miniflare-test-secret-not-production';
const configuration = { name: 'bootstrap-fixture', modules: true, script: readFileSync(join(bootstrap, 'dist/server/index.js'), 'utf8'),
  compatibilityDate: '2026-05-15', d1Databases: { DB: 'snapshot-writer-disposable' },
  bindings: { CIVIC_SNAPSHOT_WRITER_SECRET: secret, CIVIC_SNAPSHOT_MANIFEST_SHA256: protocol.manifest_sha256 },
  assets: { directory: join(bootstrap, 'dist/client'), binding: 'ASSETS',
    routerConfig: { has_user_worker: true, invoke_user_worker_ahead_of_assets: true }, assetConfig: { html_handling: 'auto-trailing-slash' } } };
const mf = new Miniflare(configuration);
const results = { environment: 'DISPOSABLE_MINIFLARE_D1', synthetic_only: true, checks: [] };
try {
  let db = await mf.getD1Database('DB');
  for (const migration of ['0000_public_projection.sql','0001_snapshot_writer.sql']) {
    const sql = readFileSync(join(app,'sites-worker/drizzle',migration),'utf8').replaceAll('--> statement-breakpoint','');
    await db.batch(sql.split(';').map((part)=>part.trim()).filter(Boolean).map((part)=>db.prepare(part)));
  }
  const base = { version:1,snapshot_id:protocol.snapshot_id,manifest_sha256:protocol.manifest_sha256 };
  async function call(op, fields={}, target=base) {
    const response = await mf.dispatchFetch('http://example.test/api/maintenance/snapshot', { method:'POST',
      headers:{authorization:`Bearer ${secret}`,'content-type':'application/json'},body:JSON.stringify({...target,op,...fields}) });
    const body = await response.json();
    return {status:response.status,body};
  }
  assert.equal((await mf.dispatchFetch('http://example.test/api/maintenance/snapshot', {method:'POST'})).status,401);
  assert.equal((await call('begin',{metadata:{projection_schema_version:2,generated_at:manifest.generated_at,generated_at_kst:manifest.generated_at_kst,git_commit:manifest.git_commit,path_count:1,part_count:1,public_people:0,public_organizations:0}})).status,200);
  assert.equal((await call('metadata',{offset:0,chunk:protocol.scope_json})).status,200);
  assert.equal((await call('manifest')).status,200);
  const part={ordinal:0,path:'/people',part:0,body_base64:gzip.toString('base64')};
  const concurrent = await Promise.all([call('part',part),call('part',part)]);
  assert.ok(concurrent.some((result)=>result.status===200));
  assert.equal((await call('state')).body.cursor,1);
  assert.equal((await db.prepare('SELECT COUNT(*) AS count FROM public_read').first()).count,1);
  assert.equal((await call('seal')).status,200);
  const validation=await Promise.all([call('validate',{ordinal:0}),call('validate',{ordinal:0})]);
  assert.ok(validation.some((result)=>result.status===200));
  assert.equal((await call('state')).body.validation_cursor,1);
  assert.equal((await call('activate',{expected_active:null,expected_epoch:0})).status,200);
  assert.equal((await call('activate',{expected_active:null,expected_epoch:0})).status,200);
  assert.equal((await call('activate',{expected_active:'ps-aaaaaaaaaaaaaaaa',expected_epoch:0})).status,409);
  assert.equal((await call('metadata',{offset:protocol.metadata_bytes,chunk:'extra'})).status,409);
  results.checks.push({auth:'PASS', actual_d1_batch:'PASS', cursor_concurrency:'PASS', seal:'PASS', decode_validation:'PASS', activation_retry_stale_cas:'PASS'});
  const secondBytes=Buffer.from('["second"]'),secondGzip=gzipSync(secondBytes),secondHash=digest(secondBytes);
  const secondSemantic={...semantic,rows:[['/people',200,secondHash]]};
  const secondSemanticHash=digest(JSON.stringify(secondSemantic));
  const secondManifest={...manifest,snapshot_id:`ps-${secondSemanticHash.slice(0,16)}`,semantic_sha256:secondSemanticHash,
    paths:[{path:'/people',status:200,sha256:secondHash,bytes:secondBytes.length,gzip_bytes:secondGzip.length}]};
  const secondProtocol=snapshotProtocol(secondManifest,[{path:'/people',part:0,chunk:secondGzip}]);
  const secondBase={...base,snapshot_id:secondProtocol.snapshot_id,manifest_sha256:secondProtocol.manifest_sha256};
  await mf.setOptions({...configuration,bindings:{...configuration.bindings,
    CIVIC_SNAPSHOT_MANIFEST_SHA256:secondProtocol.manifest_sha256,CIVIC_SNAPSHOT_PREVIOUS_MANIFEST_SHA256:protocol.manifest_sha256}});
  db=await mf.getD1Database('DB');
  assert.equal((await call('begin',{metadata:{projection_schema_version:2,generated_at:manifest.generated_at,generated_at_kst:manifest.generated_at_kst,git_commit:manifest.git_commit,path_count:1,part_count:1,public_people:0,public_organizations:0}},secondBase)).status,200);
  for(const[op,fields]of[['metadata',{offset:0,chunk:secondProtocol.scope_json}],['manifest',{}],['part',{ordinal:0,path:'/people',part:0,body_base64:secondGzip.toString('base64')}],['seal',{}],['validate',{ordinal:0}]])assert.equal((await call(op,fields,secondBase)).status,200);
  assert.equal((await call('activate',{expected_active:base.snapshot_id,expected_epoch:1},secondBase)).status,200);
  assert.equal((await call('begin',{})).status,403);
  const expected={expected_active:secondBase.snapshot_id,expected_epoch:2};
  assert.equal((await call('restore',{...expected,mode:'prepare'})).status,200);
  await db.prepare('UPDATE public_read SET body_gzip=? WHERE snapshot_id=?').bind(new Uint8Array([1]),base.snapshot_id).run();
  assert.equal((await call('restore',{...expected,mode:'validate',ordinal:0})).status,409);
  assert.equal((await call('restore',{...expected,mode:'activate'})).status,409);
  assert.equal((await db.prepare("SELECT snapshot_id FROM snapshot_meta WHERE status='ACTIVE'").first()).snapshot_id,secondBase.snapshot_id);
  await db.prepare('UPDATE public_read SET body_gzip=? WHERE snapshot_id=?').bind(new Uint8Array(gzip),base.snapshot_id).run();
  assert.equal((await call('restore',{...expected,mode:'validate',ordinal:0})).status,200);
  assert.equal((await call('restore',{...expected,mode:'activate'})).status,200);
  assert.equal((await call('restore',{...expected,mode:'activate'})).status,200);
  const back={expected_active:base.snapshot_id,expected_epoch:3};
  for(const[mode,fields]of[['prepare',{}],['validate',{ordinal:0}],['activate',{}]])assert.equal((await call('restore',{...back,mode,...fields},secondBase)).status,200);
  assert.equal((await call('restore',{...expected,mode:'activate'})).status,409);
  results.checks.push({authenticated_two_pin_actual_d1_restore:'PASS',corrupt_previous_preserves_active:'PASS',restore_revalidation:'PASS',late_restore_retry:'PASS'});
  const negativeBytes=Buffer.from('{"TEL_NO":"synthetic-prohibited-field"}'),negativeGzip=gzipSync(negativeBytes),negativeHash=digest(negativeBytes);
  const negativeSemantic={...semantic,rows:[['/people',200,negativeHash]]};
  const negativeSemanticHash=digest(JSON.stringify(negativeSemantic));
  const negativeManifest={...manifest,snapshot_id:`ps-${negativeSemanticHash.slice(0,16)}`,semantic_sha256:negativeSemanticHash,
    paths:[{path:'/people',status:200,sha256:negativeHash,bytes:negativeBytes.length,gzip_bytes:negativeGzip.length}]};
  const negativeProtocol=snapshotProtocol(negativeManifest,[{path:'/people',part:0,chunk:negativeGzip}]);
  const negativeBase={...base,snapshot_id:negativeProtocol.snapshot_id,manifest_sha256:negativeProtocol.manifest_sha256};
  await mf.setOptions({...configuration,bindings:{...configuration.bindings,CIVIC_SNAPSHOT_MANIFEST_SHA256:negativeProtocol.manifest_sha256}});
  db=await mf.getD1Database('DB');
  assert.equal((await call('begin',{metadata:{projection_schema_version:2,generated_at:manifest.generated_at,generated_at_kst:manifest.generated_at_kst,git_commit:manifest.git_commit,path_count:1,part_count:1,public_people:0,public_organizations:0}},negativeBase)).status,200);
  for(const[op,fields]of[['metadata',{offset:0,chunk:negativeProtocol.scope_json}],['manifest',{}],['part',{ordinal:0,path:'/people',part:0,body_base64:negativeGzip.toString('base64')}],['seal',{}]])assert.equal((await call(op,fields,negativeBase)).status,200);
  const negativeValidation=await call('validate',{ordinal:0},negativeBase);
  assert.equal(negativeValidation.status,409);assert.equal(negativeValidation.body.error,'PUBLIC_BOUNDARY_REJECTED');
  assert.equal((await call('activate',{expected_active:secondBase.snapshot_id,expected_epoch:4},negativeBase)).status,409);
  assert.equal((await db.prepare("SELECT snapshot_id FROM snapshot_meta WHERE status='ACTIVE'").first()).snapshot_id,secondBase.snapshot_id);
  results.checks.push({compiled_runtime_policy_constant_input:'TEL_NO_SYNTHETIC_FIXTURE',public_boundary_rejection:'PASS',active_unchanged:'PASS'});
  for (const [path,file] of [['/','index.html'],['/people/0006e231-f5d2-5c9d-9177-e4646ba5dda7/','people/0006e231-f5d2-5c9d-9177-e4646ba5dda7/index.html'],['/gukgam/2026/','gukgam/2026/index.html'],['/people/0006e231-f5d2-5c9d-9177-e4646ba5dda7/index.txt','people/0006e231-f5d2-5c9d-9177-e4646ba5dda7/index.txt']]) {
    const response=await mf.dispatchFetch(`http://example.test${path}`);
    assert.equal(response.status,200); const actual=new Uint8Array(await response.arrayBuffer());
    const expected=readFileSync(join(bootstrap,'dist/client',file)); assert.equal(digest(actual),digest(expected));
    results.checks.push({path,status:response.status,bytes:actual.length,sha256:digest(actual),exact_static_bytes:'PASS'});
  }
  const redirect=await mf.dispatchFetch('http://example.test/people/0006e231-f5d2-5c9d-9177-e4646ba5dda7',{redirect:'manual'});
  assert.ok([301,307,308].includes(redirect.status));
  results.checks.push({path:'person-without-trailing-slash',status:redirect.status,location:redirect.headers.get('location'),trailing_slash:'PASS'});
  results.status='PASS';
  writeFileSync(resolve(values.receipt),JSON.stringify(results,null,2)+'\n');
  console.log(JSON.stringify({status:'PASS',checks:results.checks.length}));
} finally { await mf.dispose(); }

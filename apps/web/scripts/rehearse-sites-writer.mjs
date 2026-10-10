// Full pinned public snapshot through the finite HTTP uploader into disposable D1.
// All credentials are synthetic; no operational database, API or hosted Site is used.
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { readFileSync, writeFileSync, createWriteStream } from 'node:fs';
import { resolve, join } from 'node:path';
import { spawn } from 'node:child_process';
import { gunzipSync } from 'node:zlib';
import { parseArgs } from 'node:util';
import { digest } from './snapshot-protocol.mjs';
const { values } = parseArgs({ options: { bootstrap:{type:'string'}, projection:{type:'string'}, receipt:{type:'string'}, log:{type:'string'} } });
const app=resolve(import.meta.dirname,'..'), bootstrap=resolve(values.bootstrap), projection=resolve(values.projection);
const protocol=JSON.parse(readFileSync(join(projection,'writer-manifest.json'),'utf8'));
assert.equal(digest(protocol.scope_json),protocol.manifest_sha256);
const scope=JSON.parse(protocol.scope_json), paths=Object.entries(scope.paths);
const { Miniflare }=createRequire(join(app,'.sites-worker-build/package.json'))('miniflare');
const secret='synthetic-local-real-data-rehearsal-secret-not-production';
const started=new Date().toISOString(), begin=performance.now();
const mf=new Miniflare({name:'real-rehearsal',host:'127.0.0.1',modules:true,
  script:readFileSync(join(bootstrap,'dist/server/index.js'),'utf8'),compatibilityDate:'2026-05-15',
  d1Databases:{DB:'real-rehearsal-disposable'},bindings:{CIVIC_SNAPSHOT_WRITER_SECRET:secret,CIVIC_SNAPSHOT_MANIFEST_SHA256:protocol.manifest_sha256}});
const log=createWriteStream(resolve(values.log));
const receipt={dataset_origin:'CURRENT_FRONTEND_PUBLIC_API',environment:'DISPOSABLE_LOCAL_MINIFLARE_D1',
  upstream_api_runtime_revision:'UNKNOWN',upstream_consistency:'UNVERIFIED_CAPTURE_WINDOW',
  snapshot_id:protocol.snapshot_id,protocol_sha256:protocol.manifest_sha256,semantic_sha256:scope.writer.semantic_sha256,
  started_at:started,hosted_effects:'NONE',canonical_effects:'NONE'};
try{
  const db=await mf.getD1Database('DB');
  for(const name of ['0000_public_projection.sql','0001_snapshot_writer.sql']){
    const sql=readFileSync(join(app,'sites-worker/drizzle',name),'utf8').replaceAll('--> statement-breakpoint','');
    await db.batch(sql.split(';').map(s=>s.trim()).filter(Boolean).map(s=>db.prepare(s)));
  }
  const origin=(await mf.ready).origin;
  async function upload(action,extra=[]){
    const child=spawn(process.execPath,[join(app,'scripts/upload-public-projection.mjs'),'--local-rehearsal','--origin',origin,'--projection',projection,'--action',action,...extra],{stdio:['pipe','pipe','pipe']});
    child.stdin.end(secret+'\n');child.stdout.pipe(log,{end:false});child.stderr.pipe(log,{end:false});
    const code=await new Promise((res,rej)=>{child.on('error',rej);child.on('close',res);});
    assert.equal(code,0,`FINITE_UPLOADER_${action.toUpperCase()}_FAILED`);
  }
  await upload('load');receipt.load_validate_elapsed_seconds=(performance.now()-begin)/1000;
  await upload('activate',['--expected-active','NONE','--expected-epoch','0']);
  const active=await db.prepare("SELECT * FROM snapshot_meta WHERE status='ACTIVE'").first();
  assert.equal(active.snapshot_id,protocol.snapshot_id);assert.equal(active.writer_phase,'VALIDATED');
  assert.equal(active.writer_cursor,scope.writer.counts.parts);assert.equal(active.validation_cursor,paths.length);
  assert.equal(digest(active.scope_json),protocol.manifest_sha256);
  const sourceIds=new Set();let totalParts=0, errorPaths=0;
  function sources(value){if(Array.isArray(value))value.forEach(sources);else if(value&&typeof value==='object')for(const[key,item]of Object.entries(value)){
    if(key==='source_ids'&&Array.isArray(item))item.forEach(id=>sourceIds.add(id));else if(key==='source_id'&&typeof item==='string')sourceIds.add(item);else sources(item);
  }}
  for(let ordinal=0;ordinal<paths.length;ordinal++){
    const[path,tuple]=paths[ordinal];
    const result=await db.prepare('SELECT part,status,content_sha256,body_gzip FROM public_read WHERE snapshot_id=? AND path=? ORDER BY part').bind(protocol.snapshot_id,path).all();
    assert.equal(result.results.length,tuple[4].length);totalParts+=result.results.length;
    const chunks=result.results.map((part,index)=>{
      const bytes=Buffer.from(part.body_gzip);assert.equal(part.part,index);assert.equal(part.status,tuple[0]);
      assert.equal(part.content_sha256,tuple[1]);assert.equal(digest(bytes),tuple[4][index]);return bytes;
    });
    const decoded=gunzipSync(Buffer.concat(chunks));assert.equal(decoded.length,tuple[2]);assert.equal(digest(decoded),tuple[1]);
    sources(JSON.parse(decoded.toString('utf8')));if(tuple[0]>=400)errorPaths++;
    if((ordinal+1)%500===0)log.write(JSON.stringify({readback_paths:ordinal+1})+'\n');
  }
  for(const id of sourceIds){assert.ok(scope.paths[`/sources/${id}`]);assert.equal(scope.paths[`/sources/${id}`][0],200);}
  assert.equal(totalParts,scope.writer.counts.parts);
  Object.assign(receipt,{status:'PASS',paths:paths.length,parts:totalParts,source_reference_closure:sourceIds.size,
    client_error_paths:errorPaths,active:active.snapshot_id,pointer_epoch:active.pointer_epoch,
    finished_at:new Date().toISOString(),elapsed_seconds:(performance.now()-begin)/1000,
    runner_max_rss_kib:process.resourceUsage().maxRSS,rss_scope:'NODE_RUNNER_ONLY_NOT_WORKER_ISOLATE_OR_HOSTED_MEMORY'});
  writeFileSync(resolve(values.receipt),JSON.stringify(receipt,null,2)+'\n');
  console.log(JSON.stringify({status:'PASS',paths:paths.length,parts:totalParts,sources:sourceIds.size,elapsed_seconds:receipt.elapsed_seconds}));
}finally{await mf.dispose();log.end();}

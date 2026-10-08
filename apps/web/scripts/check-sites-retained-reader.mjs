// Exact current generated reader DTOs against retained disposable D1 bytes.
// SQLite is read-only; this is not a new full upload or a hosted deployment claim.
import assert from 'node:assert/strict';
import { DatabaseSync } from 'node:sqlite';
import { readFileSync, writeFileSync } from 'node:fs';
import { resolve, join } from 'node:path';
import { pathToFileURL } from 'node:url';
import { parseArgs } from 'node:util';
import ts from 'typescript';
import { digest } from './snapshot-protocol.mjs';
const{values}=parseArgs({options:{source:{type:'string'},db:{type:'string'},manifest:{type:'string'},receipt:{type:'string'}}});
const sourceRoot=resolve(values.source), canonical=resolve(import.meta.dirname,'../sites-worker/public-read.d1.ts');
const shims=resolve(import.meta.dirname,'../.sites-worker-build/node_modules/vinext/dist/shims');
const {createRequestContext,runWithRequestContext}=await import(pathToFileURL(join(shims,'unified-request-context.js')));
const generated=readFileSync(join(sourceRoot,'app/public-read.ts'),'utf8');
assert.equal(digest(generated),digest(readFileSync(canonical,'utf8')),'GENERATED_READER_SOURCE_MISMATCH');
const manifest=JSON.parse(readFileSync(resolve(values.manifest),'utf8'));
const database=new DatabaseSync(resolve(values.db),{readOnly:true});
const active=database.prepare("SELECT snapshot_id,path_count,part_count FROM snapshot_meta WHERE status='ACTIVE'").get();
assert.equal(active.snapshot_id,manifest.snapshot_id);
globalThis.__retainedReaderEnv={DB:{prepare(query){let bound=[];return{bind(...values){bound=values;return this;},async all(){return{results:database.prepare(query).all(...bound)}}}}}};
const source=generated.replace('import { env } from "cloudflare:workers";','const env=globalThis.__retainedReaderEnv;')
  .replace('"vinext/cache"',JSON.stringify(pathToFileURL(join(shims,'cache-for-request.js')).href))
  .replace('"./relationship-path.mjs"',JSON.stringify(pathToFileURL(join(sourceRoot,'app/relationship-path.mjs')).href));
const code=ts.transpileModule(source,{compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.ESNext}}).outputText;
const reader=await import(`data:text/javascript;base64,${Buffer.from(code).toString('base64')}`);
const started=performance.now();let paths=0,errors=0;
try{
  for(const expected of manifest.paths){const actual=await runWithRequestContext(createRequestContext(),()=>reader.readPublic(expected.path));assert.equal(actual.status,expected.status);
    const json=Buffer.from(JSON.stringify(actual.body));assert.equal(json.length,expected.bytes);assert.equal(digest(json),expected.sha256);
    paths++;if(actual.status>=400)errors++;
  }
  const after=database.prepare("SELECT snapshot_id,path_count,part_count FROM snapshot_meta WHERE status='ACTIVE'").get();assert.deepEqual(after,active);
  const result={status:'PASS',environment:'CURRENT_GENERATED_READER_READ_ONLY_RETAINED_LOCAL_D1',
    snapshot_id:manifest.snapshot_id,reader_source_sha256:digest(generated),manifest_sha256:digest(readFileSync(resolve(values.manifest))),
    paths,parts:active.part_count,client_error_paths:errors,exact_status_json_bytes_sha256:true,
    cache_adapter:'ACTUAL_INSTALLED_VINEXT_SEPARATE_REQUEST_CONTEXT_PER_PATH',
    elapsed_seconds:(performance.now()-started)/1000,hosted_effects:'NONE',writes:'NONE'};
  writeFileSync(resolve(values.receipt),JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify({status:'PASS',paths,parts:active.part_count}));
}finally{database.close();delete globalThis.__retainedReaderEnv;}

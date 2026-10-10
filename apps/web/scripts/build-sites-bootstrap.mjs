// Temporary bootstrap: preserve every byte of the deployed static v3 while an
// authenticated finite maintenance Worker stages D1. Final deployment is code-only.
import { cpSync, existsSync, mkdirSync, readFileSync, readdirSync, statSync, writeFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { createRequire } from 'node:module';
import { spawnSync } from 'node:child_process';
import { resolve, join, relative } from 'node:path';
import { parseArgs } from 'node:util';
const { values } = parseArgs({ options: { source: { type: 'string' }, out: { type: 'string' }, 'source-sha': { type: 'string' } } });
const root = resolve(import.meta.dirname, '../../..'), app = resolve(import.meta.dirname, '..');
const source = resolve(values.source), out = resolve(values.out);
if (!out.startsWith(join(root, 'dist') + '/') && !out.startsWith(join(root, 'dist') + '\\')) throw new Error('OUTPUT_OUTSIDE_TASK_DIST');
if (existsSync(out)) throw new Error('OUTPUT_ALREADY_EXISTS');
const head = spawnSync('git', ['rev-parse', 'HEAD'], { cwd: source, encoding: 'utf8' }).stdout.trim();
const dirty = spawnSync('git', ['status', '--porcelain'], { cwd: source, encoding: 'utf8' }).stdout.trim();
if (head !== values['source-sha'] || dirty) throw new Error('SOURCE_PIN_MISMATCH');
const hosting = JSON.parse(readFileSync(join(source, '.openai/hosting.json'), 'utf8'));
if (hosting.project_id !== 'appgprj_6ac46916b4d08191872983ffd6d52aba' || hosting.static?.directory !== 'dist') throw new Error('SOURCE_HOSTING_MISMATCH');
mkdirSync(join(out, 'dist/server'), { recursive: true });
cpSync(join(source, 'dist'), join(out, 'dist/client'), { recursive: true });
mkdirSync(join(out, '.openai'), { recursive: true });
writeFileSync(join(out, '.openai/hosting.json'), JSON.stringify({ project_id: hosting.project_id, d1: 'DB', r2: null }, null, 2) + '\n');
cpSync(join(app, 'sites-worker/drizzle'), join(out, 'drizzle'), {
  recursive: true, filter: (path) => !path.endsWith('rollback_snapshot_writer.sql'),
});
const require = createRequire(join(app, '.sites-worker-build/package.json'));
await require('esbuild').build({ stdin: { resolveDir: app, sourcefile: 'bootstrap-entry.mjs', contents:
`import { handleSnapshotWriter } from './sites-worker/snapshot-writer.mjs';
import { executeSnapshotOperation } from './sites-worker/snapshot-operations.mjs';
export default {fetch(request,env){return new URL(request.url).pathname==='/api/maintenance/snapshot' ? handleSnapshotWriter(request,env,executeSnapshotOperation) : env.ASSETS.fetch(request);}};` },
outfile: join(out, 'dist/server/index.js'), bundle: true, format: 'esm', platform: 'browser', target: 'es2022' });
const generated = JSON.parse(readFileSync(join(app, '.sites-worker-build/dist/server/wrangler.json'), 'utf8'));
generated.name = 'moduigukgam-bootstrap'; generated.main = 'index.js';
generated.assets = { directory: '../client', binding: 'ASSETS', run_worker_first: ['/api/maintenance/snapshot'], html_handling: 'auto-trailing-slash' };
generated.vars = {}; generated.observability = { enabled: false };
writeFileSync(join(out, 'dist/server/wrangler.json'), JSON.stringify(generated) + '\n');
// Use a fixed root so nested filenames, redirects, RSC text and portraits remain
// an exact inventory rather than a count-only or sampled provenance claim.
function tree(directory, base = directory) {
  return readdirSync(directory).sort().flatMap((name) => {
    const file = join(directory, name);
    return statSync(file).isDirectory() ? tree(file, base) : [{ path: relative(base, file).replaceAll('\\', '/'), bytes: statSync(file).size,
      sha256: createHash('sha256').update(readFileSync(file)).digest('hex') }];
  });
}
const original = tree(join(source, 'dist')), copied = tree(join(out, 'dist/client'));
if (JSON.stringify(original) !== JSON.stringify(copied)) throw new Error('ASSET_PARITY_FAILED');
const files = tree(join(out, 'dist'));
const bytes = files.reduce((sum, file) => sum + file.bytes, 0);
if (bytes > 256 * 1024 * 1024) throw new Error('BOOTSTRAP_ARTIFACT_TOO_LARGE');
writeFileSync(join(out, 'bootstrap-receipt.json'), JSON.stringify({ source_sha: head, project_id: hosting.project_id,
  old_assets: original.length, old_asset_bytes: original.reduce((sum, file) => sum + file.bytes, 0),
  copied_assets_exact: true, artifact_files: files.length, artifact_bytes: bytes,
  artifact_tree_sha256: createHash('sha256').update(JSON.stringify(files)).digest('hex'),
  purpose: 'TEMPORARY_STATIC_PRESERVATION_D1_BOOTSTRAP_NOT_FINAL_CODE_ONLY',
}, null, 2) + '\n');
console.log(JSON.stringify({ status: 'PASS_LOCAL_BUILD_INVENTORY', bytes, old_assets: original.length }));

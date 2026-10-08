// Actual final Vinext Worker proof. No production credentials or operational DB.
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { readFileSync, readdirSync, writeFileSync } from 'node:fs';
import { resolve, join } from 'node:path';
import { parseArgs } from 'node:util';
import { createHash } from 'node:crypto';
const { values } = parseArgs({ options: { receipt: { type: 'string' } } });
const stage = resolve(import.meta.dirname, '../.sites-worker-build');
const { Miniflare } = createRequire(join(stage, 'package.json'))('miniflare');
const server = join(stage, 'dist/server');
function files(directory) {
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const path = join(directory, entry.name);
    return entry.isDirectory() ? files(path) : [path];
  });
}
const executable = files(server).filter((path) => /\.m?js$/.test(path));
for (const path of executable) {
  const source = readFileSync(path, 'utf8');
  assert.ok(!source.includes('CIVIC_SNAPSHOT_WRITER_SECRET'), 'WRITER_AUTH_CODE_RETAINED');
  assert.ok(!source.includes('PUBLIC_BOUNDARY_REJECTED'), 'WRITER_OPERATIONS_CODE_RETAINED');
}
const mf = new Miniflare({
  modules: true, scriptPath: join(server, 'index.js'), modulesRoot: server,
  modulesRules: [{ type: 'ESModule', include: ['**/*.js', '**/*.mjs'], fallthrough: true }],
  compatibilityDate: '2026-05-15', compatibilityFlags: ['nodejs_compat'],
  d1Databases: { DB: 'reader-security-disposable' },
  bindings: { CIVIC_SNAPSHOT_WRITER_SECRET: 'synthetic-valid-retained-maintenance-secret',
    CIVIC_SNAPSHOT_MANIFEST_SHA256: 'a'.repeat(64) },
});
try {
  const db = await mf.getD1Database('DB');
  // Missing schema would fail if any writer/state DB operation were dispatched.
  const before = await db.prepare('SELECT COUNT(*) AS count FROM sqlite_master').first();
  const checks = [];
  for (const body of ['{}', 'not-json', 'x'.repeat(131073)]) {
    const response = await mf.dispatchFetch('http://reader.test/api/maintenance/snapshot', {
      method: 'POST', headers: { authorization: 'Bearer synthetic-valid-retained-maintenance-secret',
        'content-type': 'application/json' }, body,
    });
    assert.equal(response.status, 404);
    assert.deepEqual(await response.json(), { error: 'MAINTENANCE_DISABLED' });
    checks.push({ body_bytes: Buffer.byteLength(body), status: response.status });
  }
  const after = await db.prepare('SELECT COUNT(*) AS count FROM sqlite_master').first();
  assert.deepEqual(after, before);
  writeFileSync(resolve(values.receipt), JSON.stringify({ status: 'PASS',
    environment: 'ACTUAL_COMPILED_VINEXT_MINIFLARE', synthetic_secret_only: true,
    writer_auth_and_operations_absent_from_all_executable_modules: true,
    missing_schema_unchanged: true, checks,
    index_sha256: createHash('sha256').update(readFileSync(join(server, 'index.js'))).digest('hex'),
  }, null, 2) + '\n');
  console.log(JSON.stringify({ status: 'PASS', requests: checks.length }));
} finally { await mf.dispose(); }

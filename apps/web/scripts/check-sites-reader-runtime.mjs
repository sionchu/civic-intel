// Actual final Vinext Worker proof. No production credentials or operational DB.
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { readFileSync, readdirSync, writeFileSync } from 'node:fs';
import { resolve, join } from 'node:path';
import { parseArgs } from 'node:util';
import { createHash } from 'node:crypto';
import { request as httpRequest } from 'node:http';
const { values } = parseArgs({ options: { receipt: { type: 'string' } } });
const stage = resolve(import.meta.dirname, '../.sites-worker-build');
const { Miniflare, Log, LogLevel } = createRequire(join(stage, 'package.json'))('miniflare');
const server = join(stage, 'dist/server');
function files(directory) {
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const path = join(directory, entry.name);
    return entry.isDirectory() ? files(path) : [path];
  });
}
const executable = files(server).filter((path) => /\.m?js$/.test(path))
  .sort((a, b) => (a === join(server, 'index.js') ? -1 : b === join(server, 'index.js') ? 1 : a.localeCompare(b)));
for (const path of executable) {
  const source = readFileSync(path, 'utf8');
  assert.ok(!source.includes('CIVIC_SNAPSHOT_WRITER_SECRET'), 'WRITER_AUTH_CODE_RETAINED');
  assert.ok(!source.includes('PUBLIC_BOUNDARY_REJECTED'), 'WRITER_OPERATIONS_CODE_RETAINED');
}
const mf = new Miniflare({
  // Vinext uses computed dynamic imports: enumerate its exact executable files.
  modules: executable.map((path) => ({ type: 'ESModule',
    path, contents: readFileSync(path, 'utf8') })),
  modulesRoot: server,
  compatibilityDate: '2026-05-15', compatibilityFlags: ['nodejs_compat'],
  log: new Log(LogLevel.INFO),
  d1Databases: { DB: 'reader-security-disposable' },
  bindings: { CIVIC_SNAPSHOT_WRITER_SECRET: 'synthetic-valid-retained-maintenance-secret',
    CIVIC_SNAPSHOT_MANIFEST_SHA256: 'a'.repeat(64) },
});
try {
  const db = await mf.getD1Database('DB');
  // Missing schema would fail if any writer/state DB operation were dispatched.
  const schema = "SELECT COUNT(*) AS count FROM sqlite_master WHERE name IN ('snapshot_meta','public_read')";
  const before = await db.prepare(schema).first();
  assert.equal(before.count, 0);
  const address = await mf.ready;
  const checks = [];
  for (const body of ['{}', 'not-json', 'x'.repeat(131073)]) {
    // Workerd may close an unread upload after sending the finite denial. Native
    // HTTP reads that denial without undici's aborted-upload/body coupling.
    const response = await new Promise((resolveResponse, rejectResponse) => {
      let received = false;
      const request = httpRequest(new URL('/api/maintenance/snapshot', address), {
        method: 'POST', agent: false, headers: { authorization: 'Bearer synthetic-valid-retained-maintenance-secret',
          'content-type': 'application/json', 'content-length': Buffer.byteLength(body), connection: 'close' },
      }, (response) => {
        received = true;
        let content = '';
        response.setEncoding('utf8');
        response.on('data', (chunk) => { content += chunk; });
        response.on('end', () => resolveResponse({ status: response.statusCode, body: JSON.parse(content) }));
        response.on('error', rejectResponse);
      });
      request.on('error', (error) => { if (!received) rejectResponse(error); });
      request.end(body);
    });
    assert.equal(response.status, 404);
    assert.deepEqual(response.body, { error: 'MAINTENANCE_DISABLED' });
    checks.push({ body_bytes: Buffer.byteLength(body), status: response.status });
  }
  const after = await db.prepare(schema).first();
  assert.deepEqual(after, before);
  writeFileSync(resolve(values.receipt), JSON.stringify({ status: 'PASS',
    environment: 'ACTUAL_COMPILED_VINEXT_MINIFLARE', synthetic_secret_only: true,
    writer_auth_and_operations_absent_from_all_executable_modules: true,
    missing_schema_unchanged: true, checks,
    index_sha256: createHash('sha256').update(readFileSync(join(server, 'index.js'))).digest('hex'),
  }, null, 2) + '\n');
  console.log(JSON.stringify({ status: 'PASS', requests: checks.length }));
} finally { await mf.dispose(); }

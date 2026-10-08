// Disposable loopback replay of one captured public projection for same-input SSR/static/D1 QA.
// Never a hosted API or canonical store. It performs no upstream reads and exposes no writes.
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { createServer } from 'node:http';
import { join, resolve } from 'node:path';
import { DatabaseSync } from 'node:sqlite';
import { parseArgs } from 'node:util';
import { gunzipSync } from 'node:zlib';

const { values } = parseArgs({ options: { projection: { type: 'string' }, port: { type: 'string', default: '8794' } } });
if (!values.projection) throw new Error('--projection is required');
const root = resolve(values.projection);
const manifest = JSON.parse(readFileSync(join(root, 'projection-manifest.json'), 'utf8'));
const expected = new Map(manifest.paths.map((row) => [row.path, row]));
const db = new DatabaseSync(':memory:');
db.exec(readFileSync(new URL('../sites-worker/drizzle/0000_public_projection.sql', import.meta.url), 'utf8'));
db.exec(readFileSync(join(root, 'load.sql'), 'utf8'));
const getParts = db.prepare('SELECT part, status, content_sha256, body_gzip FROM public_read WHERE snapshot_id = ? AND path = ? ORDER BY part');
const server = createServer((request, response) => {
  if (request.method !== 'GET' && request.method !== 'HEAD') { response.writeHead(405); response.end(); return; }
  if (request.url === '/ready') { response.writeHead(200, { 'content-type': 'application/json' }); response.end('{"status":"ready"}'); return; }
  const row = expected.get(request.url);
  if (!row) { response.writeHead(404, { 'content-type': 'application/json' }); response.end('{"error":{"code":"PUBLIC_RECORD_NOT_FOUND"}}'); return; }
  try {
    const parts = getParts.all(manifest.snapshot_id, request.url);
    if (!parts.length || parts.some((part, index) => part.part !== index || part.status !== row.status || part.content_sha256 !== row.sha256)) throw new Error('invalid parts');
    const bytes = gunzipSync(Buffer.concat(parts.map((part) => Buffer.from(part.body_gzip))));
    if (createHash('sha256').update(bytes).digest('hex') !== row.sha256) throw new Error('invalid hash');
    response.writeHead(row.status, { 'content-type': 'application/json', 'cache-control': 'no-store' });
    response.end(bytes);
  } catch {
    response.writeHead(503, { 'content-type': 'application/json' });
    response.end('{"error":{"code":"SERVICE_UNAVAILABLE"}}');
  }
});
server.listen(Number(values.port), '127.0.0.1', () => console.log(JSON.stringify({
  status: 'PUBLIC_PROJECTION_REPLAY_READY', snapshot_id: manifest.snapshot_id,
  semantic_sha256: manifest.semantic_sha256, paths: expected.size, port: Number(values.port),
})));
for (const signal of ['SIGINT', 'SIGTERM']) process.on(signal, () => server.close(() => { db.close(); process.exit(0); }));

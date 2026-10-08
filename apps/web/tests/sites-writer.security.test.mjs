import { test } from 'node:test';
import assert from 'node:assert/strict';
import { BODY_LIMIT, handleSnapshotWriter } from '../sites-worker/snapshot-writer.mjs';
import { executeSnapshotOperation } from '../sites-worker/snapshot-operations.mjs';

const token = 'synthetic-security-fixture-token-0123456789';
const pin = 'a'.repeat(64);
const envelope = { version: 1, snapshot_id: 'ps-0123456789abcdef', manifest_sha256: pin, op: 'state' };
const environment = { CIVIC_SNAPSHOT_WRITER_SECRET: token, CIVIC_SNAPSHOT_MANIFEST_SHA256: pin };
function request(body = JSON.stringify(envelope), headers = {}, method = 'POST') {
  return new Request('https://example.test/api/maintenance/snapshot', {
    method, headers: { authorization: `Bearer ${token}`, 'content-type': 'application/json', ...headers },
    ...(method === 'GET' || method === 'HEAD' ? {} : { body, ...(body instanceof ReadableStream ? { duplex: 'half' } : {}) }),
  });
}
async function denied(req, env, status) {
  let dbReads = 0, executions = 0;
  const guarded = { ...env, get DB() { dbReads++; return {}; } };
  const result = await handleSnapshotWriter(req, guarded, async () => { executions++; throw new Error(token); });
  assert.equal(result.status, status);
  assert.equal(dbReads, 0, 'denial must not even resolve DB binding');
  assert.equal(executions, 0, 'denial must not invoke executor');
  const text = await result.text();
  assert.equal(text.includes(token), false);
  assert.equal(text.includes('Bearer'), false);
  assert.equal(result.headers.get('cache-control'), 'no-store');
  return text;
}

test('missing, malformed, wrong and unconfigured capability fail before body or DB', async () => {
  for (const authorization of ['', 'Basic fixture', 'Bearer wrong', `bearer ${token}`, `Bearer ${token} suffix`, `Bearer ${'x'.repeat(257)}`]) {
    const req = request('{invalid', { authorization });
    await denied(req, environment, 401);
    assert.equal(req.bodyUsed, false);
  }
  for (const secret of [undefined, '', 'short', 'x'.repeat(257), 123]) {
    const req = request('{invalid');
    await denied(req, { ...environment, CIVIC_SNAPSHOT_WRITER_SECRET: secret }, 401);
    assert.equal(req.bodyUsed, false);
  }
  await denied(request(undefined, {}, 'GET'), environment, 405);
  const put = request('{invalid', {}, 'PUT');
  await denied(put, environment, 405);
  assert.equal(put.bodyUsed, false);
});

test('declared and streamed byte caps reject absent or spoofed Content-Length', async () => {
  await denied(request('{}', { 'content-length': String(BODY_LIMIT + 1) }), environment, 413);
  for (const length of [undefined, '1']) {
    let cancelled = false;
    const stream = new ReadableStream({
      start(controller) { controller.enqueue(new Uint8Array(BODY_LIMIT)); controller.enqueue(new Uint8Array(1)); },
      cancel() { cancelled = true; },
    });
    await denied(request(stream, length ? { 'content-length': length } : {}), environment, 413);
    assert.equal(cancelled, true, 'oversized stream must be cancelled');
  }
  await denied(request('{}', { 'content-type': 'text/plain' }), environment, 415);
});

test('invalid UTF-8, JSON and ambiguous encodings fail before DB', async () => {
  for (const body of [new Uint8Array([0xc3, 0x28]), '{', 'null', '[]', JSON.stringify(envelope) + '\n', '{"version":1,"version":1}', JSON.stringify(envelope).replace('"version":1', '"version":1.0')]) {
    await denied(request(body), environment, 400);
  }
});

test('deployment manifest pin fails closed before DB resolution', async () => {
  await denied(request(JSON.stringify({ ...envelope, manifest_sha256: 'b'.repeat(64) })), environment, 403);
  for (const approved of [undefined, '', 'A'.repeat(64), 'a'.repeat(63)]) {
    await denied(request(), { ...environment, CIVIC_SNAPSHOT_MANIFEST_SHA256: approved }, 403);
  }
  await denied(request(JSON.stringify({ ...envelope, snapshot_id: '../arbitrary' })), environment, 400);
});

test('authenticated execution exceptions are sanitized', async () => {
  const result = await handleSnapshotWriter(request(), { ...environment, DB: {} }, async () => { throw new Error(`private ${token}`); });
  assert.equal(result.status, 500);
  assert.deepEqual(await result.json(), { error: 'WRITER_FAILED' });
});

test('unknown operations and untrusted fields cannot reach database methods', async () => {
  const bodies = [
    { ...envelope, op: 'execute_sql', sql: 'DROP TABLE public_read' },
    { ...envelope, sql: 'SELECT private_data' },
    { ...envelope, url: 'https://untrusted.example/upload' },
    { ...envelope, metadata: {} },
    { ...envelope, op: 'seal', extra: true },
    { ...envelope, op: 'validate', ordinal: 0, extra: true },
    { ...envelope, op: 'part', ordinal: 0, path: '/people', part: 0, body_base64: 'e30=', extra: true },
    { ...envelope, op: 'activate', expected_active: null, expected_epoch: 0, extra: true },
    { ...envelope, op: 'restore', expected_active: null, expected_epoch: 0, extra: true },
  ];
  for (const body of bodies) {
    let dbCalls = 0;
    const db = new Proxy({}, { get() { dbCalls++; throw new Error('unexpected DB access'); } });
    const result = await handleSnapshotWriter(request(JSON.stringify(body)), { ...environment, DB: db }, executeSnapshotOperation);
    assert.equal(result.status, 400);
    assert.equal(dbCalls, 0);
    assert.equal((await result.text()).includes(token), false);
  }
});

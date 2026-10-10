import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

test('public reader denies maintenance without reading request or importing writer capabilities', async () => {
  const source = readFileSync(new URL('../sites-worker/api/maintenance/snapshot/route.js', import.meta.url), 'utf8');
  assert.doesNotMatch(source, /^import\s/m);
  const route = await import(`data:text/javascript;base64,${Buffer.from(source).toString('base64')}`);
  let accesses = 0;
  const inaccessible = new Proxy({}, { get() { accesses++; throw new Error('CAPABILITY_ACCESSED'); } });
  for (const method of ['POST', 'GET', 'PUT', 'PATCH', 'DELETE', 'OPTIONS', 'HEAD']) {
    const response = route[method](inaccessible, inaccessible);
    assert.equal(response.status, 404);
    assert.equal(response.headers.get('cache-control'), 'no-store');
    assert.deepEqual(await response.json(), { error: 'MAINTENANCE_DISABLED' });
  }
  assert.equal(accesses, 0);
});

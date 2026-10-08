// Finite maintenance client. The credential is stdin only; never an option, file,
// URL, output or persisted receipt. Production requests stay on the exact origin.
import { readFileSync, createReadStream } from 'node:fs';
import { createInterface } from 'node:readline';
import { parseArgs } from 'node:util';
import { resolve, join } from 'node:path';
import { digest } from './snapshot-protocol.mjs';

const { values } = parseArgs({ options: {
  origin: { type: 'string' }, projection: { type: 'string' },
  action: { type: 'string', default: 'load' },
  'expected-active': { type: 'string' }, 'expected-epoch': { type: 'string' },
  'local-rehearsal': { type: 'boolean', default: false },
} });
async function main() {
  const origin = new URL(values.origin);
  const local = values['local-rehearsal'] && origin.protocol === 'http:' && ['127.0.0.1','localhost','[::1]'].includes(origin.hostname);
  const hosted = !values['local-rehearsal'] && origin.protocol === 'https:' && origin.hostname === 'moduigukgam.leeje92.chatgpt.site';
  if ((!local && !hosted) || origin.username || origin.password || origin.pathname !== '/' || origin.search || origin.hash) throw new Error('INVALID_ORIGIN');
  const secret = readFileSync(0, 'utf8').replace(/\r?\n$/, '');
  if (secret.length < 32 || secret.length > 256 || /[\r\n]/.test(secret)) throw new Error('INVALID_STDIN_CREDENTIAL');
  const directory = resolve(values.projection);
  const manifest = JSON.parse(readFileSync(join(directory, 'writer-manifest.json'), 'utf8'));
  if (digest(manifest.scope_json) !== manifest.manifest_sha256 || Buffer.byteLength(manifest.scope_json) !== manifest.metadata_bytes) throw new Error('LOCAL_MANIFEST_HASH_MISMATCH');
  const scope = JSON.parse(manifest.scope_json), w = scope.writer;
  const base = { version: 1, snapshot_id: manifest.snapshot_id, manifest_sha256: manifest.manifest_sha256 };
  async function call(op, fields = {}) {
    const body = JSON.stringify({ ...base, op, ...fields });
    for (let attempt = 0; attempt < 3; attempt++) {
      let result;
      try {
        const response = await fetch(new URL('/api/maintenance/snapshot', origin), {
          method: 'POST', redirect: 'error', signal: AbortSignal.timeout(45_000),
          headers: { authorization: `Bearer ${secret}`, 'content-type': 'application/json' }, body,
        });
        result = await response.json();
        if (!response.ok) throw new Error(`REMOTE_STATUS_${response.status}`);
        if (result.snapshot_id !== base.snapshot_id || result.manifest_sha256 !== base.manifest_sha256) throw new Error('REMOTE_RECEIPT_MISMATCH');
        return result;
      } catch (error) {
        if (result || attempt === 2) throw new Error(error.message?.startsWith('REMOTE_') ? error.message : 'TRANSPORT_FAILED');
        // Retrying the same finite request uses committed cursors and exact hashes;
        // no new operation is inferred from a lost HTTP response.
      }
    }
  }
  let receipt;
  if (values.action === 'load') {
    receipt = await call('begin', { metadata: {
      projection_schema_version: w.projection_schema_version, generated_at: w.generated_at,
      generated_at_kst: w.generated_at_kst, git_commit: w.git_commit,
      path_count: w.counts.paths, part_count: w.counts.parts,
      public_people: w.counts.public_people, public_organizations: w.counts.public_organizations,
    } });
    let offset = 0;
    const characters = [...manifest.scope_json];
    for (let index = 0; index < characters.length; index += 16_000) {
      const chunk = characters.slice(index, index + 16_000).join('');
      receipt = await call('metadata', { offset, chunk }); offset += Buffer.byteLength(chunk);
    }
    receipt = await call('manifest');
    for await (const line of createInterface({ input: createReadStream(join(directory, 'writer-parts.ndjson')), crlfDelay: Infinity })) {
      if (!line) continue;
      const part = JSON.parse(line);
      if (part.ordinal < receipt.cursor) continue;
      receipt = await call('part', part);
      if (receipt.cursor % 100 === 0) console.log(JSON.stringify({ phase: receipt.phase, cursor: receipt.cursor }));
    }
    receipt = await call('seal');
    for (let ordinal = receipt.validation_cursor; ordinal < w.counts.paths; ordinal++) receipt = await call('validate', { ordinal });
    if (receipt.phase !== 'VALIDATED' || receipt.validation_cursor !== w.counts.paths) throw new Error('VALIDATION_POSTCONDITION_FAILED');
  } else if (['activate', 'restore'].includes(values.action)) {
    const expectedActive = values['expected-active'] === 'NONE' ? null : values['expected-active'];
    const expectedEpoch = Number(values['expected-epoch']);
    if (expectedActive === undefined || values['expected-epoch'] === undefined || !Number.isSafeInteger(expectedEpoch)) throw new Error('EXPECTED_POINTER_REQUIRED');
    const expected = { expected_active: expectedActive, expected_epoch: expectedEpoch };
    if (values.action === 'restore') {
      receipt = await call('restore', { ...expected, mode: 'prepare' });
      if (receipt.status !== 'ACTIVE') {
        for (let ordinal = receipt.validation_cursor; ordinal < w.counts.paths; ordinal++) receipt = await call('restore', { ...expected, mode: 'validate', ordinal });
        receipt = await call('restore', { ...expected, mode: 'activate' });
      }
    } else receipt = await call('activate', expected);
    if (receipt.status !== 'ACTIVE' || receipt.pointer_epoch !== expectedEpoch + 1) throw new Error('POINTER_POSTCONDITION_FAILED');
  } else if (values.action === 'state') receipt = await call('state');
  else throw new Error('INVALID_ACTION');
  console.log(JSON.stringify({ result: 'PASS', ...receipt }));
}
main().catch((error) => { console.error(`SNAPSHOT_UPLOAD_FAILED: ${/^[A-Z0-9_]+$/.test(error.message) ? error.message : 'INVALID_INPUT_OR_TRANSPORT'}`); process.exitCode = 1; });

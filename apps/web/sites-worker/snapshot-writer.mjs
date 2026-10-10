// Worker-only maintenance transport. This is not canonical publication authority.
export const BODY_LIMIT = 128 * 1024;
const HASH = /^[0-9a-f]{64}$/;
const SNAPSHOT = /^ps-[0-9a-f]{16}$/;
const encoder = new TextEncoder();

export class WriterError extends Error {
  constructor(code, status = 409) { super(code); this.code = code; this.status = status; }
}
export const reject = (code, status) => { throw new WriterError(code, status); };
export async function sha256(bytes) {
  return [...new Uint8Array(await crypto.subtle.digest('SHA-256', bytes))]
    .map((byte) => byte.toString(16).padStart(2, '0')).join('');
}

// Both inputs are digested before the fixed-length comparison. Missing secrets fail
// closed. Never log headers, bodies, exception details or the configured secret.
export async function authorized(request, secret) {
  if (typeof secret !== 'string' || secret.length < 32 || secret.length > 256) return false;
  const header = request.headers.get('authorization') ?? '';
  if (!header.startsWith('Bearer ') || header.length > 263) return false;
  const [actual, expected] = await Promise.all([
    crypto.subtle.digest('SHA-256', encoder.encode(header.slice(7))),
    crypto.subtle.digest('SHA-256', encoder.encode(secret)),
  ]);
  const a = new Uint8Array(actual), b = new Uint8Array(expected);
  let difference = 0;
  for (let index = 0; index < 32; index++) difference |= a[index] ^ b[index];
  return difference === 0;
}

export async function readBoundedJson(request) {
  if (request.headers.get('content-type')?.split(';')[0].trim() !== 'application/json') reject('INVALID_CONTENT_TYPE', 415);
  const declared = request.headers.get('content-length');
  if (declared !== null && (!/^\d+$/.test(declared) || Number(declared) > BODY_LIMIT)) reject('BODY_TOO_LARGE', 413);
  if (!request.body) reject('INVALID_BODY', 400);
  const reader = request.body.getReader();
  const chunks = [];
  let length = 0;
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      length += value.byteLength;
      if (length > BODY_LIMIT) { await reader.cancel(); reject('BODY_TOO_LARGE', 413); }
      chunks.push(value);
    }
  } finally { reader.releaseLock(); }
  const bytes = new Uint8Array(length);
  let offset = 0;
  for (const chunk of chunks) { bytes.set(chunk, offset); offset += chunk.length; }
  try {
    const text = new TextDecoder('utf-8', { fatal: true }).decode(bytes);
    const parsed = JSON.parse(text);
    // Finite uploader emits this exact encoding: duplicate keys and alternate
    // numeric encodings cannot silently change the hash-bound request meaning.
    if (text !== JSON.stringify(parsed)) reject('NONCANONICAL_JSON', 400);
    return parsed;
  }
  catch { reject('INVALID_JSON', 400); }
}

export function strictObject(value, keys) {
  if (!value || Array.isArray(value) || typeof value !== 'object' ||
      Object.keys(value).some((key) => !keys.includes(key))) reject('INVALID_FIELDS', 400);
}
export function envelope(value) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) reject('INVALID_ENVELOPE', 400);
  if (value.version !== 1 || typeof value.snapshot_id !== 'string' || typeof value.manifest_sha256 !== 'string' ||
      !SNAPSHOT.test(value.snapshot_id) || !HASH.test(value.manifest_sha256)) reject('INVALID_ENVELOPE', 400);
}

export function response(value, status = 200) {
  return Response.json(value, { status, headers: { 'cache-control': 'no-store' } });
}

export async function handleSnapshotWriter(request, environment, execute) {
  // No body parsing or DB access before authentication and method validation.
  if (request.method !== 'POST') return response({ error: 'METHOD_NOT_ALLOWED' }, 405);
  if (!await authorized(request, environment.CIVIC_SNAPSHOT_WRITER_SECRET)) return response({ error: 'UNAUTHORIZED' }, 401);
  try {
    const body = await readBoundedJson(request);
    envelope(body);
    // Authentication is maintenance access, not permission to publish an arbitrary
    // snapshot. Deployment configuration must independently pin the reviewed bytes.
    const currentApproved = HASH.test(environment.CIVIC_SNAPSHOT_MANIFEST_SHA256 ?? '') &&
      body.manifest_sha256 === environment.CIVIC_SNAPSHOT_MANIFEST_SHA256;
    const previousApproved = ['state', 'restore'].includes(body.op) &&
      HASH.test(environment.CIVIC_SNAPSHOT_PREVIOUS_MANIFEST_SHA256 ?? '') &&
      body.manifest_sha256 === environment.CIVIC_SNAPSHOT_PREVIOUS_MANIFEST_SHA256;
    if (!currentApproved && !previousApproved) reject('SNAPSHOT_NOT_APPROVED', 403);
    if (!environment.DB) reject('WRITER_UNAVAILABLE', 503);
    return response(await execute(body, environment.DB));
  } catch (error) {
    return response({ error: error instanceof WriterError ? error.code : 'WRITER_FAILED' },
      error instanceof WriterError ? error.status : 500);
  }
}

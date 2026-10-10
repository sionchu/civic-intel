import { envelope, reject, sha256, strictObject, WriterError } from './snapshot-writer.mjs';
import { PERSON_RELATIONSHIP_QUERY } from '../app/relationship-path.mjs';
import { EMAIL, forbiddenToken } from '../scripts/public-boundary.mjs';
import { SCOPES } from '../scripts/snapshot-scopes.mjs';

const enc = new TextEncoder();
const hash = /^[0-9a-f]{64}$/;
const integer = (value, maximum) => Number.isSafeInteger(value) && value >= 0 && value <= maximum;
const common = ['version', 'snapshot_id', 'manifest_sha256', 'op'];
const uuid = '[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}';
const fixedPaths = new Set(['/people', '/organizations', '/gukgam/2026/targets', '/gukgam/2026/committees', '/gukgam/2026/witnesses']);
const allowedPath = (path) => typeof path === 'string' && !/[\r\n]/.test(path) && (fixedPaths.has(path) || new RegExp(`^/(?:people|organizations|sources|ontology/people|ontology/organizations)/${uuid}$`).test(path) ||
  new RegExp(`^/organizations/${uuid}/money\\?earlier_fiscal_year=2024&later_fiscal_year=2025$`).test(path) ||
  new RegExp(`^/relationships/people/${uuid}\\?${PERSON_RELATIONSHIP_QUERY}$`).test(path));

async function manifestFor(row, body) {
  if (await sha256(enc.encode(row.scope_json)) !== body.manifest_sha256) reject('MANIFEST_HASH_MISMATCH');
  let scope;
  try { scope = JSON.parse(row.scope_json); } catch { reject('INVALID_MANIFEST', 400); }
  if (JSON.stringify(scope) !== row.scope_json) reject('INVALID_MANIFEST', 400);
  strictObject(scope, ['patterns', 'paths', 'writer']);
  const writer = scope.writer;
  strictObject(writer, ['version', 'snapshot_id', 'semantic_sha256', 'projection_schema_version', 'generated_at', 'generated_at_kst', 'git_commit', 'counts']);
  if (writer.version !== 1 || writer.snapshot_id !== row.snapshot_id || !hash.test(writer.semantic_sha256) ||
      writer.snapshot_id !== `ps-${writer.semantic_sha256.slice(0, 16)}` ||
      writer.projection_schema_version !== row.projection_schema_version || writer.generated_at !== row.generated_at ||
      writer.generated_at_kst !== row.generated_at_kst || writer.git_commit !== row.git_commit ||
      writer.counts.paths !== row.path_count || writer.counts.parts !== row.part_count ||
      writer.counts.public_people !== row.public_people || writer.counts.public_organizations !== row.public_organizations ||
      JSON.stringify(scope.patterns) !== JSON.stringify(SCOPES) ||
      !scope.paths || Array.isArray(scope.paths) || typeof scope.paths !== 'object') reject('INVALID_MANIFEST', 400);
  const paths = Object.entries(scope.paths);
  let count = 0, prior = '';
  for (const [path, tuple] of paths) {
    if (!allowedPath(path) || path <= prior || !Array.isArray(tuple) || tuple.length !== 5 ||
        ![200, 404, 422].includes(tuple[0]) || (tuple[0] !== 200 && !path.includes('/money?')) ||
        !hash.test(tuple[1]) || !integer(tuple[2], 16 * 1024 * 1024) || !integer(tuple[3], 8 * 1024 * 1024) ||
        !Array.isArray(tuple[4]) || tuple[4].length !== Math.ceil(tuple[3] / 40_000) ||
        tuple[4].some((digest) => !hash.test(digest))) reject('INVALID_MANIFEST', 400);
    count += tuple[4].length; prior = path;
  }
  const semantic = { semantics: 'REPLACEABLE_PUBLIC_READ_SNAPSHOT_NOT_SSOT', projection_schema_version: 2,
    scopes: scope.patterns, rows: paths.map(([path, tuple]) => [path, tuple[0], tuple[1]]) };
  if (paths.length !== row.path_count || count !== row.part_count ||
      await sha256(enc.encode(JSON.stringify(semantic))) !== writer.semantic_sha256) reject('INVALID_MANIFEST', 400);
  return { scope, paths };
}
const statement = (db, sql, ...values) => db.prepare(sql).bind(...values);
const assertion = (db, condition, values = []) => statement(db,
  `SELECT CASE WHEN ${condition} THEN 1 ELSE json('WRITER_CONFLICT') END`, ...values);
async function atomic(db, statements) {
  try { return await db.batch(statements); }
  catch { throw new WriterError('STATE_CONFLICT'); }
}
async function state(db, body) {
  const row = await statement(db, `SELECT snapshot_id,status,projection_schema_version,generated_at,generated_at_kst,git_commit,path_count,part_count,public_people,public_organizations,writer_manifest_sha256,writer_phase,writer_cursor,validation_cursor,pointer_epoch,writer_transition_sha256 FROM snapshot_meta WHERE snapshot_id = ?`, body.snapshot_id).first();
  if (!row || row.writer_manifest_sha256 !== body.manifest_sha256) reject('STATE_CONFLICT');
  return row;
}
const receipt = (row) => ({ snapshot_id: row.snapshot_id, manifest_sha256: row.writer_manifest_sha256,
  status: row.status, phase: row.writer_phase, cursor: row.writer_cursor,
  validation_cursor: row.validation_cursor, pointer_epoch: row.pointer_epoch });
const receiptQuery=(db,id)=>statement(db,'SELECT snapshot_id,writer_manifest_sha256,status,writer_phase,writer_cursor,validation_cursor,pointer_epoch FROM snapshot_meta WHERE snapshot_id=?',id);
async function withManifest(db, row) {
  const result = await statement(db, 'SELECT scope_json FROM snapshot_meta WHERE snapshot_id=?', row.snapshot_id).first();
  return { ...row, scope_json: result.scope_json };
}
function expectedPointer(body) {
  if ((body.expected_active !== null && (typeof body.expected_active !== 'string' || !/^ps-[0-9a-f]{16}$/.test(body.expected_active))) ||
      !integer(body.expected_epoch, Number.MAX_SAFE_INTEGER - 1)) reject('INVALID_POINTER', 400);
  return body.expected_active === null
    ? { condition: `(SELECT COUNT(*) FROM snapshot_meta WHERE status='ACTIVE')=0 AND (SELECT COALESCE(MAX(pointer_epoch),0) FROM snapshot_meta)=?`, values:[body.expected_epoch] }
    : { condition: `(SELECT COUNT(*) FROM snapshot_meta WHERE status='ACTIVE')=1 AND EXISTS(SELECT 1 FROM snapshot_meta WHERE status='ACTIVE' AND snapshot_id=? AND pointer_epoch=?)`, values:[body.expected_active,body.expected_epoch] };
}
const transitionFor = (body) => sha256(enc.encode(JSON.stringify([body.op, body.expected_active, body.expected_epoch])));

export async function executeSnapshotOperation(body, db) {
  envelope(body);
  if (body.op === 'begin') {
    strictObject(body, [...common, 'metadata']);
    const m = body.metadata;
    strictObject(m, ['projection_schema_version', 'generated_at', 'generated_at_kst', 'git_commit', 'path_count', 'part_count', 'public_people', 'public_organizations']);
    if (m.projection_schema_version !== 2 || !integer(m.path_count, 100_000) || !integer(m.part_count, 200_000) ||
        !integer(m.public_people, 100_000) || !integer(m.public_organizations, 100_000) ||
        typeof m.generated_at !== 'string' || m.generated_at.length > 40 || !Number.isFinite(Date.parse(m.generated_at)) ||
        typeof m.generated_at_kst !== 'string' || m.generated_at_kst.length > 40 ||
        typeof m.git_commit !== 'string' || !/^(?:[0-9a-f]{40}|UNKNOWN)$/.test(m.git_commit)) reject('INVALID_METADATA', 400);
    await atomic(db, [statement(db, `INSERT INTO snapshot_meta
      (snapshot_id,status,projection_schema_version,generated_at,generated_at_kst,git_commit,scope_json,path_count,part_count,public_people,public_organizations,writer_manifest_sha256,writer_phase)
      VALUES (?,'STAGED',?,?,?,?, '',?,?,?,?,?,'METADATA') ON CONFLICT DO NOTHING`,
    body.snapshot_id, m.projection_schema_version, m.generated_at, m.generated_at_kst, m.git_commit,
    m.path_count, m.part_count, m.public_people, m.public_organizations, body.manifest_sha256),
    assertion(db, `EXISTS(SELECT 1 FROM snapshot_meta WHERE snapshot_id=? AND writer_manifest_sha256=?
      AND projection_schema_version=? AND generated_at=? AND generated_at_kst=? AND git_commit=?
      AND path_count=? AND part_count=? AND public_people=? AND public_organizations=?)`,
    [body.snapshot_id, body.manifest_sha256, m.projection_schema_version, m.generated_at, m.generated_at_kst,
      m.git_commit, m.path_count, m.part_count, m.public_people, m.public_organizations])]);
    return receipt(await state(db, body));
  }
  if (body.op === 'state') {
    strictObject(body, common);
    return receipt(await state(db, body));
  }
  if (body.op === 'manifest') {
    strictObject(body, common);
    const row = await withManifest(db, await state(db, body));
    await manifestFor(row, body);
    if (row.writer_phase !== 'METADATA') return receipt(row);
    await atomic(db, [assertion(db, `EXISTS(SELECT 1 FROM snapshot_meta WHERE snapshot_id=? AND writer_manifest_sha256=? AND status='STAGED' AND writer_phase='METADATA' AND scope_json=?)`,
      [body.snapshot_id, body.manifest_sha256, row.scope_json]),
    statement(db, "UPDATE snapshot_meta SET writer_phase='LOADING',writer_cursor=0 WHERE snapshot_id=?", body.snapshot_id)]);
    return receipt(await state(db, body));
  }
  if (body.op === 'part') {
    strictObject(body, [...common, 'ordinal', 'path', 'part', 'body_base64']);
    if (!integer(body.ordinal, 200_000) || typeof body.body_base64 !== 'string' ||
        !allowedPath(body.path) || !integer(body.part, 200_000) || body.body_base64.length > 53_336 || !/^[A-Za-z0-9+/]+={0,2}$/.test(body.body_base64)) reject('INVALID_PART', 400);
    let bytes;
    try {
      const binary = atob(body.body_base64);
      if (btoa(binary) !== body.body_base64) reject('INVALID_PART', 400);
      bytes = Uint8Array.from(binary, (letter) => letter.charCodeAt(0));
    } catch { reject('INVALID_PART', 400); }
    const row = await state(db, body);
    // Query only the immutable descriptor, not the entire 1.3 MB manifest on each
    // part. json_each reads the same canonical metadata; no auxiliary payload store.
    const selected = await statement(db, `SELECT j.value AS tuple_json,
      (SELECT COALESCE(SUM(json_array_length(p.value,'$[4]')),0) FROM snapshot_meta m,json_each(m.scope_json,'$.paths') p WHERE m.snapshot_id=? AND p.key<?) AS start_ordinal
      FROM snapshot_meta m,json_each(m.scope_json,'$.paths') j WHERE m.snapshot_id=? AND j.key=?`,
    body.snapshot_id, body.path, body.snapshot_id, body.path).first();
    if (!selected) reject('INVALID_PART', 400);
    const tuple = JSON.parse(selected.tuple_json), path = body.path, part = body.part;
    if (selected.start_ordinal + part !== body.ordinal || part >= tuple[4].length) reject('INVALID_PART', 400);
    if (bytes.length !== Math.min(40_000, tuple[3] - part * 40_000) ||
        await sha256(bytes) !== tuple[4][part]) reject('PART_HASH_MISMATCH');
    const equal = `EXISTS(SELECT 1 FROM public_read WHERE snapshot_id=? AND path=? AND part=? AND status=? AND content_sha256=? AND body_gzip=?)`;
    const equality = [body.snapshot_id, path, part, tuple[0], tuple[1], bytes];
    if (body.ordinal < row.writer_cursor) {
      await atomic(db, [assertion(db, equal, equality)]);
      return receipt(await state(db, body));
    }
    await atomic(db, [assertion(db, `EXISTS(SELECT 1 FROM snapshot_meta WHERE snapshot_id=? AND writer_manifest_sha256=? AND status='STAGED' AND writer_phase='LOADING' AND writer_cursor=?)`,
      [body.snapshot_id, body.manifest_sha256, body.ordinal]),
    statement(db, `INSERT INTO public_read(snapshot_id,path,part,status,content_sha256,body_gzip) VALUES(?,?,?,?,?,?) ON CONFLICT DO NOTHING`, ...equality),
    assertion(db, equal, equality),
    statement(db, 'UPDATE snapshot_meta SET writer_cursor=writer_cursor+1 WHERE snapshot_id=?', body.snapshot_id)]);
    return receipt(await state(db, body));
  }
  if (body.op === 'seal') {
    strictObject(body, common);
    const row = await withManifest(db, await state(db, body));
    await manifestFor(row, body);
    if (['SEALED', 'VALIDATED'].includes(row.writer_phase)) return receipt(row);
    await atomic(db, [assertion(db, `EXISTS(SELECT 1 FROM snapshot_meta WHERE snapshot_id=? AND writer_manifest_sha256=? AND status='STAGED' AND writer_phase='LOADING' AND writer_cursor=part_count)
      AND (SELECT COUNT(*) FROM public_read WHERE snapshot_id=?)=?`, [body.snapshot_id, body.manifest_sha256, body.snapshot_id, row.part_count]),
    statement(db, "UPDATE snapshot_meta SET writer_phase='SEALED' WHERE snapshot_id=?", body.snapshot_id)]);
    return receipt(await state(db, body));
  }
  if (body.op === 'restore' && body.mode === 'prepare') {
    strictObject(body,[...common,'mode','expected_active','expected_epoch']);
    const pointer=expectedPointer(body);
    if(body.expected_active===null)reject('INVALID_POINTER',400);
    const row=await withManifest(db,await state(db,body));await manifestFor(row,body);
    const transition=await transitionFor(body);
    if(row.status==='ACTIVE'&&row.pointer_epoch===body.expected_epoch+1&&row.writer_transition_sha256===transition){
      const confirmed=await atomic(db,[assertion(db,`(SELECT COUNT(*) FROM snapshot_meta WHERE status='ACTIVE')=1 AND
        EXISTS(SELECT 1 FROM snapshot_meta WHERE snapshot_id=? AND status='ACTIVE' AND pointer_epoch=? AND writer_transition_sha256=?)`,
        [body.snapshot_id,body.expected_epoch+1,transition]),receiptQuery(db,body.snapshot_id)]);
      return receipt(confirmed.at(-1).results[0]);
    }
    if(row.status!=='PREVIOUS'||!['VALIDATED','RESTORE_SEALED','RESTORE_VALIDATED'].includes(row.writer_phase)||row.writer_cursor!==row.part_count)reject('STATE_CONFLICT');
    await atomic(db,[assertion(db,pointer.condition,pointer.values)]);
    if(['RESTORE_SEALED','RESTORE_VALIDATED'].includes(row.writer_phase)&&row.writer_transition_sha256===transition)return receipt(row);
    await atomic(db,[assertion(db,`${pointer.condition} AND EXISTS(SELECT 1 FROM snapshot_meta WHERE snapshot_id=? AND status='PREVIOUS' AND writer_manifest_sha256=?)`,[...pointer.values,body.snapshot_id,body.manifest_sha256]),
      statement(db,"UPDATE snapshot_meta SET writer_phase='RESTORE_SEALED',validation_cursor=0,writer_transition_sha256=? WHERE snapshot_id=?",transition,body.snapshot_id)]);
    return receipt(await state(db,body));
  }
  if (body.op === 'validate' || (body.op === 'restore' && body.mode === 'validate')) {
    const restoring=body.op==='restore';
    strictObject(body, [...common, 'ordinal', ...(restoring?['mode','expected_active','expected_epoch']:[])]);
    const pointer=restoring?expectedPointer(body):null;
    const transition=restoring?await transitionFor(body):null;
    if (!integer(body.ordinal, 100_000)) reject('INVALID_CURSOR', 400);
    const row = await state(db, body);
    if (!(restoring?['RESTORE_SEALED','RESTORE_VALIDATED']:['SEALED','VALIDATED']).includes(row.writer_phase) ||
        (restoring&&(row.status!=='PREVIOUS'||row.writer_transition_sha256!==transition))) reject('STATE_CONFLICT');
    if(restoring)await atomic(db,[assertion(db,pointer.condition,pointer.values)]);
    if (body.ordinal < row.validation_cursor) return receipt(row);
    const selected = await statement(db, `SELECT j.key AS path,j.value AS tuple_json FROM snapshot_meta m,json_each(m.scope_json,'$.paths') j WHERE m.snapshot_id=? ORDER BY j.key LIMIT 1 OFFSET ?`, body.snapshot_id, body.ordinal).first();
    if (!selected) reject('INVALID_CURSOR', 400);
    const path = selected.path, tuple = JSON.parse(selected.tuple_json);
    const result = await statement(db, 'SELECT part,status,content_sha256,body_gzip FROM public_read WHERE snapshot_id=? AND path=? ORDER BY part', body.snapshot_id, path).all();
    const parts = result.results;
    if (parts.length !== tuple[4].length) reject('INCOMPLETE_RESPONSE');
    const chunks = [];
    for (let index = 0; index < parts.length; index++) {
      const part = parts[index];
      const bytes = new Uint8Array(part.body_gzip);
      if (part.part !== index || part.status !== tuple[0] || part.content_sha256 !== tuple[1] ||
          bytes.length !== Math.min(40_000, tuple[3] - index * 40_000) || await sha256(bytes) !== tuple[4][index]) reject('CORRUPT_RESPONSE');
      chunks.push(bytes);
    }
    const reader = new Blob(chunks).stream().pipeThrough(new DecompressionStream('gzip')).getReader();
    const decoded = []; let length = 0;
    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        length += value.byteLength;
        if (length > tuple[2]) { await reader.cancel(); reject('CORRUPT_RESPONSE'); }
        decoded.push(value);
      }
    } catch { reject('CORRUPT_RESPONSE'); }
    finally { reader.releaseLock(); }
    const bytes = new Uint8Array(length); let offset = 0;
    for (const chunk of decoded) { bytes.set(chunk, offset); offset += chunk.length; }
    if (length !== tuple[2] || await sha256(bytes) !== tuple[1]) reject('CORRUPT_RESPONSE');
    let text;
    try { text = new TextDecoder('utf-8', { fatal: true }).decode(bytes); JSON.parse(text); }
    catch { reject('CORRUPT_RESPONSE'); }
    if (EMAIL.test(text) || forbiddenToken(text)) reject('PUBLIC_BOUNDARY_REJECTED');
    const guard=restoring?`${pointer.condition} AND `:'';
    await atomic(db, [assertion(db, `${guard}EXISTS(SELECT 1 FROM snapshot_meta WHERE snapshot_id=? AND writer_manifest_sha256=? AND status=? AND writer_phase=? AND validation_cursor=?)`,
      [...(restoring?pointer.values:[]),body.snapshot_id, body.manifest_sha256,restoring?'PREVIOUS':'STAGED',restoring?'RESTORE_SEALED':'SEALED',body.ordinal]),
    statement(db, `UPDATE snapshot_meta SET validation_cursor=validation_cursor+1,writer_phase=CASE WHEN validation_cursor+1=path_count THEN ? ELSE ? END WHERE snapshot_id=?`,
      restoring?'RESTORE_VALIDATED':'VALIDATED',restoring?'RESTORE_SEALED':'SEALED',body.snapshot_id)]);
    return receipt(await state(db, body));
  }
  if (body.op === 'activate' || body.op === 'restore') {
    strictObject(body, [...common, 'expected_active', 'expected_epoch', ...(body.op==='restore'?['mode']:[])]);
    if(body.op==='restore'&&body.mode!=='activate')reject('INVALID_OPERATION',400);
    const pointer=expectedPointer(body);
    const row = await withManifest(db, await state(db, body));
    await manifestFor(row, body);
    const transition = await transitionFor(body);
    // A response-loss retry only confirms the immediately resulting epoch. A later
    // cutover, even to the same snapshot, never authorizes resurrection of old state.
    if (row.status === 'ACTIVE' && row.pointer_epoch === body.expected_epoch + 1 && row.writer_transition_sha256 === transition) {
      const confirmed=await atomic(db, [assertion(db, `(SELECT COUNT(*) FROM snapshot_meta WHERE status='ACTIVE')=1 AND
        EXISTS(SELECT 1 FROM snapshot_meta WHERE status='ACTIVE' AND snapshot_id=? AND pointer_epoch=? AND writer_transition_sha256=?)`,
      [body.snapshot_id, body.expected_epoch + 1,transition]),receiptQuery(db,body.snapshot_id)]);
      return receipt(confirmed.at(-1).results[0]);
    }
    const targetStatus = body.op === 'activate' ? 'STAGED' : 'PREVIOUS';
    const phase=body.op==='restore'?'RESTORE_VALIDATED':'VALIDATED';
    if(body.op==='restore'&&row.writer_transition_sha256!==transition)reject('STATE_CONFLICT');
    const committed = await atomic(db, [assertion(db, `${pointer.condition} AND EXISTS(SELECT 1 FROM snapshot_meta WHERE snapshot_id=? AND writer_manifest_sha256=? AND status=? AND writer_phase=? AND validation_cursor=path_count AND writer_cursor=part_count)`,
      [...pointer.values, body.snapshot_id, body.manifest_sha256, targetStatus,phase]),
    // Retain retired snapshots so an already pinned reader can finish. GC is a
    // separate bounded operation and is deliberately absent from this endpoint.
    statement(db, "UPDATE snapshot_meta SET status='RETIRED' WHERE status='PREVIOUS' AND snapshot_id<>?", body.snapshot_id),
    statement(db, "UPDATE snapshot_meta SET status='PREVIOUS' WHERE status='ACTIVE'"),
    statement(db, "UPDATE snapshot_meta SET status='ACTIVE',writer_phase='VALIDATED',pointer_epoch=?,writer_transition_sha256=? WHERE snapshot_id=?", body.expected_epoch + 1, transition, body.snapshot_id),
    assertion(db, `(SELECT COUNT(*) FROM snapshot_meta WHERE status='ACTIVE')=1 AND EXISTS(SELECT 1 FROM snapshot_meta WHERE snapshot_id=? AND status='ACTIVE' AND pointer_epoch=?)`,
      [body.snapshot_id, body.expected_epoch + 1]),
    receiptQuery(db,body.snapshot_id)]);
    return receipt(committed.at(-1).results[0]);
  }
  if (body.op === 'metadata') {
    strictObject(body, [...common, 'offset', 'chunk']);
    if (!integer(body.offset, 1_900_000) || typeof body.chunk !== 'string' || !body.chunk.length ||
        enc.encode(body.chunk).length > 60_000) reject('INVALID_METADATA_CHUNK', 400);
    const row = await withManifest(db, await state(db, body));
    const bytes = enc.encode(row.scope_json), chunk = enc.encode(body.chunk);
    if (body.offset < bytes.length) {
      const prior = bytes.slice(body.offset, body.offset + chunk.length);
      if (await sha256(prior) !== await sha256(chunk)) reject('STATE_CONFLICT');
      return receipt(row);
    }
    if (bytes.length + chunk.length > 1_900_000) reject('METADATA_TOO_LARGE', 413);
    await atomic(db, [assertion(db, `EXISTS(SELECT 1 FROM snapshot_meta WHERE snapshot_id=? AND writer_manifest_sha256=?
      AND status='STAGED' AND writer_phase='METADATA' AND length(CAST(scope_json AS BLOB))=?)`,
    [body.snapshot_id, body.manifest_sha256, body.offset]),
    statement(db, 'UPDATE snapshot_meta SET scope_json=scope_json||? WHERE snapshot_id=?', body.chunk, body.snapshot_id)]);
    return receipt(await state(db, body));
  }
  reject('INVALID_OPERATION', 400);
}

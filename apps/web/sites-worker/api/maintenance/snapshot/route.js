import { env } from 'cloudflare:workers';
import { handleSnapshotWriter } from '../../../../sites-worker/snapshot-writer.mjs';
import { executeSnapshotOperation } from '../../../../sites-worker/snapshot-operations.mjs';

export const dynamic = 'force-dynamic';
export function POST(request) {
  return handleSnapshotWriter(request, env, executeSnapshotOperation);
}

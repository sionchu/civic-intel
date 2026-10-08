// The public reader never dispatches maintenance, regardless of retained runtime
// secrets. The explicit bootstrap builder owns the authenticated writer instead.
// Do not import environment, authorization, payload parsing or DB operations here.
export const dynamic = 'force-dynamic';
export function POST() {
  return new Response('{"error":"MAINTENANCE_DISABLED"}', {
    status: 404,
    headers: { 'content-type': 'application/json', 'cache-control': 'no-store' },
  });
}
export const GET = POST;
export const PUT = POST;
export const PATCH = POST;
export const DELETE = POST;
export const OPTIONS = POST;
export const HEAD = POST;

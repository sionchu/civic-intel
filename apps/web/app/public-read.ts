// Transport for the public read model. Every page reads the publication-gated API DTO by its API
// path through this one function. The server build and the static Sites snapshot read the private
// API over HTTP (this file); the D1-backed Sites Worker build swaps in
// `sites-worker/public-read.d1.ts`, which serves the same DTO bytes from an exported snapshot.
export type PublicReadResponse = {
  status: number;
  body: unknown;
  requestId: string | null;
};

const API = process.env.CIVIC_API_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function readPublic(
  path: string,
  options: { revalidateSeconds?: number } = {},
): Promise<PublicReadResponse> {
  const response = await fetch(
    `${API}${path}`,
    options.revalidateSeconds
      ? { next: { revalidate: options.revalidateSeconds } }
      : { cache: "no-store" },
  );
  return {
    status: response.status,
    // A success body that is not JSON throws, which the caller reports as a transport failure.
    body: response.ok ? await response.json() : await response.json().catch(() => null),
    requestId: response.headers.get("x-request-id"),
  };
}

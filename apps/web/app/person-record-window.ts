// Presentation windows over the unchanged, publication-gated canonical DTO.
// The server still reads the complete Person; only the selected records cross RSC.
export const RECORD_PAGE_SIZE = 20;
export type RecordQuery = Record<string, string>;
export function parseRecordQuery(input: Record<string, string | string[] | undefined>): RecordQuery {
  const result: RecordQuery = {};
  const pages = new Set(["bills", "other", "votes", "sources", "sectionPage"]);
  const allowed = new Set([...pages, "q", "vote_q", "committee", "section", "claim", "source", "v"]);
  for (const [key, value] of Object.entries(input)) {
    if (!allowed.has(key)) continue;
    if (value === undefined || value === "") continue;
    if (Array.isArray(value) || value.length > 160) throw new Error("INVALID_INPUT");
    if (pages.has(key) && (!/^[1-9][0-9]{0,5}$/.test(value))) throw new Error("INVALID_INPUT");
    if (key === "v" && !/^[a-f0-9]{64}$/.test(value)) throw new Error("INVALID_INPUT");
    if (["claim", "source", "section"].includes(key) && !/^[a-zA-Z0-9_-]{1,80}$/.test(value)) throw new Error("INVALID_INPUT");
    result[key] = value;
  }
  return result;
}
export function recordWindow<T>(items: T[], page = "1") {
  const current = Math.min(Number(page), Math.max(1, Math.ceil(items.length / RECORD_PAGE_SIZE)));
  const start = (current - 1) * RECORD_PAGE_SIZE;
  return { items: items.slice(start, start + RECORD_PAGE_SIZE), total: items.length, page: current, pages: Math.ceil(items.length / RECORD_PAGE_SIZE) };
}
export async function personReadVersion(...values: unknown[]): Promise<string> {
  const bytes = new TextEncoder().encode(JSON.stringify(values));
  return [...new Uint8Array(await crypto.subtle.digest("SHA-256", bytes))].map((byte) => byte.toString(16).padStart(2, "0")).join("");
}
export function recordHref(query: RecordQuery, change: RecordQuery, anchor: string) {
  const next = { ...query, ...change };
  delete next.claim; delete next.source;
  const params = new URLSearchParams(Object.entries(next).filter(([, value]) => value !== ""));
  return `?${params}#${anchor}`;
}

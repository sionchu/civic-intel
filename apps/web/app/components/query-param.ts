import { useState, useSyncExternalStore } from "react";

const subscribe = () => () => {};

function readQueryParam(): string {
  return (new URLSearchParams(window.location.search).get("q") ?? "").trim().slice(0, 80);
}

// Search text state seeded from ?q=. The server passes the query it saw; a prebuilt static snapshot
// sees none, so after hydration the browser URL supplies it until the reader types.
export function useQueryState(initialQuery: string): [string, (next: string) => void] {
  const urlQuery = useSyncExternalStore(subscribe, readQueryParam, () => initialQuery);
  const [edited, setEdited] = useState<string | null>(null);
  return [edited ?? (initialQuery || urlQuery), setEdited];
}

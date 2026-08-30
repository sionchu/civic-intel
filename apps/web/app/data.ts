import type { Person, Source } from "./types";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function getJson<T>(path: string, fallback: T): Promise<T> {
  try {
    const response = await fetch(`${API}${path}`, { cache: "no-store" });
    if (!response.ok) return fallback;
    return (await response.json()) as T;
  } catch {
    return fallback;
  }
}

export function getPeople(): Promise<Person[]> { return getJson("/people", []); }
export function getPerson(id: string): Promise<Person | null> { return getJson(`/people/${id}`, null); }
export function getSource(id: string): Promise<Source | null> { return getJson(`/sources/${id}`, null); }

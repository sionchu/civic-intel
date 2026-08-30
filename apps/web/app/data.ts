import type { Person, Source } from "./types";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const personId = "00000000-0000-0000-0000-000000000001";
const sourceId = "20000000-0000-0000-0000-000000000001";

const fixturePerson: Person = {
  id: personId,
  canonical_name: "Kim Min",
  identity_status: "RESOLVED",
  claims: [{
    id: "30000000-0000-0000-0000-000000000001",
    proposition: "Kim Min took office on 2 January 2026.",
    epistemic_status: "FACT",
    evidence: [{ id: "40000000-0000-0000-0000-000000000001", source_id: sourceId, stance: "SUPPORT", excerpt: "took office as Minister of Civic Affairs on 2 January 2026" }],
    source_ids: [sourceId],
  }],
};

const fixtureSource: Source = { id: sourceId, url: "https://example.gov/open-data/cabinet/kim-min", title: "Cabinet appointment notice: Kim Min", publisher: "Example Government", policy: { source_class: "official", license: "Open Government Licence", can_show_excerpt: true } };

async function getJson<T>(path: string, fallback: T): Promise<T> {
  try {
    const response = await fetch(`${API}${path}`, { cache: "no-store" });
    if (!response.ok) return fallback;
    return (await response.json()) as T;
  } catch {
    return fallback;
  }
}

export function getPeople(): Promise<Person[]> { return getJson("/people", [fixturePerson]); }
export function getPerson(id: string): Promise<Person | null> { return id === personId ? getJson(`/people/${id}`, fixturePerson) : getJson(`/people/${id}`, null); }
export function getSource(id: string): Promise<Source | null> { return id === sourceId ? getJson(`/sources/${id}`, fixtureSource) : getJson(`/sources/${id}`, null); }

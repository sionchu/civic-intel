import type { Claim, Person } from "../../types";

export const METHOD = "public-vote-record-intersection/1";
export const PAGE_SIZE = 20;
export type VoteRow = { key: string; claimId: string; billId: string; term: string; event: string; date: string; title: string; choice: string; sourceIds: string[] };
type Input = Pick<Person, "id" | "canonical_name" | "identity_status" | "claims">;

export function calendarDate(value: string): boolean {
  return /^\d{4}-\d{2}-\d{2}$/.test(value) && Number.isFinite(Date.parse(`${value}T00:00:00Z`)) && new Date(`${value}T00:00:00Z`).toISOString().slice(0, 10) === value;
}

function collect(person: Input, start: string, end: string) {
  const excluded = { invalid: 0, conflict: 0, duplicate: 0, outsidePeriod: 0 };
  const groups = new Map<string, VoteRow[]>();
  // A conflicting or otherwise ineligible published duplicate cannot leave its clean
  // counterpart looking unambiguous. Count event collisions before eligibility filtering.
  const occurrences = new Map<string, number>();
  for (const claim of person.claims ?? []) {
    const q = claim.qualifiers;
    if (claim.predicate !== "ASSEMBLY_PLENARY_VOTE" || claim.person_id !== person.id || claim.publication_status !== "PUBLISHED" || q.source_contract !== "assembly_plenary_roll_call_vote") continue;
    const key = JSON.stringify([q.assembly_age, q.bill_id, q.vote_datetime]);
    occurrences.set(key, (occurrences.get(key) ?? 0) + 1);
  }
  for (const claim of person.claims ?? []) {
    if (claim.predicate !== "ASSEMBLY_PLENARY_VOTE") continue;
    const q = claim.qualifiers;
    const supporting = claim.evidence.filter((e) => e.stance === "SUPPORT" && claim.source_ids.includes(e.source_id) && (!("claim_id" in e) || e.claim_id === claim.id));
    if (claim.person_id !== person.id || claim.publication_status !== "PUBLISHED" || !["FACT", "CLAIM"].includes(claim.epistemic_status) || q.source_contract !== "assembly_plenary_roll_call_vote" || supporting.length === 0) { excluded.invalid++; continue; }
    if (claim.source_conflict || claim.evidence.some((e) => e.stance === "REFUTE")) { excluded.conflict++; continue; }
    const event = q.vote_datetime ?? "";
    const date = event.slice(0, 10);
    if (!calendarDate(date) || !/^\d{4}-\d{2}-\d{2}[T ](?:[01]\d|2[0-3]):[0-5]\d:[0-5]\d(?:\.\d{1,6})?(?:Z|[+-](?:[01]\d|2[0-3]):[0-5]\d)?$/.test(event) || !/^\d{1,3}$/.test(q.assembly_age ?? "") || Number(q.assembly_age) < 1 || !q.bill_id?.trim() || !["찬성", "반대", "기권", "불참"].includes(q.vote_value_published)) { excluded.invalid++; continue; }
    if (date < start || date > end) { excluded.outsidePeriod++; continue; }
    const key = JSON.stringify([q.assembly_age, q.bill_id, event]);
    const row = { key, claimId: claim.id, billId: q.bill_id, term: q.assembly_age, event, date, title: claim.object_text, choice: q.vote_value_published, sourceIds: [...new Set(supporting.map((e) => e.source_id))].sort() };
    groups.set(key, [...(groups.get(key) ?? []), row]);
  }
  const records = new Map<string, VoteRow>();
  for (const [key, rows] of groups) {
    if (occurrences.get(key) !== 1) excluded.duplicate += rows.length;
    else records.set(key, rows[0]);
  }
  return { records, excluded };
}

export async function compareVotes(left: Input, right: Input, start: string, end: string) {
  if (left.id === right.id || left.identity_status !== "RESOLVED" || right.identity_status !== "RESOLVED") throw new Error("서로 다른 두 공개 인물을 선택해 주세요.");
  if (!calendarDate(start) || !calendarDate(end) || start > end) throw new Error("시작일과 종료일을 올바르게 입력해 주세요.");
  const a = collect(left, start, end), b = collect(right, start, end);
  const rows = [...a.records.values()].flatMap((l) => {
    const r = b.records.get(l.key);
    return r ? [{ left: l, right: r, different: l.choice !== r.choice }] : [];
  }).sort((x, y) => y.left.event.localeCompare(x.left.event) || x.left.key.localeCompare(y.left.key));
  // Pin the exact public input, including excluded/corrected evidence; never mix pages after drift.
  const claims = (p: Input) => (p.claims ?? []).filter((c) => c.predicate === "ASSEMBLY_PLENARY_VOTE").slice().sort((x, y) => x.id.localeCompare(y.id));
  const bytes = new TextEncoder().encode(JSON.stringify([METHOD, start, end, left.id, right.id, claims(left), claims(right)]));
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  const version = [...new Uint8Array(digest)].map((n) => n.toString(16).padStart(2, "0")).join("");
  return { method: METHOD, version, start, end, rows, common: rows.length, leftOnly: a.records.size - rows.length, rightOnly: b.records.size - rows.length, leftExcluded: a.excluded, rightExcluded: b.excluded };
}

export function evidenceHref(personId: string, claim: Pick<Claim, "id"> | VoteRow) {
  const id = "claimId" in claim ? claim.claimId : claim.id;
  return `/people/${encodeURIComponent(personId)}?claim=${encodeURIComponent(id)}#claim-${encodeURIComponent(id)}`;
}

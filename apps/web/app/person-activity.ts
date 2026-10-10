import type { Claim } from "./types";

export type OfficialVoteRecord = {
  claimId: string; billId: string; title: string; date: string | null;
  committee: string | null; choice: string; status: Claim["epistemic_status"];
  sourceIds: string[]; sourceConflict: boolean;
};

function exactCalendarDate(value: string | undefined) {
  return value && /^\d{4}-\d{2}-\d{2}$/.test(value) && Number.isFinite(Date.parse(value)) &&
    new Date(value).toISOString().slice(0, 10) === value ? value : null;
}

export function officialVoteRecords(person: { id: string; identity_status: string }, claims: Claim[]): OfficialVoteRecord[] {
  if (person.identity_status !== "RESOLVED") return [];
  const records = claims.flatMap((claim) => {
    const q = claim.qualifiers;
    const evidence = supportingActivityEvidence(claim);
    if (claim.person_id !== person.id || claim.publication_status !== "PUBLISHED" ||
      claim.epistemic_status === "ENTITY_UNRESOLVED" || claim.predicate !== "ASSEMBLY_PLENARY_VOTE" ||
      q.source_contract !== "assembly_plenary_roll_call_vote" || !q.bill_id?.trim() ||
      !["찬성", "반대", "기권", "불참"].includes(q.vote_value_published) || evidence.length === 0) return [];
    return [{ claimId: claim.id, billId: q.bill_id, title: claim.object_text,
      date: exactCalendarDate(q.vote_datetime?.match(/^\d{4}-\d{2}-\d{2}(?:T| )/)?.[0].slice(0, 10)),
      committee: q.committee?.trim() || null, choice: q.vote_value_published,
      status: claim.epistemic_status, sourceIds: [...new Set(evidence.map((item) => item.source_id))],
      sourceConflict: Boolean(claim.source_conflict) }];
  });
  return records.sort((a, b) => (b.date ?? "").localeCompare(a.date ?? "") || a.claimId.localeCompare(b.claimId));
}

// Retrieval over exact source fields; matching does not assert a topic or policy position.
export function selectVoteRecords(records: OfficialVoteRecord[], query: string, committee: string) {
  const term = query.trim().toLocaleLowerCase("ko-KR");
  return records.filter((record) => (!term || record.title.toLocaleLowerCase("ko-KR").includes(term)) &&
    (committee === "ALL" || (committee === "UNKNOWN" ? record.committee === null : record.committee === committee)));
}

export function supportingActivityEvidence(claim: Claim) {
  return claim.evidence.filter((item) => item.stance === "SUPPORT" &&
    claim.source_ids.includes(item.source_id) &&
    (!("claim_id" in item) || item.claim_id === claim.id));
}

// A bounded presentation index over the existing published Claim DTO, not a new truth store.
export function recentOfficialActivity(person: { id: string; identity_status: string }, claims: Claim[]) {
  if (person.identity_status !== "RESOLVED") return { items: [], datedCount: 0, undatedCount: 0 };
  const eligible = claims.flatMap((claim) => {
    if (claim.person_id !== person.id || claim.publication_status !== "PUBLISHED" ||
      claim.epistemic_status === "ENTITY_UNRESOLVED" ||
      supportingActivityEvidence(claim).length === 0) return [];
    const q = claim.qualifiers;
    let date: string | undefined;
    let action: string;
    if (claim.predicate === "ASSEMBLY_BILL_PARTICIPATION" && q.source_contract === "assembly_term_bill_participation") {
      if (!["REPRESENTATIVE_PROPOSER", "CO_PROPOSER"].includes(q.participation_role)) return [];
      date = q.proposed_date;
      action = q.participation_role === "REPRESENTATIVE_PROPOSER" ? "대표 발의" : "공동 발의";
    } else if (claim.predicate === "ASSEMBLY_PLENARY_VOTE" && q.source_contract === "assembly_plenary_roll_call_vote") {
      if (!["찬성", "반대", "기권", "불참"].includes(q.vote_value_published)) return [];
      date = q.vote_datetime?.match(/^\d{4}-\d{2}-\d{2}(?:T| )/)?.[0].slice(0, 10);
      action = `본회의 표결 · ${q.vote_value_published}`;
    } else return [];
    const validDate = exactCalendarDate(date);
    return [{ claim, date: validDate, action }];
  });
  const dated = eligible.filter((item): item is typeof item & { date: string } => item.date !== null);
  dated.sort((a, b) => b.date.localeCompare(a.date) || a.claim.id.localeCompare(b.claim.id));
  return { items: dated.slice(0, 8), datedCount: dated.length, undatedCount: eligible.length - dated.length };
}

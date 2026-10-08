import type { Claim } from "./types";

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
    const validDate = date && /^\d{4}-\d{2}-\d{2}$/.test(date) &&
      Number.isFinite(Date.parse(date)) && new Date(date).toISOString().slice(0, 10) === date ? date : null;
    return [{ claim, date: validDate, action }];
  });
  const dated = eligible.filter((item): item is typeof item & { date: string } => item.date !== null);
  dated.sort((a, b) => b.date.localeCompare(a.date) || a.claim.id.localeCompare(b.claim.id));
  return { items: dated.slice(0, 8), datedCount: dated.length, undatedCount: eligible.length - dated.length };
}

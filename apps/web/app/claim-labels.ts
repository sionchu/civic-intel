// Reader-facing Korean field labels for published Claim predicates. Presentation only: a label
// never changes a Claim's meaning, status or evidence, and an unmapped predicate falls back to a
// neutral label instead of exposing an internal code in the reading flow.

const PREDICATE_LABELS: Record<string, string> = {
  HELD_ROLE: "직위",
  ASSEMBLY_PARTY: "정당",
  ASSEMBLY_DISTRICT: "지역구",
  ASSEMBLY_COMMITTEES: "소속 위원회",
  ASSEMBLY_REELECTION: "선수",
  ASSEMBLY_BILL_PARTICIPATION: "법안 발의 참여",
  ALIO_REVIEWED_PERSON_ROLE: "공공기관 임원 공시",
  ALIO_CURRENT_EXECUTIVE_DISCLOSURE: "현재 임원 공시",
  ALIO_INSTITUTION_CLASSIFICATION: "ALIO 기관 분류",
  NEC_LOCAL_ELECTION_CANDIDACY: "지방선거 후보 등록",
  LISTED_AS_GUKGAM_AUDIT_TARGET: "2026 국정감사 피감대상",
  DISCLOSED_BUSINESS_EXPENSE: "업무추진비 공시",
  NOMINATED_AS: "지명",
  DESIGNATED_AS: "내정",
  APPOINTED_AS: "임명",
  APPOINTMENT_EFFECTIVE: "임명 효력",
  APPOINTMENT_RATIONALE: "발표된 임명 사유",
  HAS_REPUTATION: "발표문 속 평가 서술",
  BIRTH_DATE: "출생일",
  OPERATOR_REVIEWED_CORRECTION: "검토된 정정",
};

export const UNMAPPED_PREDICATE_LABEL = "기타 공개 기록";

export function predicateLabel(predicate: string): string {
  return PREDICATE_LABELS[predicate] ?? UNMAPPED_PREDICATE_LABEL;
}

// Latest Civic Intel recording time among the given Claims. This is when Civic Intel recorded the
// record, not when the underlying fact happened.
export function latestRecordedAt(claims: { recorded_at?: string | null }[]): string | null {
  let latest: { value: string; time: number } | null = null;
  for (const claim of claims) {
    const time = claim.recorded_at ? Date.parse(claim.recorded_at) : Number.NaN;
    if (!Number.isNaN(time) && (!latest || time > latest.time)) latest = { value: claim.recorded_at!, time };
  }
  return latest?.value ?? null;
}

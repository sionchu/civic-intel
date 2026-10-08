// User-facing labels only. Canonical codes, CSS classes and persisted values stay unchanged.
const STATUS_LABELS: Record<string, string> = {
  PUBLIC_RECORD_NOT_FOUND: "공개 기록 없음", INSUFFICIENT_ELIGIBLE_INPUTS: "비교 근거 부족", INVALID_INPUT: "입력 확인 필요",
  NOT_FOUND: "공개 기록 없음", INSUFFICIENT_INPUT: "비교 입력 부족", SOURCE_VERSION_CONFLICT: "출처 버전 충돌", ACCESS_DENIED: "접근 제한", SERVICE_UNAVAILABLE: "일시적 연결 오류",
  HUMAN_REVIEW_REQUIRED_NO_WRITE: "사람 검토 필요 · 변경 없음",
  ARTIFACT_UNAVAILABLE: "검토 자료 이용 불가", ARTIFACT_INVALID: "검토 자료 오류",
  CURRENT_SOURCE_UNAVAILABLE: "현재 출처 확인 불가", CURRENT_SOURCE_CONFLICT: "현재 출처 충돌",
  CURRENT_SOURCE_DRIFT: "현재 출처 변경 확인", CURRENT_ORGANIZATION_DRIFT: "현재 기관 기록 변경 확인",
  CURRENT_REVIEW_DRIFT: "현재 검토 조건 변경 확인", CURRENT_REVIEW_UNAVAILABLE: "현재 검토 자료 이용 불가",
  CURRENT_HUMAN_REVIEW_READY: "현재 자료로 사람 검토 가능", CURRENT_REVIEW_BLOCKED: "현재 자료로 검토 진행 불가",
  CANONICAL: "정본 등록 기록", SOURCE_RECORD_NOT_PERSON: "출처상 기록 · 인물 미연결",
  ENTITY_UNRESOLVED: "신원 미확정",
  FACT: "확인된 사실", CLAIM: "출처의 주장", INFERENCE: "근거에 따른 추론", HYPOTHESIS: "검토할 가설", UNKNOWN: "미확인",
  AVAILABLE: "기록 있음", PARTIAL: "일부 확인", RESOLVED: "신원 확인", REVIEW_REQUIRED: "검토 필요", HARD_CONFLICT: "근거 충돌",
  DERIVED: "기록 기반 분석", SUPPORT: "뒷받침", REFUTE: "반박", NEUTRAL: "참고", CONFLICT: "출처 충돌",
  PUBLISHED: "공개", DRAFT: "초안", REVIEW: "검토 중", WITHHELD: "비공개", UNRESOLVED: "미확정",
  SOURCE_NOT_COLLECTED: "출처 미수집", INSUFFICIENT_EVIDENCE: "근거 부족", DERIVATION_NOT_AVAILABLE: "분석 결과 미작성", NOT_APPLICABLE: "해당 없음",
  UNREVIEWED: "미검토", HELD: "보류", EXCLUDED: "제외", SOURCE_CONTEXT_REVIEW: "출처 맥락 검토", REVIEW_ONLY: "검토 전용", REGISTERED: "등록됨", HAS_CANDIDATE: "후보 있음",
  DISCLOSED_OWNED: "소유 주택 신고", DISCLOSED_NONE: "신고 기준일에 본인 소유 주택 없음", COMPLETE_SELF_HOUSING: "본인 주택 항목 전체 확인", REVIEWED_SELECTED_RECORD: "검토된 해당 기록", WITHDRAWN: "철회", ACTIVE: "활성", SUSPENDED: "중단", VERIFIED: "검증됨", CANCELLED: "취소", NOT_OVERLAPPING: "기간 겹침 없음", BLOCKED: "접근 차단", RUNNING: "실행 중", SUCCESS: "완료", FAILED: "실패", OPEN: "미처리", REJECTED: "제외", CURRENT: "현재", SUPERSEDED: "대체됨",
};
export function statusLabel(code: string | null | undefined): string { return (code ? STATUS_LABELS[code] ?? (/[가-힣]/.test(code) ? code : "상태 미확인") : "미확인"); }
const SOURCE_CLASSES: Record<string, string> = {
  official_open_api_html: "공식 공개 웹 자료", official_statutory_disclosure_api: "공식 법정 공시", official_reviewed_committee_attachment: "검토된 위원회 공식 첨부 자료", official_standard_dataset: "공식 표준 자료", official_personnel_notice: "공식 인사 공고", official_government_organization_html: "공식 정부 조직 자료", official_presidential_personnel_release: "공식 대통령실 인사 발표", official_open_api: "공식 공개 자료", official_national_assembly_minutes: "국회 공식 회의록", official_committee_attachment: "위원회 공식 첨부 자료",
  official_statutory_disclosure: "공식 법정 공시", official_structured_disclosure: "공식 구조화 공시", owner_supplied_reviewed_copy: "검토된 제공 자료",
  official_public_declared_asset_metadata: "공개 재산신고 자료", official_government_gazette: "공식 관보",
};
export function sourceClassLabel(code: string | null | undefined): string { return (code ? SOURCE_CLASSES[code] ?? "출처 자료" : "출처 자료"); }

export function entryKindLabel(code: string): string { return ({ IDENTITY: "인물 정보", LIMITATION: "자료 범위", CHANGE: "기록 변화", DECISION_EPISODE: "의사결정 기록", CLAIM: "공개 기록", DERIVED: "기록 기반 분석", RELATIONSHIP: "공식 연결", DECISION: "의사결정 기록", STATEMENT: "발언 기록" } as Record<string, string>)[code] ?? "공개 기록"; }

export function relationLabel(code: string): string { return ({ HELD_ROLE: "직책", DISCLOSED_ROLE_AT: "검토된 공시상 직책", WORKED_AT: "경력", STUDIED_AT: "학력", SERVED_ON: "위원회", DIRECTOR_OF: "이사회", APPOINTED_TO: "임명", APPEARED_AT: "출석", QUESTIONED: "질의", AUDITED_BY: "감사", LISTS_EXECUTIVE: "공식 공시상 임원" } as Record<string, string>)[code] ?? "관계 유형 미확인"; }

export function nodeKindLabel(code: string): string { return ({ PERSON: "인물", ORGANIZATION: "기관", EDUCATIONAL_INSTITUTION: "교육기관", COMPANY: "기업", COMMITTEE: "위원회", HEARING: "청문회", ISSUE: "쟁점", OFFICE: "직위", SOURCE_LISTED_ROLE_HOLDER: "출처 기재 직책 보유자" } as Record<string, string>)[code] ?? "대상 유형 미확인"; }

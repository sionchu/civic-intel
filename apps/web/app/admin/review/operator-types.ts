import { statusLabel, sourceClassLabel, relationLabel, nodeKindLabel } from "../../display-labels";
import { predicateLabel } from "../../predicate-labels";

export type FieldValue = string | number | boolean | string[] | null;
export type OperatorRecord = {
  id: string; kind: string; label: string; status: string; version?: string;
  fields: Record<string, FieldValue>;
};
export type OperatorGraph = {
  center: string;
  nodes: (OperatorRecord & { record_id: string; inspect_kind?: string; inspect_id?: string })[];
  edges: { id: string; source: string; target: string; label: string; review_only: boolean }[];
  truncated: boolean; max_nodes: number; max_depth: number; semantics: string;
};
export type OperatorDetail = { record: OperatorRecord; graph: OperatorGraph };
export type RecordPage = { kind: string; total: number; offset: number; limit: number; items: OperatorRecord[] };
export type Lane = {
  feeder: string; scope_key: string; observation_versions: number; provider_keys: number;
  latest_run_id: string | null; latest_run_status: string | null;
  latest_run_started_at: string | null; latest_run_finished_at: string | null;
  records_seen: number | null; observations_created: number | null; observations_unchanged: number | null;
  last_success_at: string | null; checkpoint_updated_at: string | null;
};
export type Overview = {
  counts: Record<string, number>; lanes: Lane[]; lanes_truncated: boolean;
  checked_at: string; environment_label: string; schema_expected: string;
  documented_catalog: { name: string; scope: string; source: string; mode: string; maturity: string }[];
};
export type GukgamClaimReviewItem = {
  review_key: string;
  organization_id: string;
  organization_name: string;
  committee_name: string;
  audit_date: string;
  audited_target: string;
  observation_id: string;
  match_class: string;
  current_claim_present: boolean;
};

export type GukgamReviewDecision = "APPROVE" | "REJECT" | "HOLD";
export type GukgamReviewHoldReason =
  | "INSTITUTION_IDENTITY_UNCLEAR"
  | "LIFECYCLE_OR_SUCCESSOR_UNCLEAR"
  | "SOURCE_CONTEXT_INSUFFICIENT"
  | "OTHER_EVIDENCE_REQUIRED";

export type GukgamReviewEvidenceOpens = {
  organization: number;
  gukgam_observation: number;
};

export type GukgamReviewMetricItem = {
  review_key: string;
  decision: GukgamReviewDecision;
  hold_reason: GukgamReviewHoldReason | null;
  decided_at: string;
  active_ms: number;
  evidence_opens: GukgamReviewEvidenceOpens;
  org_occurrence_index: number;
  org_occurrence_count: number;
  batch_decided: boolean;
  receipt_sha256: string;
};

export type ReviewMetricGroup = {
  count: number;
  decision_counts: Record<string, number>;
  hold_reason_counts: Record<string, number>;
  median_active_ms: number | null;
  p90_active_ms: number | null;
  with_evidence_opens: number;
  evidence_open_rate: number | null;
  batch_decided_count: number;
};

export type GukgamReviewThroughput = {
  semantics: "GUKGAM_EXISTING_ORGANIZATION_REVIEW_THROUGHPUT_V1";
  manifest_sha256: string;
  review_item_count: number;
  organization_count: number;
  decided_count: number;
  remaining_count: number;
  all_reviewed: boolean;
  overall: ReviewMetricGroup;
  first_occurrence: ReviewMetricGroup;
  repeat_occurrence: ReviewMetricGroup;
  items: GukgamReviewMetricItem[];
  canonical_write_performed: false;
  claim_commit_authorized: false;
};

export type MoisOrganizationReviewItem = {
  organization_name: string;
  org_code: string;
  lowest_name: string | null;
  type_big: string | null;
  type_mid: string | null;
  parent_org_code: string | null;
  top_org_code: string | null;
  representative_org_code: string | null;
  base_date: string | null;
  changed_date: string | null;
  observation_id: string;
  occurrence_count: number;
  occurrences: {
    review_key: string;
    committee_name: string;
    audit_date: string;
    audited_target: string;
    observation_id: string;
  }[];
  materialization_authorized: boolean;
};

export type Manifest = {
  status: string;
  message: string;
  checked_at?: string;
  write_performed: false;
  gukgam_claim_review: {
    status: string;
    message?: string;
    manifest_sha256?: string | null;
    item_count?: number;
    organization_count?: number;
    current_organization_count?: number;
    existing_gukgam_claim_count?: number;
    claim_commit_authorized: boolean;
    items: GukgamClaimReviewItem[];
  };
  mois_organization_review: {
    status: string;
    message?: string;
    artifact_sha256?: string;
    proposal_count?: number;
    occurrence_count?: number;
    unmatched_distinct_target_count?: number;
    ambiguous_distinct_target_count?: number;
    materialization_authorized: boolean;
    items: MoisOrganizationReviewItem[];
  };
};

export const KIND_LABELS: Record<string, string> = {
  organizations: "기관", people: "인물", claims: "공개 내용 기록", observations: "수집 기록",
  sources: "출처", runs: "수집 실행", evidence: "근거 기록", snapshots: "수집본",
  reviews: "신원 검토", policies: "출처 정책", links: "인물 연결", checkpoints: "수집 진행 지점",
};
export const FIELD_LABELS: Record<string, string> = {
  relation_periods: "관계별 기록 기간", source_conflict: "관련 근거에 출처 상충",
  canonical_id: "정본 식별자", claim_ids: "근거 기록 식별자", evidence_ids: "근거 식별자", source_ids: "출처 식별자",
  name: "기관명", canonical_name: "이름", subject: "대상", predicate: "내용 유형",
  object_text: "기록 내용", proposition: "명제", epistemic_status: "내용 판단 상태",
  publication_status: "공개 상태", identity_status: "신원 상태", asserted_as_true: "사실 주장 여부",
  valid_from: "유효 시작", valid_to: "유효 종료", recorded_at: "저장 시각",
  superseded_at: "대체 시각", feeder: "수집 경로", scope_key: "수집 범위",
  provider_record_key: "공급자 기록 키", snapshot_id: "수집본 식별자", run_id: "실행 식별자",
  source_id: "출처 식별자", claim_id: "기록 식별자", feeder_observation_id: "수집 기록 식별자",
  provider_observed_at: "공급자 기준 시각", content_hash: "내용 해시", semantic_scope: "기록 의미",
  title: "제목", publisher: "발행처", url: "출처 주소", published_at: "발행 시각",
  policy_id: "정책 식별자", started_at: "실행 시작", finished_at: "실행 종료", records_seen: "확인한 행",
  observations_created: "새 기록 버전", observations_unchanged: "변화 없는 기록", stance: "근거 입장",
  fetched_at: "수집 시각", reason_code: "검토 사유", status: "처리 상태",
  candidate_person_id: "후보 인물 식별자 · 동일인 미확정", person_id: "인물 식별자", organization_id: "기관 식별자",
  institution_name: "기관명", position_text: "공시 직책", committee_name: "위원회", audit_date: "감사 예정일",
  audited_targets: "출처 기재 감사대상", domain: "도메인", collection_mode: "수집 방식",
  can_fetch: "접근 허용", can_store_metadata: "메타데이터 저장", can_store_fulltext: "전문 저장",
  can_send_to_ai: "AI 전송", can_show_excerpt: "발췌 표시", can_commercialize: "상업 이용",
};
export function fieldText(value: FieldValue): string {
  if (value === null) return "기록 없음";
  if (typeof value === "boolean") return value ? "예" : "아니요";
  return Array.isArray(value) ? value.join(" · ") : String(value);
}


// Display adapter only: eligibility and identity remain the existing ontology API's responsibility.
export function publicOntologyDetail(graph: import("../../types").OntologyGraph, record: OperatorRecord): OperatorDetail {
  const edges = graph.edges.slice(0, 60);
  const included = new Set([graph.center_node_id, ...edges.flatMap((edge) => [edge.source, edge.target])]);
  const nodes = graph.nodes.filter((node) => included.has(node.id)).map((node) => {
    const related = edges.filter((edge) => edge.source === node.id || edge.target === node.id);
    const kind = node.kind === "PERSON" ? "people" : node.kind === "ORGANIZATION" ? "organizations" : node.kind;
    return { id: node.id, record_id: node.canonical_id ?? "", kind, label: node.label,
      status: node.canonical_id ? "CANONICAL" : "SOURCE_RECORD_NOT_PERSON",
      inspect_kind: node.canonical_id ? kind : "claims", inspect_id: node.canonical_id ?? related[0]?.claim_id,
      fields: { node_kind: node.kind, canonical_id: node.canonical_id,
        claim_ids: [...new Set(related.map((edge) => edge.claim_id))],
        evidence_ids: [...new Set(related.flatMap((edge) => edge.evidence_ids))],
        source_ids: [...new Set(related.flatMap((edge) => edge.source_ids))],
        relation_types: [...new Set(related.map((edge) => edge.relation_type))],
        epistemic_status: [...new Set(related.map((edge) => edge.epistemic_status))],
        source_conflict: related.some((edge) => edge.source_conflict),
        relation_periods: related.map((edge) => `${relationLabel(edge.relation_type)}: ${edge.valid_from ?? "시작 기록 없음"} → ${edge.valid_to ?? "종료 기록 없음"}`),
      } as Record<string, FieldValue>,
    };
  });
  return { record, graph: { center: graph.center_node_id, nodes,
    edges: edges.map((edge) => ({ id: edge.id, source: edge.source, target: edge.target,
      label: relationLabel(edge.relation_type), review_only: false })),
    truncated: graph.edges.length > edges.length, max_nodes: 80, max_depth: 1,
    semantics: "PUBLIC_CANONICAL_CLAIM_EVIDENCE_RELATIONS",
  } };
}

export function fieldDisplayText(name: string, value: FieldValue): string {
  if (Array.isArray(value)) return value.map((item) => fieldDisplayText(name, item)).join(" · ");
  if (typeof value === "string") {
    if (["epistemic_status", "publication_status", "identity_status", "stance", "status"].includes(name)) return statusLabel(value);
    if (name === "relation_types") return relationLabel(value);
    if (name === "node_kind") return nodeKindLabel(value);
    if (name === "predicate") return predicateLabel(value);
    if (name === "source_class") return sourceClassLabel(value);
    if (name === "collection_mode") return ({ API: "공개 자료 연동", RSS: "구독 자료 연동", HTTP: "공개 웹 자료 연동", BLOCKED: "수집 차단", BROWSER: "화면 검토", DISCOVERY_ONLY: "출처 탐색" } as Record<string, string>)[value] ?? "방식 미확인";
  }
  return fieldText(value);
}

export function catalogDisplay(item: Overview["documented_catalog"][number]) {
  const stage = /L3 FULL_ENUMERATION/.test(item.maturity) ? "문서상 지정 범위 전체 수집" : /L2 SINGLE_PULL/.test(item.maturity) ? "문서상 단일 범위 수집" : /L1 CONTRACT_STAGED/.test(item.maturity) ? "수집 계약 준비" : /L0 RESEARCHED/.test(item.maturity) ? "출처 조사 단계" : "문서상 준비 단계 별도 확인";
  const modes: Record<string, string> = { API: "공개 자료 연동", OFFICIAL_WEB: "공식 웹 자료", STRUCTURED_DISCLOSURE: "구조화 공시", XLSX: "표 자료", BROWSER: "화면 검토", DISCOVERY_ONLY: "출처 탐색", BLOCKED: "접근 차단" };
  return { scope: "문서에 지정된 공개 대상 범위", mode: Object.entries(modes).filter(([code]) => item.mode.includes(code)).map(([, label]) => label).join(" · ") || "문서상 수집 방식 별도 확인", maturity: stage + (/BLOCKED|blocked/.test(item.maturity) ? " · 제약 있음" : "") };
}

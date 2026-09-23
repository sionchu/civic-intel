export type FieldValue = string | number | boolean | string[] | null;
export type OperatorRecord = {
  id: string; kind: string; label: string; status: string;
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
export type Manifest = {
  status: string; message: string; manifest_sha256?: string; proposal_core_sha256?: string;
  item_count?: number; organizations_to_create?: number | null; organizations_to_reuse?: number | null;
  checked_at?: string;
  items?: { organization_name: string; org_code: string; chart_id: string; category: string;
    source_locator: string | null; organization_id: string; action: string; review_occurrences: number }[];
};
export const KIND_LABELS: Record<string, string> = {
  organizations: "기관", people: "인물", claims: "Claim · 내용", observations: "수집 기록",
  sources: "출처", runs: "수집 실행", evidence: "Evidence · 근거", snapshots: "수집본",
  reviews: "신원 검토", policies: "출처 정책", links: "인물 연결", checkpoints: "체크포인트",
};
export const FIELD_LABELS: Record<string, string> = {
  relation_periods: "관계별 기록 기간", source_conflict: "관련 근거에 출처 상충",
  canonical_id: "canonical ID", claim_ids: "근거 Claim ID", evidence_ids: "Evidence ID", source_ids: "출처 ID",
  name: "기관명", canonical_name: "이름", subject: "대상", predicate: "내용 유형",
  object_text: "기록 내용", proposition: "명제", epistemic_status: "내용 판단 상태",
  publication_status: "공개 상태", identity_status: "신원 상태", asserted_as_true: "사실 주장 여부",
  valid_from: "유효 시작", valid_to: "유효 종료", recorded_at: "DB 기록 시각",
  superseded_at: "대체 시각", feeder: "수집 경로", scope_key: "수집 범위",
  provider_record_key: "공급자 기록 키", snapshot_id: "수집본 ID", run_id: "실행 ID",
  source_id: "출처 ID", claim_id: "Claim ID", feeder_observation_id: "수집 기록 ID",
  provider_observed_at: "공급자 기준 시각", content_hash: "내용 해시", semantic_scope: "기록 의미",
  title: "제목", publisher: "발행처", url: "출처 주소", published_at: "발행 시각",
  policy_id: "정책 ID", started_at: "실행 시작", finished_at: "실행 종료", records_seen: "확인한 행",
  observations_created: "새 기록 버전", observations_unchanged: "변화 없는 기록", stance: "근거 입장",
  fetched_at: "수집 시각", reason_code: "검토 사유", status: "처리 상태",
  candidate_person_id: "후보 인물 ID · 동일인 미확정", person_id: "인물 ID", organization_id: "기관 ID",
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
        relation_periods: related.map((edge) => `${edge.relation_type}: ${edge.valid_from ?? "시작 기록 없음"} → ${edge.valid_to ?? "종료 기록 없음"}`),
      } as Record<string, FieldValue>,
    };
  });
  return { record, graph: { center: graph.center_node_id, nodes,
    edges: edges.map((edge) => ({ id: edge.id, source: edge.source, target: edge.target,
      label: edge.relation_type, review_only: false })),
    truncated: graph.edges.length > edges.length, max_nodes: 80, max_depth: 1,
    semantics: "PUBLIC_CANONICAL_CLAIM_EVIDENCE_RELATIONS",
  } };
}

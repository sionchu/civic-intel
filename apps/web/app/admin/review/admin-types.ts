import type { OperatorRecord } from "./operator-types";

export type AdminCapabilities = { schema_ready: boolean; writes_enabled: boolean; actor: string; write_mode_requested: boolean; schema_required: string; operations: string[] };
export type QueueItem = OperatorRecord & { disposition: string; linked_person_id: string | null; candidate_count: number; candidates: { id: string; canonical_name: string; identity_status: string }[] };
export type ReviewQueue = { total: number; limit: number; offset: number; items: QueueItem[]; counts: Record<string, number>; named_record_total: number; distinct_names: number; semantics: string };
export type AdminChange = { table: string; id: string; operation: string; before: Record<string, unknown> | null; after: Record<string, unknown> };
export type AdminPreview = { preview_token: string; state_hash: string; actor: string; selected_count: number; changes: AdminChange[]; outcomes: Record<string, unknown>[]; writes_enabled: boolean };
export type AdminReceipt = { id: string; version: string; actor: string; action: string; created_at: string; reason: string; changes: AdminChange[]; result: { outcomes: Record<string, unknown>[]; changed_rows: number }; write_performed: boolean; replayed: boolean };
export type AdminHistory = { available: boolean; total: number; items: AdminReceipt[]; offset?: number; limit?: number };
export type AdminCommand = { request_id: string; action: string; record_ids: string[]; reason: string; target_person_id?: string; evidence_ids?: string[]; value?: string; identity_basis?: string; human_verified?: boolean };
export const ACTION_LABELS: Record<string, string> = {
  HOLD: "보류", EXCLUDE: "대상 제외", REOPEN: "검토 재개", REGISTER_PERSON: "신규 인물 등록",
  LINK_PERSON: "기존 인물에 연결", SUBMIT_REVIEW: "검토 요청", PUBLISH: "승인·공개", WITHDRAW: "공개 취소",
  CORRECT_CLAIM: "정정안 작성", RENAME_PERSON: "이름 정정", DEACTIVATE_PERSON: "인물 비활성화",
  MERGE_PERSON: "중복 인물 병합",
};
export const DISPOSITION_LABELS: Record<string, string> = {
  ALL: "전체", UNREVIEWED: "미검토", HAS_CANDIDATE: "동일 이름 후보 있음", HELD: "보류",
  EXCLUDED: "대상 제외", REGISTERED: "인물 연결 완료", CONFLICT: "연결 충돌",
};
export async function adminRequest<T>(operation: string, payload: unknown): Promise<T> {
  const response = await fetch("/admin/review/actions", { method: "POST",
    headers: { "Content-Type": "application/json", "X-Civic-Admin-Intent": "explicit" },
    body: JSON.stringify({ operation, payload }),
  });
  const result = await response.json();
  if (!response.ok) throw new Error(result.error?.message ?? "작업을 완료하지 못했습니다. 상태를 다시 확인하세요.");
  return result as T;
}

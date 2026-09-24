"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ACTION_LABELS, adminRequest, type AdminCapabilities, type AdminCommand, type AdminPreview, type AdminReceipt } from "./admin-types";
import type { OperatorRecord } from "./operator-types";

const OPERATIONS: Record<string, string[]> = {
  observations: ["HOLD", "REGISTER_PERSON", "LINK_PERSON", "EXCLUDE", "REOPEN"],
  claims: ["SUBMIT_REVIEW", "PUBLISH", "WITHDRAW", "CORRECT_CLAIM"],
  people: ["RESOLVE_PERSON", "RENAME_PERSON", "MERGE_PERSON", "DEACTIVATE_PERSON"],
};
const IDENTITY = new Set(["REGISTER_PERSON", "RESOLVE_PERSON", "LINK_PERSON", "MERGE_PERSON"]);
const BRIDGE = new Set(["LINK_PERSON", "MERGE_PERSON"]);
const EDIT = new Set(["CORRECT_CLAIM", "RENAME_PERSON"]);
const DESTRUCTIVE = new Set(["EXCLUDE", "WITHDRAW", "DEACTIVATE_PERSON", "MERGE_PERSON"]);

export default function AdminActions({ kind, ids, capabilities, labels = [], status }: {
  kind: string; ids: string[]; capabilities: AdminCapabilities; labels?: string[]; status?: string;
}) {
  const router = useRouter();
  const actions = (OPERATIONS[kind] ?? []).filter((item) => item !== "RESOLVE_PERSON" || status === "REVIEW");
  const [action, setAction] = useState(actions[0] ?? "");
  const [reason, setReason] = useState("");
  const [value, setValue] = useState("");
  const [target, setTarget] = useState("");
  const [targetQuery, setTargetQuery] = useState("");
  const [targets, setTargets] = useState<OperatorRecord[]>([]);
  const [evidence, setEvidence] = useState("");
  const [evidenceQuery, setEvidenceQuery] = useState("");
  const [evidenceOptions, setEvidenceOptions] = useState<{ id: string; label: string; proposition: string; source_title: string; url: string | null; stance: string }[]>([]);
  const [basis, setBasis] = useState("OFFICIAL_BIOGRAPHY_CONTINUITY");
  const [verified, setVerified] = useState(false);
  const [confirmed, setConfirmed] = useState(false);
  const [preview, setPreview] = useState<{ data: AdminPreview; command: AdminCommand } | null>(null);
  const [receipt, setReceipt] = useState<AdminReceipt | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  function invalidate() { setPreview(null); setConfirmed(false); setError(""); setReceipt(null); }
  async function lookup() {
    setBusy(true); setError("");
    try { const result = await adminRequest<{ items: OperatorRecord[] }>("lookup", { kind: "people", q: targetQuery }); setTargets(result.items); }
    catch (error) { setError(error instanceof Error ? error.message : "대상 검색 실패"); }
    finally { setBusy(false); }
  }
  async function findEvidence() {
    setBusy(true); setError("");
    try { const result = await adminRequest<{ items: typeof evidenceOptions }>("lookup", { kind: "evidence", q: evidenceQuery }); setEvidenceOptions(result.items); }
    catch (error) { setError(error instanceof Error ? error.message : "근거 검색 실패"); }
    finally { setBusy(false); }
  }
  async function prepare() {
    setBusy(true); setError(""); setReceipt(null); setConfirmed(false);
    const command: AdminCommand = { request_id: crypto.randomUUID(), action, record_ids: ids, reason };
    if (IDENTITY.has(action)) command.human_verified = verified;
    if (BRIDGE.has(action)) { command.target_person_id = target; command.identity_basis = basis; }
    if (BRIDGE.has(action) || EDIT.has(action)) command.evidence_ids = evidence.split(/[\s,]+/).filter(Boolean);
    if (EDIT.has(action)) command.value = value;
    try { const data = await adminRequest<AdminPreview>("preview", command); setPreview({ data, command }); }
    catch (error) { setPreview(null); setError(error instanceof Error ? error.message : "미리보기 실패"); }
    finally { setBusy(false); }
  }
  async function commit() {
    if (!preview || !confirmed) return;
    setBusy(true); setError("");
    try {
      const result = await adminRequest<AdminReceipt>("commit", { command: preview.command, preview_token: preview.data.preview_token, confirmed: true });
      setReceipt(result); setPreview(null); router.refresh();
    } catch (error) { setError(error instanceof Error ? error.message : "처리 실패"); }
    finally { setBusy(false); }
  }
  if (!actions.length) return null;
  const selectedKey = ids.join(",");
  const previewMatches = preview?.command.record_ids.join(",") === selectedKey;
  const followup = receipt?.result.outcomes.flatMap((item) => typeof item.claim_id === "string" ? [item.claim_id]
    : typeof item.correction_claim_id === "string" ? [item.correction_claim_id] : []) ?? [];
  return <section className="admin-command" aria-label="운영자 작업">
    <div className="operator-section-head"><h3>선택 항목 처리</h3><span>{ids.length}건 · {capabilities.actor}</span></div>
    {!capabilities.writes_enabled && <p className="admin-notice">현재 연결은 조회·미리보기 모드입니다.
      {!capabilities.schema_ready ? " 변경 이력 DB 준비(0007)가 필요합니다." : " 운영자 쓰기 모드가 꺼져 있습니다."}
      실제 반영은 준비된 어드민 세션에서만 실행됩니다.</p>}
    <p className="operator-note">{labels.slice(0, 4).join(" · ")}{labels.length > 4 ? ` 외 ${labels.length - 4}건` : ""}</p>
    <label>작업<select value={action} onChange={(event) => { setAction(event.target.value); invalidate(); }}>
      {actions.map((item) => <option value={item} key={item}>{ACTION_LABELS[item]}</option>)}</select></label>
    {action === "REGISTER_PERSON" && <p className="operator-note">원문의 이름·기관·직책을 직접 확인한 기록만 선택하세요. 동일 이름 후보가 있으면 일괄 신규 등록을 중단합니다. 등록된 역할 Claim은 초안이며 자동 공개하지 않습니다.</p>}
    {action === "RESOLVE_PERSON" && <p className="operator-note">자동 생성된 ALIO source-context Person만 확인합니다. 현재 공식 ALIO 행·기관 binding·역할 초안·Evidence를 다시 검증하며, 다른 출처와 동일인이라는 의미는 아닙니다. 신원 확인 뒤 역할 Claim은 여전히 별도 승인 대상입니다.</p>}
    {BRIDGE.has(action) && <fieldset><legend>{action === "MERGE_PERSON" ? "유지할 인물" : "연결 대상 인물"}</legend>
      <div className="admin-search"><input aria-label="연결 대상 이름 검색" value={targetQuery} onChange={(event) => setTargetQuery(event.target.value)} placeholder="인물 이름 또는 ID" />
        <button type="button" disabled={busy} onClick={lookup}>대상 검색</button></div>
      {targets.map((person) => <label className="admin-check" key={person.id}><input type="radio" name="target-person" value={person.id} checked={target === person.id}
        onChange={() => { setTarget(person.id); invalidate(); }} />{person.label} · {person.status}<small>{person.id}</small></label>)}
      <label>선택 대상 ID<input value={target} onChange={(event) => { setTarget(event.target.value); invalidate(); }} placeholder="위 검색에서 선택" /></label>
      <label>공식 연결 근거의 종류<select value={basis} onChange={(event) => { setBasis(event.target.value); invalidate(); }}>
        <option value="OFFICIAL_BIOGRAPHY_CONTINUITY">공식 약력에서 동일인 경력 연결 확인</option>
        <option value="OFFICIAL_CAREER_CONTINUITY">공식 인사·경력 자료에서 전후 역할 연결 확인</option></select></label>
      <p className="operator-note">동명이인·소속 유사성·모델 점수는 동일인 근거가 아닙니다. 실제 공식 자료에서 두 역할이 같은 사람임을 확인해야 합니다.</p>
    </fieldset>}
    {action === "CORRECT_CLAIM" && <p className="operator-note">정정안은 별도의 서술형 CLAIM 초안입니다. 원문·자동 추출값을 덮어쓰거나 FACT로 올리지 않습니다. 승인하면 원본 Claim을 대체하며, 원본의 특수 관계도는 자동 재해석하지 않습니다.</p>}
    {EDIT.has(action) && <label>{action === "RENAME_PERSON" ? "정정할 이름" : "정정 내용 · 새 초안으로 작성"}
      <textarea value={value} maxLength={action === "RENAME_PERSON" ? 100 : 1500} rows={3} onChange={(event) => { setValue(event.target.value); invalidate(); }} /></label>}
    {(BRIDGE.has(action) || EDIT.has(action)) && <fieldset><legend>검토 근거 선택</legend>
      <div className="admin-search"><input aria-label="근거 내용 검색" value={evidenceQuery} onChange={(event) => setEvidenceQuery(event.target.value)} placeholder="인물·기관·기록 내용으로 근거 검색" />
        <button type="button" onClick={findEvidence} disabled={busy}>근거 검색</button></div>
      {evidenceOptions.map((item) => <article className="admin-evidence-option" key={item.id}><label className="admin-check">
        <input type="checkbox" checked={evidence.split(/[\s,]+/).includes(item.id)} onChange={(event) => {
          const values = new Set(evidence.split(/[\s,]+/).filter(Boolean)); if (event.target.checked) values.add(item.id); else values.delete(item.id); setEvidence([...values].join(", ")); invalidate();
        }} /><span><strong>{item.label} · {item.stance}</strong><small>{item.proposition}</small></span></label>
        {item.url && <a href={item.url} target="_blank" rel="noreferrer">{item.source_title} 원문 ↗</a>}</article>)}
    </fieldset>}
    {(BRIDGE.has(action) || EDIT.has(action)) && <label>검토한 Evidence ID · 쉼표 또는 줄바꿈으로 구분
      <textarea value={evidence} rows={2} onChange={(event) => { setEvidence(event.target.value); invalidate(); }} placeholder="근거 패널의 Evidence 레코드 ID" />
      <small>원문·출처는 DB 목록의 Evidence/Source에서 확인합니다. 존재하지 않는 ID나 정책 위반 근거는 거절됩니다.</small></label>}
    <label>처리 사유·검토 근거<textarea value={reason} minLength={10} maxLength={1500} rows={3}
      onChange={(event) => { setReason(event.target.value); invalidate(); }} placeholder="무엇을 확인했고 왜 변경하는지 기록하세요." /></label>
    {IDENTITY.has(action) && <label className="admin-check"><input type="checkbox" checked={verified}
      onChange={(event) => { setVerified(event.target.checked); invalidate(); }} />원문과 신원 문맥을 직접 검토했습니다. 이름만으로 동일인이라고 판단하지 않았습니다.</label>}
    <button className="admin-primary" type="button" disabled={busy || !ids.length || reason.trim().length < 10}
      onClick={prepare}>{busy ? "검증 중…" : "변경 미리보기"}</button>
    {error && <p className="admin-error" role="alert">{error}</p>}
    {preview && previewMatches && <div className="admin-preview"><h4>반영 전 확인 · {ACTION_LABELS[action]}</h4>
      <p>{preview.data.selected_count}건 선택 · {preview.data.changes.length}개 DB 행 변경 예정 · 5분 후 미리보기 만료</p>
      {DESTRUCTIVE.has(action) && <p className="admin-error">공개 상태 또는 인물 연결이 달라지는 작업입니다. 아래 영향 범위를 확인하세요. 원본 수집 기록은 삭제하지 않습니다.</p>}
      <div className="admin-change-list">{preview.data.changes.map((change) => <details key={`${change.table}:${change.id}`}><summary>{change.operation} · {change.table} · {change.id.slice(0, 8)}</summary>
        <div className="admin-diff"><div><strong>변경 전</strong><pre>{JSON.stringify(change.before, null, 2)}</pre></div><div><strong>변경 후</strong><pre>{JSON.stringify(change.after, null, 2)}</pre></div></div></details>)}</div>
      <label className="admin-check"><input type="checkbox" checked={confirmed} onChange={(event) => setConfirmed(event.target.checked)} />정확히 이 항목과 변경 내용을 확인했습니다.</label>
      <div className="admin-button-row"><button type="button" disabled={busy} onClick={() => { setPreview(null); setConfirmed(false); }}>취소 · 변경 안 함</button>
        <button className="admin-primary" type="button" disabled={busy || !confirmed || !capabilities.writes_enabled || !preview.data.writes_enabled}
          onClick={commit}>{busy ? "반영 확인 중…" : `${ACTION_LABELS[action]} 확정`}</button></div>
      <small>요청 ID {preview.command.request_id}. 결과를 받지 못하면 새 작업을 만들기 전에 변경 이력을 확인하세요.</small>
    </div>}
    {receipt && <div className="admin-receipt" role="status"><strong>{receipt.replayed ? "이미 반영된 요청입니다." : "DB 반영을 확인했습니다."}</strong>
      <p>{ACTION_LABELS[receipt.action]} · {receipt.result.changed_rows}행 · {receipt.actor}</p>
      <p>작업 ID {receipt.id}</p><Link href="/admin/review?tab=history" prefetch={false}>변경 이력 보기 →</Link>
      {followup.length > 0 && <details><summary>생성된 초안 {followup.length}건을 계속 검토</summary>
        <AdminActions kind="claims" ids={followup} capabilities={capabilities} /></details>}</div>}
  </section>;
}

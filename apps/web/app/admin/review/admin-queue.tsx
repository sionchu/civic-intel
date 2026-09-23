"use client";

import { useState } from "react";
import Link from "next/link";
import { DISPOSITION_LABELS, adminRequest, type AdminCapabilities, type ReviewQueue } from "./admin-types";
import type { OperatorDetail } from "./operator-types";
import AdminActions from "./admin-actions";
import OperatorGraphView from "./operator-graph";

export default function AdminQueue({ queue, capabilities, q, state }: {
  queue: ReviewQueue; capabilities: AdminCapabilities; q: string; state: string;
}) {
  const [selected, setSelected] = useState<string[]>([]);
  const [detail, setDetail] = useState<OperatorDetail | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const activeIds = selected.filter((id) => queue.items.some((item) => item.id === id));
  const selectedItems = queue.items.filter((item) => activeIds.includes(item.id));
  function toggle(id: string) { setSelected((value) => value.includes(id) ? value.filter((item) => item !== id) : [...value, id]); }
  function href(nextState: string, offset = 0) { return `/admin/review?${new URLSearchParams({ tab: "people-review", state: nextState, q, offset: String(offset) })}`; }
  async function inspect(id: string) {
    setError(""); setBusy(true);
    try { setDetail(await adminRequest<OperatorDetail>("lookup", { kind: "observations", id })); }
    catch (error) { setError(error instanceof Error ? error.message : "근거 확인 실패"); }
    finally { setBusy(false); }
  }
  return <section className="admin-queue">
    <div className="operator-section-head"><div><span className="micro-label">PERSON RECORD REVIEW</span><h2>인물 수집 기록 검토</h2></div>
      <span>ALIO 공개 이름 기록 {queue.named_record_total.toLocaleString()}건</span></div>
    <p className="operator-note">이름이 있는 출처 기록을 빠짐없이 업무로 표시합니다. 고유 이름 문자열 {queue.distinct_names.toLocaleString()}개는 서로 다른 사람 수가 아닙니다. 각 행의 기관·직책·원문과 기존 인물 후보를 검토하세요.</p>
    <nav className="admin-dispositions" aria-label="인물 검토 상태">{Object.entries(DISPOSITION_LABELS).map(([key, label]) =>
      <Link key={key} href={href(key)} prefetch={false} aria-current={state === key ? "page" : undefined}>{label}
        {key === "ALL" ? <strong>{queue.named_record_total.toLocaleString()}</strong> : key !== "HAS_CANDIDATE" && <strong>{(queue.counts[key] ?? 0).toLocaleString()}</strong>}</Link>)}</nav>
    <form method="get" action="/admin/review" className="operator-filters"><input type="hidden" name="tab" value="people-review" /><input type="hidden" name="state" value={state} />
      <label>이름·기관·직책 검색<input name="q" type="search" defaultValue={q} maxLength={200} /></label><button type="submit">검색</button></form>
    <div className="admin-workspace"><div>
      <div className="admin-selection"><label className="admin-check"><input type="checkbox" checked={queue.items.length > 0 && activeIds.length === queue.items.length}
        onChange={(event) => setSelected(event.target.checked ? queue.items.map((item) => item.id) : [])} />현재 페이지 {queue.items.length}건 선택</label>
        <span>선택 {activeIds.length}건 · 조건 전체 {queue.total.toLocaleString()}건</span></div>
      <div className="admin-review-list">{queue.items.map((item) => <article className="admin-review-row" key={item.id} data-selected={activeIds.includes(item.id)}>
        <label className="admin-check"><input type="checkbox" checked={activeIds.includes(item.id)} onChange={() => toggle(item.id)} aria-label={`${item.label} 검토 선택`} />
          <strong>{item.fields.canonical_name ?? item.label}</strong><span className="operator-tag">{DISPOSITION_LABELS[item.disposition] ?? item.disposition}</span></label>
        <p>{String(item.fields.institution_name ?? "기관 미기록")} · {String(item.fields.position_text ?? "직책 미기록")}</p>
        <small>{String(item.fields.term_start ?? "기간 미기록")} → {String(item.fields.term_end ?? "종료 미기록")}</small>
        {item.candidate_count > 0 && item.disposition !== "REGISTERED" && <aside className="admin-candidates"><strong>동일 이름 후보 {item.candidate_count}명 · 동일인 미확정</strong>
          {item.candidates.map((person) => <Link key={person.id} target="_blank" prefetch={false} href={`/admin/review?tab=records&kind=people&focus_kind=people&focus_id=${person.id}`}>{person.canonical_name} · {person.id.slice(0, 8)} ↗</Link>)}</aside>}
        <div className="admin-row-actions"><button type="button" disabled={busy} onClick={() => inspect(item.id)}>원문 경로·연결 확인</button>
          {item.linked_person_id && <Link href={`/admin/review?tab=records&kind=people&focus_kind=people&focus_id=${item.linked_person_id}`} prefetch={false}>등록 인물 관리 →</Link>}</div>
        <details><summary>기록 식별자</summary><small>{item.id}<br />{String(item.fields.provider_record_key)}</small></details>
      </article>)}</div>
      {queue.items.length === 0 && <p className="operator-empty">이 조건의 검토 기록이 없습니다. 다른 상태를 선택하거나 검색 조건을 바꾸세요.</p>}
      <nav className="operator-pagination" aria-label="인물 검토 페이지">
        {queue.offset > 0 && <Link prefetch={false} href={href(state, Math.max(0, queue.offset - queue.limit))}>← 이전</Link>}
        <span>{queue.offset + (queue.items.length ? 1 : 0)}–{queue.offset + queue.items.length} / {queue.total.toLocaleString()}</span>
        {queue.offset + queue.limit < queue.total && <Link prefetch={false} href={href(state, queue.offset + queue.limit)}>다음 →</Link>}</nav>
    </div><div className="admin-review-detail">
      <AdminActions kind="observations" ids={activeIds} labels={selectedItems.map((item) => String(item.fields.canonical_name ?? item.label))} capabilities={capabilities} />
      {error && <p className="admin-error" role="alert">{error}</p>}
      {detail ? <OperatorGraphView key={detail.graph.center} detail={detail} contextQuery="tab=records&kind=observations" /> : <p className="operator-empty">행의 ‘원문 경로·연결 확인’을 누르면 선택한 기록의 근거를 이 자리에서 확인합니다. 항목 선택과 근거 열람은 별개입니다.</p>}
    </div></div>
  </section>;
}

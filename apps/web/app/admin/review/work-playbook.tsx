"use client";

import { useRef, useState } from "react";
import Link from "next/link";
import { adminRequest } from "./admin-types";
import { KIND_LABELS, type OperatorRecord } from "./operator-types";

export type PlaybookCatalog = {
  recipes: { id: string; title: string; role: string; reviewer?: string; input_kinds: string[]; input_hint: string; outcome: string; href: string }[];
  configuration: { available: boolean; base_commit: string | null; working_tree_dirty: boolean | null; role_model_path: string };
  execution: { status: string; dispatch_enabled: boolean; reason: string; job_id: null; last_event: null };
  max_selected: number; max_parallel_children_policy: number; stage_labels: string[];
};
type Prepared = {
  work_order: { request_id: string; status: string; recipe_id: string; role: string; actor: string;
    prepared_at: string; environment_label: string; packet_sha256: string; source_content_included: boolean;
    references: { kind: string; id: string; version: string; view_href: string }[];
    source_policies: { policy_id: string; can_send_source_content_to_ai: boolean }[];
  };
  markdown: string; markdown_sha256: string;
};
const ROLES: Record<string, string> = { source_worker: "출처·수집 담당", record_curator: "기록 검토 담당", product_builder: "제품 개발 담당", quality_reviewer: "독립 검증 담당", risk_reviewer: "권리·신원 검토 담당" };

export default function WorkPlaybook({ catalog, records = [], initialRecipe = "person_review", expanded = false }: {
  catalog: PlaybookCatalog; records?: OperatorRecord[]; initialRecipe?: string; expanded?: boolean;
}) {
  const [recipeId, setRecipeId] = useState(initialRecipe);
  const [note, setNote] = useState("");
  const [area, setArea] = useState("admin");
  const [extras, setExtras] = useState<OperatorRecord[]>([]);
  const [lookupKind, setLookupKind] = useState("people");
  const [query, setQuery] = useState("");
  const [options, setOptions] = useState<{ id: string; label: string; kind: string; source_title?: string }[]>([]);
  const lookupGeneration = useRef(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [feedback, setFeedback] = useState("");
  const [prepared, setPrepared] = useState<{ signature: string; data: Prepared } | null>(null);
  const recipe = catalog.recipes.find((item) => item.id === recipeId) ?? catalog.recipes[0];
  const selection = [...new Map([...records, ...extras].map((item) => [`${item.kind}:${item.id}`, item])).values()];
  const signature = JSON.stringify({ recipeId, refs: selection.map((item) => [item.kind, item.id, item.version]), note, area });
  const current = prepared?.signature === signature ? prepared.data : null;
  const invalidVersion = selection.some((item) => !item.version);
  const kindMismatch = selection.some((item) => !recipe.input_kinds.includes(item.kind));
  const needsRecords = !["product_fix", "result_check"].includes(recipeId);
  const canPrepare = catalog.configuration.available && !invalidVersion && !kindMismatch && selection.length <= catalog.max_selected
    && (!needsRecords || selection.length > 0) && (recipeId !== "product_fix" || note.trim().length >= 10)
    && (recipeId !== "result_check" || selection.length > 0 || note.trim().length >= 10);

  async function search() {
    const generation = ++lookupGeneration.current;
    const kind = lookupKind;
    setBusy(true); setError("");
    try { const found = await adminRequest<{ items: typeof options }>("lookup", { kind, q: query });
      if (generation === lookupGeneration.current) setOptions(found.items.map((item) => ({ ...item, kind })));
    } catch (err) { if (generation === lookupGeneration.current) setError(err instanceof Error ? err.message : "후보 조회 실패"); }
    finally { if (generation === lookupGeneration.current) setBusy(false); }
  }
  async function attach(id: string, kind: string) {
    const generation = ++lookupGeneration.current;
    setBusy(true); setError("");
    try { const result = await adminRequest<{ record: OperatorRecord }>("lookup", { kind, id });
      if (generation === lookupGeneration.current) {
        setExtras((prior) => [...prior.filter((item) => !(item.kind === result.record.kind && item.id === id)), result.record]);
        setOptions([]); setFeedback("");
      }
    } catch (err) { if (generation === lookupGeneration.current) setError(err instanceof Error ? err.message : "자료 확인 실패"); }
    finally { if (generation === lookupGeneration.current) setBusy(false); }
  }
  async function prepare() {
    setBusy(true); setError(""); setFeedback(""); setPrepared(null);
    try {
      const data = await adminRequest<Prepared>("work_order_draft", { request_id: crypto.randomUUID(), recipe_id: recipeId,
        references: selection.map((item) => ({ kind: item.kind, id: item.id, version: item.version })), operator_note: note, code_area: area });
      setPrepared({ signature, data });
    } catch (err) { setError(err instanceof Error ? err.message : "요청서 준비 실패"); }
    finally { setBusy(false); }
  }
  async function copy() {
    if (!current) return;
    try { await navigator.clipboard.writeText(current.markdown); setFeedback("요청서 초안을 복사했습니다. 에이전트에 전송하거나 실행하지 않았습니다."); }
    catch { setFeedback("클립보드 사용이 거절됐습니다. Markdown 내려받기 또는 아래 텍스트를 사용하세요."); }
  }
  function download(format: "md" | "json") {
    if (!current) return;
    const text = format === "md" ? current.markdown : JSON.stringify(current.work_order, null, 2);
    const objectUrl = URL.createObjectURL(new Blob([text], { type: format === "md" ? "text/markdown;charset=utf-8" : "application/json" }));
    const anchor = document.createElement("a"); anchor.href = objectUrl; anchor.download = `civic-work-${current.work_order.request_id}.${format}`; anchor.click();
    setTimeout(() => URL.revokeObjectURL(objectUrl), 1000); setFeedback("초안을 내려받았습니다. 작업 접수·실행·DB 반영은 발생하지 않았습니다.");
  }
  return <details className="work-playbook" open={expanded || undefined}>
    <summary><strong>업무 플레이북</strong><span>{records.length ? `현재 선택 ${records.length}건으로 요청 준비` : "업무 선택 · 담당 · 입력 · 다음 단계"}</span></summary>
    <div className="work-playbook-body">
      <div className="work-stages" aria-label="업무 단계">{catalog.stage_labels.map((stage, index) => <span key={stage} data-active={index === (current ? 2 : 0)}>{index + 1}. {stage}</span>)}</div>
      <aside className="work-execution-state"><strong>에이전트 실행 미연동</strong><p>{catalog.execution.reason}</p>
        <small>현재 화면은 정확한 요청서 초안까지 준비합니다. 수집 실행·검토 결과·DB 반영 이력은 각 기존 화면에서 확인합니다.</small></aside>
      <div className="work-recipes" aria-label="업무 유형">{catalog.recipes.map((item) => <button type="button" key={item.id} aria-pressed={recipeId === item.id}
        onClick={() => { lookupGeneration.current++; setBusy(false); setRecipeId(item.id); setFeedback(""); setError(""); setExtras([]); setOptions([]); }}><strong>{item.title}</strong><span>{ROLES[item.role]}</span></button>)}</div>
      <div className="work-contract"><div><span>담당 역할</span><strong>{ROLES[recipe.role]} <small>({recipe.role})</small></strong></div>
        <div><span>준비 결과</span><strong>{recipe.outcome}</strong></div><div><span>반영 권한</span><strong>없음 · MAIN 검토와 기존 승인 경로를 거쳐야 합니다.</strong></div></div>
      <p className="operator-note">{recipe.input_hint} <Link href={recipe.href} prefetch={false}>관련 화면 열기 →</Link></p>
      <div className="work-selection"><strong>요청에 포함할 자료 {selection.length} / {catalog.max_selected}</strong>
        {selection.length === 0 && <p>현재 선택 자료가 없습니다. 관련 목록에서 선택하거나 코드 개선 내용을 입력하세요.</p>}
        {selection.length > 0 && <ul>{selection.map((record) => <li key={`${record.kind}:${record.id}`}><span>{KIND_LABELS[record.kind] ?? "변경 이력"} · {record.label}</span>
          <small>{record.id} · 버전 {record.version?.slice(0, 12) ?? "미제공 — 새로 조회 필요"}</small>
          {extras.some((item) => item.kind === record.kind && item.id === record.id) && <button type="button" onClick={() => setExtras((items) => items.filter((item) => !(item.kind === record.kind && item.id === record.id)))}>추가 자료 제외</button>}</li>)}</ul>}
      </div>
      {recipeId === "identity_link" && <fieldset><legend>후보 인물·공식 근거 추가</legend><div className="work-lookup">
        <label>추가 자료<select value={lookupKind} onChange={(event) => { lookupGeneration.current++; setBusy(false); setLookupKind(event.target.value); setOptions([]); }}><option value="people">후보 인물</option><option value="evidence">Evidence 근거</option></select></label>
        <label>이름·내용 검색<input value={query} maxLength={200} onChange={(event) => setQuery(event.target.value)} /></label><button type="button" disabled={busy} onClick={search}>찾기</button></div>
        {options.map((item) => <button className="work-lookup-result" type="button" key={item.id} disabled={busy || selection.length >= catalog.max_selected} onClick={() => attach(item.id, item.kind)}>
          {item.label} {item.source_title && `· ${item.source_title}`} <small>{item.id}</small> 추가</button>)}
        <p className="operator-note">후보·근거 선택은 동일인 확인이나 인간 검토를 완료했다는 뜻이 아닙니다.</p></fieldset>}
      {recipeId === "product_fix" && <label>제안할 수정 범위<select value={area} onChange={(event) => setArea(event.target.value)}><option value="admin">어드민 UI</option><option value="api">API</option><option value="graph">연결 지도</option></select></label>}
      <label>목적·재현 절차·확인할 점<textarea rows={3} maxLength={1500} value={note} onChange={(event) => { setNote(event.target.value); setFeedback(""); }} placeholder="원문·개인정보·비밀번호·토큰 없이 필요한 업무 맥락만 적어 주세요." /></label>
      {kindMismatch && <p className="work-warning">이 업무와 선택한 자료 종류가 맞지 않습니다. 관련 화면에서 필요한 입력을 선택하세요.</p>}
      {invalidVersion && <p className="work-warning">선택 자료의 버전이 없습니다. 최신 화면을 다시 여세요.</p>}
      {!catalog.configuration.available && <p className="work-warning">프로젝트 코드·역할 설정을 확인하지 못해 요청서 생성을 중단했습니다.</p>}
      <button type="button" className="work-primary" disabled={busy || !canPrepare} onClick={prepare}>{busy ? "선택 자료 검증 중…" : "선택 자료로 요청서 준비"}</button>
      {error && <p className="work-warning" role="alert">{error}</p>}
      {prepared && !current && <p className="work-warning">선택 자료나 입력 내용이 달라졌습니다. 요청서를 다시 준비해야 복사·내려받을 수 있습니다.</p>}
      {current && <section className="work-prepared" aria-label="준비된 작업 요청서"><h3>요청서 준비됨 · DRAFT</h3>
        <p>{current.work_order.environment_label} · 입력 {current.work_order.references.length}건 · 담당 {ROLES[current.work_order.role]}</p>
        <p className="operator-note">출처 내용은 내보내지 않습니다. ID·버전·허용된 참조만 포함하며, 이후 자료 접근·AI 전송 전에 출처 정책을 다시 확인해야 합니다.</p>
        {current.work_order.source_policies.some((p) => !p.can_send_source_content_to_ai) && <p className="work-warning">AI 전송이 허용되지 않은 출처가 포함되어 있습니다. 원문을 별도로 복사해 추가하지 마세요.</p>}
        <div className="work-actions"><button type="button" onClick={copy}>요청서 복사</button><button type="button" onClick={() => download("md")}>Markdown 내려받기</button><button type="button" onClick={() => download("json")}>참조 JSON</button></div>
        <dl><div><dt>요청서 ID (실행 ID 아님)</dt><dd>{current.work_order.request_id}</dd></div><div><dt>확인 시각</dt><dd>{current.work_order.prepared_at}</dd></div><div><dt>내용 SHA-256</dt><dd>{current.work_order.packet_sha256}</dd></div></dl>
        <details><summary>요청서 내용 확인</summary><pre>{current.markdown}</pre></details>
        <p className="operator-note">이 초안은 서버에 작업으로 저장되지 않습니다. 페이지를 떠나기 전에 필요한 파일을 내려받으세요. 실행·검증·반영은 아직 시작하지 않았습니다.</p>
      </section>}
      {feedback && <p role="status" className="work-feedback">{feedback}</p>}
      <footer className="operator-note">규칙: {catalog.configuration.role_model_path} · 기준 {catalog.configuration.base_commit?.slice(0, 12) ?? "확인 불가"}
        {catalog.configuration.working_tree_dirty && " · 미커밋 작업본"}</footer>
    </div>
  </details>;
}

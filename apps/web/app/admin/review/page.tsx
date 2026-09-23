import Link from "next/link";
import type { Metadata } from "next";
import type { ApiResult, OntologyGraph } from "../../types";
import { operatorRead, requireOperator } from "./operator-data";
import { KIND_LABELS, publicOntologyDetail, type Overview, type RecordPage, type OperatorDetail, type Manifest } from "./operator-types";
import OperatorGraphView from "./operator-graph";
import ReadState from "../../components/read-state";
import AdminQueue from "./admin-queue";
import AdminActions from "./admin-actions";
import { ACTION_LABELS, type AdminCapabilities, type ReviewQueue, type AdminHistory } from "./admin-types";
import "./operator.css";
import "./admin.css";

export const dynamic = "force-dynamic";
export const metadata: Metadata = { title: "인물·수집 데이터 관리 | Civic Intel", robots: { index: false, follow: false } };
const TABS = { "people-review": "인물 검토·등록", history: "변경 이력", overview: "수집 현황", records: "DB 목록·연결", manifest: "검토 manifest", catalog: "출처 계획·제약" };
const STATUS_OPTIONS: Record<string, Record<string, string>> = {
  claims: { DRAFT: "초안", REVIEW: "검토 중", PUBLISHED: "공개", WITHHELD: "비공개", CURRENT: "현재 버전", SUPERSEDED: "대체된 버전" },
  people: { RESOLVED: "확인된 인물", REVIEW: "신원 검토", UNRESOLVED: "미확정", CURRENT: "활성", SUPERSEDED: "비활성" },
  organizations: { CURRENT: "활성", SUPERSEDED: "비활성" },
  runs: { RUNNING: "실행 중", SUCCESS: "성공", PARTIAL: "부분 완료", FAILED: "실패" },
  reviews: { OPEN: "미처리", RESOLVED: "처리 완료", REJECTED: "대상 제외" },
  links: { CURRENT: "활성 연결", SUPERSEDED: "이전 연결" },
};
const METRICS = [
  ["current_people", "현재 인물"], ["current_organizations", "현재 기관"], ["current_claims", "현재 Claim"],
  ["published_claims", "공개 상태 Claim"], ["observations", "수집 기록 버전"], ["observation_keys", "고유 공급자 키"],
  ["sources", "출처"], ["open_reviews", "DB 미해결 검토"],
];
function time(value: string | null): string {
  if (!value) return "기록 없음";
  if (!/(Z|[+-][0-9]{2}:[0-9]{2})$/i.test(value)) return `${value.replace("T", " ")} (시간대 미기록)`;
  return new Date(value).toLocaleString("ko-KR", { timeZone: "Asia/Seoul", hour12: false });
}
function recordLink(kind: string, id?: string): string {
  const query = new URLSearchParams({ tab: "records", kind });
  if (id) { query.set("focus_kind", kind); query.set("focus_id", id); }
  return `/admin/review?${query}`;
}

export default async function ReviewPage({ searchParams }: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  await requireOperator(); // Gate before any operational fetch, including during public rendering.
  const raw = await searchParams;
  const get = (key: string) => typeof raw[key] === "string" ? raw[key] as string : "";
  const tab = get("tab") in TABS ? get("tab") as keyof typeof TABS : "people-review";
  const kind = get("kind") in KIND_LABELS ? get("kind") : "organizations";
  const q = get("q").slice(0, 200), status = get("status").slice(0, 32);
  const feeder = get("feeder").slice(0, 100), scope = get("scope").slice(0, 300);
  const offset = Math.min(100000, Math.max(0, Number.parseInt(get("offset"), 10) || 0));
  const view = get("view") === "relations" ? "relations" : "lineage";
  const query = new URLSearchParams({ tab, kind, q, status, feeder, scope, view, offset: String(offset) });
  const [overviewResult, capabilityResult] = await Promise.all([
    operatorRead<Overview>("/admin/operations"), operatorRead<AdminCapabilities>("/admin/operations/capabilities"),
  ]);
  if (overviewResult.state === "error") return <div className="site-page"><h1>수집·DB 운영</h1><ReadState error={overviewResult.error} /></div>;
  const overview = overviewResult.data;
  if (capabilityResult.state === "error") return <div className="site-page"><h1>관리 기능 연결 실패</h1><ReadState error={capabilityResult.error} /></div>;
  const capabilities = capabilityResult.data;
  const queueState = get("state") || "UNREVIEWED";
  if (tab === "people-review") query.set("state", queueState);
  const queueResult = tab === "people-review" ? await operatorRead<ReviewQueue>(`/admin/operations/people-review?${new URLSearchParams({ q, state: queueState, offset: String(offset), limit: "25" })}`) : null;
  const historyResult = tab === "history" ? await operatorRead<AdminHistory>(`/admin/operations/history?offset=${offset}&limit=25`) : null;
  const listResult = tab === "records" ? await operatorRead<RecordPage>(`/admin/operations/records?${new URLSearchParams({ kind, q, status, feeder, scope, offset: String(offset), limit: "25" })}`) : null;
  const list = listResult?.state === "success" ? listResult.data : null;
  const focusKind = get("focus_kind") in KIND_LABELS ? get("focus_kind") : kind;
  const requestedId = get("focus_id") || list?.items[0]?.id || "";
  const focusId = /^[0-9a-f-]{36}$/i.test(requestedId) ? requestedId : "";
  let detailResult: ApiResult<OperatorDetail> | null = tab === "records" && focusId
    ? await operatorRead<OperatorDetail>(`/admin/operations/records/${focusKind}/${focusId}`) : null;
  if (view === "relations" && ["people", "organizations"].includes(focusKind) && detailResult?.state === "success") {
    const publicResult = await operatorRead<OntologyGraph>(`/ontology/${focusKind}/${focusId}`);
    detailResult = publicResult.state === "success"
      ? { state: "success", data: publicOntologyDetail(publicResult.data, detailResult.data.record) } : publicResult;
  }
  const viewHref = (nextView: string) => { const next = new URLSearchParams(query); next.set("view", nextView);
    next.set("focus_kind", focusKind); next.set("focus_id", focusId); return `/admin/review?${next}`; };
  const manifestResult = tab === "manifest" ? await operatorRead<Manifest>("/admin/operations/manifest") : null;
  const manifest = manifestResult?.state === "success" ? manifestResult.data : null;
  const pageHref = (position: number) => { const next = new URLSearchParams(query); next.set("offset", String(position)); return `/admin/review?${next}`; };
  const selectHref = (id: string) => { const next = new URLSearchParams(query); next.set("focus_kind", kind); next.set("focus_id", id); return `/admin/review?${next}`; };
  const laneKind = ["observations", "runs", "checkpoints"].includes(kind);

  return <div className="site-page operator-page" data-view={tab}>
    <header className="operator-header"><div><div className="eyebrow">Civic Intel / Operator workspace</div>
      <h1>인물·수집 데이터 관리</h1><p>무엇을 수집했고, 어디에 저장했으며, 어떤 근거로 연결되었는지 확인합니다.</p></div>
      <div className="operator-runtime"><strong>{overview.environment_label} · {capabilities.writes_enabled ? "ADMIN WRITE" : "READ / PREVIEW"}</strong>
        <span>확인 {time(overview.checked_at)} KST</span><span>스키마 {capabilities.schema_ready ? capabilities.schema_required : "0006 · 변경 이력 준비 필요"} · 환경명은 운영자 지정</span>
        <form action="/admin/review" method="get">
          {[...query.entries()].map(([name, value]) => <input key={name} type="hidden" name={name} value={value} />)}
          {focusId && <><input type="hidden" name="focus_kind" value={focusKind} /><input type="hidden" name="focus_id" value={focusId} /></>}
          <button className="operator-refresh" type="submit">현재 DB 다시 확인 ↻</button>
        </form></div></header>
    <aside className="operator-scope">운영자 {capabilities.actor} · {capabilities.writes_enabled ? "미리보기와 최종 확인을 거친 작업만 DB에 반영합니다." : "현재 연결에서는 목록 검토와 변경 미리보기를 사용할 수 있습니다."} 인물 검토 큐는 수집 기록을 기준으로 계산하며 DB의 OPEN 항목 수와 다릅니다. 원본 수집 기록은 보존합니다.</aside>
    <div className="operator-metrics">{METRICS.filter(([key]) => tab !== "people-review" || ["current_people", "current_organizations", "observations"].includes(key)).map(([key, label]) => <div key={key}><span>{label}</span><strong>{overview.counts[key]?.toLocaleString("ko-KR") ?? "—"}</strong></div>)}</div>
    <nav className="operator-tabs" aria-label="운영 메뉴">{Object.entries(TABS).map(([key, label]) => <Link prefetch={false}
      key={key} aria-current={tab === key ? "page" : undefined} href={`/admin/review?tab=${key}`}>{label}</Link>)}</nav>

    {tab === "people-review" && (queueResult?.state === "success" ? <AdminQueue key={`${queueState}:${q}:${offset}`} queue={queueResult.data} capabilities={capabilities} q={q} state={queueState} />
      : queueResult?.state === "error" ? <ReadState error={queueResult.error} /> : null)}
    {tab === "history" && <section><div className="operator-section-head"><div><span className="micro-label">COMMITTED ADMIN OPERATIONS</span><h2>운영 변경 이력</h2></div></div>
      {historyResult?.state === "error" && <ReadState error={historyResult.error} />}
      {historyResult?.state === "success" && (!historyResult.data.available ? <p className="admin-notice">아직 변경 이력 DB가 준비되지 않았습니다. 이 환경에서 작업 완료를 주장하지 않습니다.</p> : <>
        <p>DB 반영이 완료된 작업 {historyResult.data.total}건. 취소·실패한 미리보기는 완료 이력에 포함하지 않습니다.</p>
        {historyResult.data.items.map((entry) => <article className="admin-history-entry" key={entry.id}>
          <div className="operator-section-head"><strong>{ACTION_LABELS[entry.action] ?? entry.action}</strong><span>{entry.actor} · {time(entry.created_at)}</span></div>
          <p>{entry.reason}</p><small>요청 ID {entry.id} · 변경 {entry.result.changed_rows}행</small>
          <details><summary>변경 전후와 처리 결과</summary><pre>{JSON.stringify({ changes: entry.changes, result: entry.result }, null, 2)}</pre></details>
        </article>)}
        <nav className="operator-pagination">{offset > 0 && <Link href={pageHref(Math.max(0, offset - 25))} prefetch={false}>← 이전</Link>}
          {offset + 25 < historyResult.data.total && <Link href={pageHref(offset + 25)} prefetch={false}>다음 →</Link>}</nav>
      </>)}
    </section>}

    {tab === "overview" && <section><div className="operator-section-head"><div><span className="micro-label">PERSISTED COLLECTION LANES</span><h2>실제 DB 수집 경로</h2></div>
      <span>{overview.lanes.length}개 범위{overview.lanes_truncated ? " · 목록 제한 500" : ""}</span></div>
      <p className="operator-note">성공한 실행도 전체 출처 수집 완료를 뜻하지 않습니다. 공급자 전체 분모가 검증되지 않은 범위에는 진행률을 만들지 않습니다.</p>
      {overview.lanes.length === 0 ? <p className="operator-empty">이 DB에는 수집 실행·기록·체크포인트가 아직 없습니다. 아래 DB 레코드 수와 출처 계획을 별도로 확인하세요.</p> :
        <div className="operator-table-scroll"><table className="operator-table"><thead><tr><th>수집 경로 / 범위</th><th>최근 실행</th><th>저장 버전 / 고유 키</th><th>최근 실행 결과</th><th>성공 / 체크포인트</th><th>확인</th></tr></thead>
          <tbody>{overview.lanes.map((lane) => <tr key={`${lane.feeder}:${lane.scope_key}`}><td><strong>{lane.feeder}</strong><small>{lane.scope_key}</small></td>
            <td><span className="operator-tag">{lane.latest_run_status ?? "NO_RUN"}</span><small>{time(lane.latest_run_started_at)}</small></td>
            <td>{lane.observation_versions.toLocaleString()} / {lane.provider_keys.toLocaleString()}</td>
            <td>확인 {lane.records_seen ?? "—"}<small>신규 {lane.observations_created ?? "—"} · 변화 없음 {lane.observations_unchanged ?? "—"}</small></td>
            <td><small>성공 {time(lane.last_success_at)}</small><small>체크포인트 {time(lane.checkpoint_updated_at)}</small></td>
            <td><Link prefetch={false} href={`/admin/review?${new URLSearchParams({ tab: "records", kind: "observations", feeder: lane.feeder, scope: lane.scope_key })}`}>기록 목록 →</Link>
              {lane.latest_run_id && <small><Link prefetch={false} href={recordLink("runs", lane.latest_run_id)}>실행 근거 →</Link></small>}</td></tr>)}</tbody></table></div>}
      <details className="operator-db-inventory"><summary>DB 테이블별 전체 행 수 확인</summary><div className="operator-inventory-grid">
        {Object.entries(KIND_LABELS).map(([key, label]) => <Link key={key} prefetch={false} href={recordLink(key)}><span>{label}</span><strong>{overview.counts[key]?.toLocaleString() ?? 0}</strong></Link>)}
      </div><p className="operator-note">전체 행에는 과거·대체된 버전이 포함될 수 있습니다. 위의 현재 레코드 수와 구분합니다.</p></details>
    </section>}

    {tab === "records" && <section><nav className="operator-kind-tabs" aria-label="DB 레코드 종류">{Object.entries(KIND_LABELS).map(([key, label]) =>
      <Link key={key} href={recordLink(key)} prefetch={false} aria-current={key === kind ? "page" : undefined}>{label} <small>{overview.counts[key]?.toLocaleString()}</small></Link>)}</nav>
      <form className="operator-filters" method="get" action="/admin/review"><input type="hidden" name="tab" value="records" /><input type="hidden" name="kind" value={kind} />
        <label>이름·내용·ID 검색<input type="search" name="q" defaultValue={q} maxLength={200} placeholder="수집된 이름이나 기록을 검색" /></label>
        {["claims", "people", "organizations", "runs", "reviews", "links"].includes(kind) && <label>상태<select name="status" defaultValue={status}><option value="">전체 상태</option>{Object.entries(STATUS_OPTIONS[kind] ?? {}).map(([value, label]) => <option value={value} key={value}>{label}</option>)}</select></label>}
        {laneKind && <><label>수집 경로<input name="feeder" defaultValue={feeder} maxLength={100} /></label><label>수집 범위<input name="scope" defaultValue={scope} maxLength={300} /></label></>}
        <button type="submit">검색·필터 적용</button><Link href={recordLink(kind)} prefetch={false}>초기화</Link></form>
      {listResult?.state === "error" && <ReadState error={listResult.error} />}
      {list && <div className="operator-workbench"><div className="operator-record-panel"><div className="operator-section-head"><h2>{KIND_LABELS[kind]} 목록</h2><span>{list.total.toLocaleString()}건</span></div>
        <p className="operator-note">현재 {Math.min(offset + 1, list.total)}–{Math.min(offset + list.items.length, list.total)} / {list.total.toLocaleString()} · 25개씩</p>
        {list.items.length === 0 ? <p className="operator-empty">이 조건에 해당하는 저장 기록이 없습니다.</p> : <div className="operator-record-list">
          {list.items.map((item) => <Link key={item.id} href={selectHref(item.id)} prefetch={false} className="operator-record"
            aria-current={item.id === focusId && kind === focusKind ? "true" : undefined}><span className="operator-record-heading"><strong>{item.label}</strong><span className="operator-tag">{item.status}</span></span>
            <span>{String(item.fields.object_text ?? item.fields.position_text ?? item.fields.semantic_scope ?? item.fields.publisher ?? item.fields.scope_key ?? "저장된 canonical 레코드").slice(0, 220)}</span>
            <small>{String(item.fields.fiscal_year ?? item.fields.business_year ?? item.fields.audit_date ?? "")} {String(item.fields.predicate ?? "")} {String(item.fields.epistemic_status ?? "")} · {item.id}</small></Link>)}
        </div>}
        <nav className="operator-pagination" aria-label="목록 페이지">{offset > 0 && <Link href={pageHref(Math.max(0, offset - 25))} prefetch={false}>← 이전 25개</Link>}
          {offset + 25 < list.total && <Link href={pageHref(offset + 25)} prefetch={false}>다음 25개 →</Link>}</nav></div>
        <div className="operator-detail">
          {["people", "organizations"].includes(focusKind) && focusId && <nav className="operator-kind-tabs" aria-label="연결 종류">
            <Link prefetch={false} href={viewHref("lineage")} aria-current={view === "lineage" ? "page" : undefined}>DB 근거·수집 경로</Link>
            <Link prefetch={false} href={viewHref("relations")} aria-current={view === "relations" ? "page" : undefined}>공개된 직책·임원 관계</Link>
          </nav>}
          {detailResult?.state === "success" && ["people", "claims", "observations"].includes(focusKind) && <AdminActions key={`action:${focusKind}:${focusId}`} kind={focusKind} ids={[focusId]} labels={[detailResult.data.record.label]} capabilities={capabilities} />}
          {detailResult?.state === "success" ? <OperatorGraphView key={`${focusKind}:${focusId}:${view}`} detail={detailResult.data} contextQuery={query.toString()} />
          : detailResult?.state === "error" ? <ReadState error={detailResult.error} /> : <p className="operator-empty">목록에서 기록을 선택하면 연결 지도와 내용이 표시됩니다.</p>}</div></div>}
    </section>}

    {tab === "manifest" && <section><div className="operator-section-head"><div><span className="micro-label">EXACT REVIEWED ARTIFACT</span><h2>org.go 기관 반영 사전검증</h2></div><span className="operator-tag">NO WRITE</span></div>
      {manifestResult?.state === "error" && <ReadState error={manifestResult.error} />}
      {manifest && <><div className="operator-scope"><strong>{manifest.status}</strong> · {manifest.message}</div>
        <p>{manifest.item_count ?? "—"}개 검토 항목 · 생성 예상 {manifest.organizations_to_create ?? "검증 차단"} · 재사용 {manifest.organizations_to_reuse ?? "검증 차단"}</p>
        <p className="operator-note">기관 존재 여부와 Gukgam Claim 공개는 별도입니다. 반영 실행·과거 commit receipt 증명 기능은 포함하지 않습니다.</p>
        <details className="operator-hashes"><summary>검토 manifest·proposal 해시</summary><p>Manifest: {manifest.manifest_sha256}</p><p>Proposal: {manifest.proposal_core_sha256}</p></details>
        {manifest.items && <div className="operator-table-scroll"><table className="operator-table"><thead><tr><th>검토 기관</th><th>orgCode / chartId</th><th>사전검증</th><th>국감 검토 occurrence</th><th>기록·출처</th></tr></thead>
          <tbody>{manifest.items.map((item) => <tr key={item.org_code}><td><strong>{item.organization_name}</strong><small>{item.category}</small></td>
            <td>{item.org_code} / {item.chart_id}</td><td>{item.action}</td><td>{item.review_occurrences}건 · 공개 관계 아님</td>
            <td><Link prefetch={false} href={recordLink("organizations", item.organization_id)}>DB 존재 확인 →</Link>
              {item.source_locator && <small><a href={item.source_locator} target="_blank" rel="noreferrer">공식 출처 ↗</a></small>}</td></tr>)}</tbody></table></div>}</>}
    </section>}

    {tab === "catalog" && <section><div className="operator-section-head"><div><span className="micro-label">DOCUMENTED SOURCE STRATEGY</span><h2>수집 출처 계획·제약</h2></div><span>{overview.documented_catalog.length}개 문서 항목</span></div>
      <p className="operator-scope">기존 FEEDER_SOURCE_COVERAGE.md의 문서상 성숙도입니다. 이 DB에 실제 데이터가 있다는 뜻이 아니며, 실시간 수집 현황과 별도로 봅니다.</p>
      <div className="operator-table-scroll"><table className="operator-table"><thead><tr><th>출처 경로</th><th>대상 범위</th><th>출처 / 방식</th><th>문서상 준비 단계·제약</th></tr></thead>
        <tbody>{overview.documented_catalog.map((item) => <tr key={item.name}><td><strong>{item.name}</strong></td><td>{item.scope}</td><td>{item.source}<small>{item.mode}</small></td><td>{item.maturity}</td></tr>)}</tbody></table></div>
    </section>}
    <footer className="operator-footnote">원본 전문·연락처·민감 필드·접속 정보는 표시하지 않습니다. 이 화면은 canonical DB의 허용된 조회 모델이며 별도 데이터 저장소가 아닙니다.</footer>
  </div>;
}

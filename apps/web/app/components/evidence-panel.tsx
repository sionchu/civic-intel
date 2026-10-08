import { sourceClassLabel, statusLabel } from "../display-labels";
import type { ReactNode } from "react";

import type { Claim, EvidenceTrace, Source } from "../types";

// The single evidence presentation path for Person and Organization pages. A rendered Claim is a
// native <details> disclosure: the collapsed line keeps status, as-of date and source name adjacent
// to the item; the expanded definition list walks Claim -> Evidence -> Source. Operational IDs stay
// inside the nested audit disclosure.

const KST = "Asia/Seoul";

export function formatDay(value: string | null | undefined): string | null {
  if (!value) return null;
  if (/^\d{4}-\d{2}-\d{2}$/.test(value)) return value;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("sv-SE", { timeZone: KST, year: "numeric", month: "2-digit", day: "2-digit" }).format(date);
}

export function formatDateTime(value: string | null | undefined): string | null {
  if (!value) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  const text = new Intl.DateTimeFormat("sv-SE", {
    timeZone: KST, year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit",
  }).format(date);
  return `${text} 한국 시간`;
}

const QUALIFIER_LABELS: Record<string, string> = {
  audit_date: "감사일",
  bill_no: "의안번호", bill_name: "법안명", proposed_date: "발의일",
  committee: "소관위원회", vote_value_published: "표결", vote_datetime: "표결 시각",
  participation_role: "발의 구분", publication_date: "공개일", registration_date: "신고 등록일", report_type: "신고유형",
  committee_name: "위원회",
  section: "구분",
  page_number: "쪽",
  audited_target: "피감대상",
  time_text: "시간",
  venue: "장소",
  field_name: "필드",
  fiscal_year: "회계연도",
  as_of: "기준일",
  position_text: "직위",
  title: "직책",
  canonical_name: "공개 이름",
  term_start: "임기 시작",
  term_end: "임기 종료",
  disclosure_no: "공시번호",
  classification_text: "기관 분류",
  list_title: "명단",
  list_version: "명단 판",
  list_year: "연도",
  adoption_date: "의결일",
  category: "증인·참고인",
  affiliation_title: "명단 기재 소속·직위",
  list_section: "명단 구분",
  attendance_date_text: "출석 요구일(기재)",
  attendance_date: "출석 요구일",
  assumed_year_basis: "연도 근거",
  acquisition_channel: "수집 경로",
  source_tag: "명단 구분",
  provenance_label: "출처 상태",
  row_number: "명단 행",
  table_index: "표",
  table_row: "표 행",
  corp_name: "회사",
  corp_code: "DART 고유번호",
  stock_code: "종목코드",
  business_year: "사업연도",
  report_code: "보고서 코드",
  receipt_no: "공시 접수번호",
  settlement_date: "결산기준일",
  position: "직위(공시)",
  registered_status: "등기 여부",
  full_time_status: "상근 여부",
  responsibility: "담당 업무",
  tenure_text: "재직 기간(공시)",
  tenure_end_on: "임기 만료일",
  reported_main_career: "주요경력(회사 공시·독립 검증 전)",
};

// Shown elsewhere in the panel, or identifiers / hashes that belong in the audit disclosure.
const HIDDEN_QUALIFIERS = new Set([
  "source_published_date",
  "source_scope", "semantic_scope", "event_semantics",
  "provider_record_key", "observation_provider_record_key", "immutable_observation_hash",
  "audited_target_index", "alio_apba_id", "classification", "executive_kind",
  "source_claim_id", "source_observation_id", "identity_review_id", "identity_scope",
  "reported_main_career_semantics", "organization_id",
  // Normalized date anchors are not literal source values. Career presentation preserves units.
  "period_start", "period_end", "period_point", "period_start_precision", "period_end_precision",
  "period_point_precision", "period_ongoing",
]);

const CONTRACT_NOTES: Record<string, string> = {
  assembly_member_roster: "국회 의원 명부의 필드를 값 그대로 옮긴 기록",
  gukgam_reviewed_plan_attachment_v1: "검토를 거친 국정감사 계획서 첨부의 일정 항목",
  alio_item_4_current_executive_roster: "ALIO 항목 4 임원현황 공시의 항목",
  alio_reviewed_person_role: "ALIO 임원현황 공시 행을 사람이 검토해 이 인물에 연결한 기록",
  gukgam_witness_reviewed_person_link:
    "위원회 증인·참고인 명단의 한 행을 사람이 검토해 이 인물에 연결한 기록. 출석 요구 기재이며 혐의나 잘못을 뜻하지 않음",
  opendart_reviewed_executive_role:
    "회사가 OpenDART 임원 현황 공시에 기재한 내용을 사람이 검토해 이 인물에 연결한 기록. 주요경력은 회사 제출 내용",
};

const SCOPE_NOTES: Record<string, string> = {
  legislative_member_roster: "국회 현재 의원 명부 기준",
  national_assembly_audit_plan_schedule: "국회 위원회 감사 계획서 일정 기준",
  public_institution_executive_disclosure: "공공기관 임원 공시 기준",
};

const PERMISSION: Record<string, string> = { PERMITTED: "허용", NOT_PERMITTED: "불가" };

function policyText(source: Source): string {
  const policy = source.policy_summary;
  return [
    `수집 ${PERMISSION[policy.collection] ?? "미확인"}`,
    `메타데이터 저장 ${PERMISSION[policy.metadata_storage] ?? "미확인"}`,
    `전문 저장 ${PERMISSION[policy.fulltext_storage] ?? "미확인"}`,
    `발췌 표시 ${PERMISSION[policy.excerpt_display] ?? "미확인"}`,
  ].join(" · ");
}

function claimSources(claim: Claim, sourceById: Map<string, Source>): { ids: string[]; sources: Source[] } {
  const ids = [...new Set([...claim.evidence.map((item) => item.source_id), ...claim.source_ids])];
  return { ids, sources: ids.flatMap((id) => sourceById.get(id) ?? []) };
}

function qualifierText(key: string, value: string): string {
  if (value === "UNKNOWN") return "미확인";
  if (key === "participation_role") return value === "REPRESENTATIVE_PROPOSER" ? "대표 발의" : value === "CO_PROPOSER" ? "공동 발의" : "발의 구분 미확인";
  if (key === "acquisition_channel") return ({ OFFICIAL_SITE: "공식 게시", OFFICIAL_MINUTES: "공식 회의록", OWNER_SUPPLIED_COPY: "제공 사본" } as Record<string, string>)[value] ?? "수집 경로 미확인";
  return value;
}

export default function EvidencePanel({
  claim,
  sourceById,
  title,
  kind,
  className,
  sourceConflict = false,
  dateLabel = "기준",
  claimAnchor = true,
  children,
}: {
  claim: Claim;
  sourceById: Map<string, Source>;
  title?: string;
  kind?: string;
  className?: string;
  sourceConflict?: boolean;
  dateLabel?: string;
  claimAnchor?: boolean;
  children?: ReactNode;
}) {
  const conflict = sourceConflict || claim.source_conflict === true;
  const { ids: sourceIds, sources } = claimSources(claim, sourceById);
  const asOf = formatDay(claim.valid_from);
  const validTo = formatDay(claim.valid_to);
  const qualifiers = claim.qualifiers;
  const position = [qualifiers.section, qualifiers.page_number ? `${qualifiers.page_number}쪽` : null]
    .filter(Boolean)
    .join(" · ");
  const rawValues = Object.entries(qualifiers).filter(
    ([key, value]) => key in QUALIFIER_LABELS && !HIDDEN_QUALIFIERS.has(key) && typeof value === "string" && value !== "" && value.length <= 120,
  );
  const contract = qualifiers.source_contract;
  const scopeNote = qualifiers.semantic_scope ? SCOPE_NOTES[qualifiers.semantic_scope] ?? null : null;
  const processing = contract ? [CONTRACT_NOTES[contract] ?? "출처의 공개 항목을 옮긴 기록", scopeNote].filter(Boolean).join(" · ") : null;
  const limits = [
    qualifiers.event_semantics === "OFFICIAL_PLAN_LISTING_NOT_COMPLETED_AUDIT"
      ? "공식 계획서상 일정 목록이며 감사가 실제로 열렸다는 기록이 아닙니다."
      : null,
    "출처가 말한 범위까지만 표시합니다.",
  ].filter((item): item is string => item !== null);
  const firstSource = sources[0];

  return (
    <article className={`claim evidence-panel${className ? ` ${className}` : ""}`} id={claimAnchor ? `claim-${claim.id}` : undefined}>
      {kind && <span className="claim-kind">{kind}</span>}
      <p className="claim-title">{title ?? claim.proposition}</p>
      {children}
      {claim.resolution_note && <p className="resolution">{claim.resolution_note}</p>}
      <details className="evidence-disclosure">
        <summary>
          <span className="evidence-summary-line">
            <span className={`status ${claim.epistemic_status}`}>{statusLabel(claim.epistemic_status)}</span>
            {claim.publication_status !== "PUBLISHED" && (
              <span className="status UNKNOWN">{statusLabel(claim.publication_status)}</span>
            )}
            {conflict && <span className="status CONFLICT">{statusLabel("CONFLICT")}</span>}
            <span className="evidence-asof">{dateLabel} {asOf ?? "기준일 미기재"}</span>
            {firstSource && (
              <span className="evidence-source-name">
                {firstSource.title}{sources.length > 1 ? ` 외 ${sources.length - 1}` : ""}
              </span>
            )}
          </span>
          <span className="evidence-toggle">
            <span className="when-closed">근거 열기</span>
            <span className="when-open">근거 닫기</span>
          </span>
        </summary>
        <dl className="evidence-dl">
          <div><dt>기록</dt><dd>{claim.proposition}</dd></div>
          <div>
            <dt>상태</dt>
            <dd>
              <span className="evidence-chips">
                <span className={`status ${claim.epistemic_status}`}>{statusLabel(claim.epistemic_status)}</span>
                <span className="evidence-plain">공개 상태 {statusLabel(claim.publication_status)}</span>
                {conflict && <span className="status CONFLICT">{statusLabel("CONFLICT")}</span>}
              </span>
              {conflict && (
                <small>서로 다른 근거가 상충하며 자동으로 어느 한쪽을 진실로 판정하지 않습니다.</small>
              )}
            </dd>
          </div>
          <div>
            <dt>{dateLabel === "기록 기준" ? "기록 유효 기간" : "유효 기간"}</dt>
            <dd>{asOf ?? "시작일 미기재"} – {validTo ?? "종료일 없음"}</dd>
          </div>
          <div>
            <dt>기록 시각</dt>
            <dd>
              {formatDateTime(claim.recorded_at) ?? "미기재"}
              <small>이 서비스가 기록을 저장한 시각이며 현실 세계의 사건 시각이 아닙니다.</small>
            </dd>
          </div>
          <div>
            <dt>근거</dt>
            <dd>
              {claim.evidence.length === 0 ? "연결된 근거가 없습니다." : (
                <ul className="evidence-rows">
                  {claim.evidence.map((item) => {
                    const source = sourceById.get(item.source_id);
                    return (
                      <li key={item.id}>
                        <span className={`status ${item.stance}`}>{statusLabel(item.stance)}</span>
                        {source ? <a href={`#source-${source.id}`}>{source.title}</a> : <span>출처 정보를 불러오지 못했습니다</span>}
                      </li>
                    );
                  })}
                </ul>
              )}
            </dd>
          </div>
          <div>
            <dt>출처</dt>
            <dd>
              {sources.length === 0 ? "출처 정보를 불러오지 못했습니다." : (
                <ul className="evidence-sources">
                  {sources.map((source) => {
                    const published = formatDay(source.published_at) ?? formatDay(qualifiers.source_published_date);
                    return (
                      <li key={source.id}>
                        <span>{source.publisher} · <a href={source.url} target="_blank" rel="noreferrer">{source.title} <span aria-hidden="true">↗</span></a></span>
                        <small>
                          {published ? `공개일 ${published}` : "공개일 미기재"}
                          {position && <> · 위치 {position}</>}
                          {" "}· 확인 시각 {formatDateTime(source.terms_checked_at) ?? "미기재"}
                        </small>
                      </li>
                    );
                  })}
                </ul>
              )}
            </dd>
          </div>
          {rawValues.length > 0 && (
            <div>
              <dt>원문 값</dt>
              <dd>
                <ul className="evidence-values">
                  {rawValues.map(([key, value]) => (
                    <li key={key}><span>{QUALIFIER_LABELS[key]}</span> {qualifierText(key, value)}</li>
                  ))}
                </ul>
                <small>출처에 기재된 값을 그대로 표시합니다.</small>
              </dd>
            </div>
          )}
          {processing && <div><dt>처리 방식</dt><dd>{processing}</dd></div>}
          {sources.length > 0 && (
            <div>
              <dt>출처 정책</dt>
              <dd>
                {sources.map((source) => (
                  <span className="evidence-policy" key={source.id}>
                    {sources.length > 1 && <strong>{source.publisher}</strong>}
                    {policyText(source)}
                  </span>
                ))}
              </dd>
            </div>
          )}
          <div>
            <dt>한계</dt>
            <dd>{limits.map((item) => <span className="evidence-limit" key={item}>{item}</span>)}</dd>
          </div>
        </dl>
        <details className="audit-details evidence-audit">
          <summary>근거 식별자</summary>
          <small>
            기록 {claim.id}<br />
            판단 상태 식별값 {claim.epistemic_status} · 공개 상태 식별값 {claim.publication_status}<br />
            {Object.entries(qualifiers).filter(([key]) => !(key in QUALIFIER_LABELS) && !HIDDEN_QUALIFIERS.has(key)).map(([key, value]) => <span key={key}>기록 속성 식별값 {key}: {String(value)}<br /></span>)}
            {claim.person_id && <>인물 {claim.person_id}<br /></>}
            {claim.organization_id && <>기관 {claim.organization_id}<br /></>}
            {claim.evidence.map((item) => (
              <span key={item.id}>
                근거 {item.id}<br />
                {item.snapshot_id && <>출처 저장본 {item.snapshot_id}<br /></>}
                {item.feeder_observation_id && <>수집 기록 {item.feeder_observation_id}<br /></>}
              </span>
            ))}
            {sourceIds.map((id) => <span key={id}>출처 {id}<br /></span>)}
          </small>
        </details>
      </details>
    </article>
  );
}

// Derived read models (change trace, money comparison) are not Claims; they reuse the same
// evidence row so there is one stance + source presentation.
export function EvidenceTraceList({
  traces,
  sourceById,
  claimLabel,
}: {
  traces: Pick<EvidenceTrace, "id" | "stance" | "source_id" | "snapshot_id" | "feeder_observation_id">[];
  sourceById: Map<string, Source>;
  claimLabel?: string;
}) {
  if (traces.length === 0) return null;
  return (
    <div className="evidence-list">
      <div className="evidence-list-heading"><strong>근거 추적</strong><span>{traces.length}건</span></div>
      {traces.map((trace) => {
        const source = sourceById.get(trace.source_id);
        return (
          <div className="evidence-trace" key={trace.id}>
            <span className={`status ${trace.stance}`}>{statusLabel(trace.stance)}</span>
            {source ? <a href={`#source-${source.id}`}>{source.title}</a> : <span>출처 정보를 불러오지 못했습니다</span>}
            <details className="audit-details">
              <summary>근거 식별자</summary>
              <small>
                근거 {trace.id}<br />
                {claimLabel && <>기록 {claimLabel}<br /></>}
                출처 {trace.source_id}<br />
                {trace.snapshot_id && <>출처 저장본 {trace.snapshot_id}<br /></>}
                {trace.feeder_observation_id && <>수집 기록 {trace.feeder_observation_id}</>}
              </small>
            </details>
          </div>
        );
      })}
    </div>
  );
}

export function SourceCard({ source }: { source: Source }) {
  return (
    <article className="source" id={`source-${source.id}`}>
      <h3><a href={source.url} target="_blank" rel="noreferrer">{source.title}</a></h3>
      <p className="source-meta">
        {source.publisher} <span>·</span> {source.published_at ? `공개일 ${formatDay(source.published_at)}` : "공개일 미기재"} <span>·</span> {sourceClassLabel(source.source_class)}
      </p>
      <p className="source-license">이용 조건: {source.license ?? "이용 조건 미기재"}</p>
      <p className="source-license">출처 정책 {policyText(source)}</p>
      <p className="source-license">확인 시각 {formatDateTime(source.terms_checked_at) ?? "미기재"}</p>
      <details className="audit-details">
        <summary>근거 식별자</summary>
        <small>출처 {source.id}<br />자료 유형 식별값 {source.source_class}<br />원문 주소 {source.url}</small>
      </details>
    </article>
  );
}

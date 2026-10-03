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
  return `${text} KST`;
}

const QUALIFIER_LABELS: Record<string, string> = {
  audit_date: "감사일",
  committee_name: "위원회",
  section: "구분",
  page_number: "쪽",
  audited_target: "피감대상",
  time_text: "시간",
  venue: "장소",
  field_name: "필드",
  source_contract: "수집 계약",
  fiscal_year: "회계연도",
  as_of: "기준일",
  position_text: "직위",
  title: "직책",
  canonical_name: "공개 이름",
  term_start: "임기 시작",
  term_end: "임기 종료",
  disclosure_no: "공시번호",
  classification_text: "기관 분류",
};

// Shown elsewhere in the panel, or identifiers / hashes that belong in the audit disclosure.
const HIDDEN_QUALIFIERS = new Set([
  "source_published_date",
  "source_scope", "semantic_scope", "event_semantics",
  "provider_record_key", "observation_provider_record_key", "immutable_observation_hash",
  "audited_target_index", "alio_apba_id", "classification", "executive_kind",
]);

const CONTRACT_NOTES: Record<string, string> = {
  assembly_member_roster: "국회 의원 명부의 필드를 값 그대로 옮긴 기록",
  gukgam_reviewed_plan_attachment_v1: "검토를 거친 국정감사 계획서 첨부의 일정 항목",
  alio_item_4_current_executive_roster: "ALIO 항목 4 임원현황 공시의 항목",
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
    `수집 ${PERMISSION[policy.collection]}`,
    `메타데이터 저장 ${PERMISSION[policy.metadata_storage]}`,
    `전문 저장 ${PERMISSION[policy.fulltext_storage]}`,
    `발췌 표시 ${PERMISSION[policy.excerpt_display]}`,
  ].join(" · ");
}

function claimSources(claim: Claim, sourceById: Map<string, Source>): { ids: string[]; sources: Source[] } {
  const ids = [...new Set([...claim.evidence.map((item) => item.source_id), ...claim.source_ids])];
  return { ids, sources: ids.flatMap((id) => sourceById.get(id) ?? []) };
}

export default function EvidencePanel({
  claim,
  sourceById,
  title,
  kind,
  className,
  sourceConflict = false,
  children,
}: {
  claim: Claim;
  sourceById: Map<string, Source>;
  title?: string;
  kind?: string;
  className?: string;
  sourceConflict?: boolean;
  children?: ReactNode;
}) {
  const conflict = sourceConflict || claim.source_conflict === true;
  const { ids: sourceIds, sources } = claimSources(claim, sourceById);
  const asOf = formatDay(claim.valid_from);
  const validTo = formatDay(claim.valid_to);
  const qualifiers = claim.qualifiers;
  const position = [qualifiers.section, qualifiers.page_number ? `p.${qualifiers.page_number}` : null]
    .filter(Boolean)
    .join(" · ");
  const rawValues = Object.entries(qualifiers).filter(
    ([key, value]) => !HIDDEN_QUALIFIERS.has(key) && typeof value === "string" && value !== "" && value.length <= 120,
  );
  const contract = qualifiers.source_contract;
  const scopeNote = qualifiers.semantic_scope ? SCOPE_NOTES[qualifiers.semantic_scope] ?? qualifiers.semantic_scope : null;
  const processing = contract ? [CONTRACT_NOTES[contract] ?? contract, scopeNote].filter(Boolean).join(" · ") : null;
  const limits = [
    qualifiers.event_semantics === "OFFICIAL_PLAN_LISTING_NOT_COMPLETED_AUDIT"
      ? "공식 계획서상 일정 목록이며 감사가 실제로 열렸다는 기록이 아닙니다."
      : null,
    "출처가 말한 범위까지만 표시합니다.",
  ].filter((item): item is string => item !== null);
  const firstSource = sources[0];

  return (
    <article className={`claim evidence-panel${className ? ` ${className}` : ""}`} id={`claim-${claim.id}`}>
      {kind && <span className="claim-kind">{kind}</span>}
      <p className="claim-title">{title ?? claim.proposition}</p>
      {children}
      {claim.resolution_note && <p className="resolution">{claim.resolution_note}</p>}
      <details className="evidence-disclosure">
        <summary>
          <span className="evidence-summary-line">
            <span className={`status ${claim.epistemic_status}`}>{claim.epistemic_status}</span>
            {claim.publication_status !== "PUBLISHED" && (
              <span className="status UNKNOWN">{claim.publication_status}</span>
            )}
            {conflict && <span className="status CONFLICT">SOURCE CONFLICT</span>}
            <span className="evidence-asof">기준 {asOf ?? "기준일 미기재"}</span>
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
                <span className={`status ${claim.epistemic_status}`}>{claim.epistemic_status}</span>
                <span className="evidence-plain">공개 상태 {claim.publication_status}</span>
                {conflict && <span className="status CONFLICT">SOURCE CONFLICT</span>}
              </span>
              {conflict && (
                <small>서로 다른 근거가 상충하며 자동으로 어느 한쪽을 진실로 판정하지 않습니다.</small>
              )}
            </dd>
          </div>
          <div>
            <dt>유효 기간</dt>
            <dd>{asOf ?? "시작일 미기재"} – {validTo ?? "종료일 없음"}</dd>
          </div>
          <div>
            <dt>기록 시각</dt>
            <dd>
              {formatDateTime(claim.recorded_at) ?? "미기재"}
              <small>Civic Intel이 이 기록을 저장한 시각이며 현실 세계의 사건 시각이 아닙니다.</small>
            </dd>
          </div>
          <div>
            <dt>근거</dt>
            <dd>
              {claim.evidence.length === 0 ? "연결된 Evidence가 없습니다." : (
                <ul className="evidence-rows">
                  {claim.evidence.map((item) => {
                    const source = sourceById.get(item.source_id);
                    return (
                      <li key={item.id}>
                        <span className={`status ${item.stance}`}>{item.stance}</span>
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
                    <li key={key}><span>{QUALIFIER_LABELS[key] ?? key}</span> {value}</li>
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
          <summary>감사 ID</summary>
          <small>
            Claim {claim.id}<br />
            {claim.person_id && <>Person {claim.person_id}<br /></>}
            {claim.organization_id && <>Organization {claim.organization_id}<br /></>}
            {claim.evidence.map((item) => (
              <span key={item.id}>
                Evidence {item.id}<br />
                {item.snapshot_id && <>SourceSnapshot {item.snapshot_id}<br /></>}
                {item.feeder_observation_id && <>FeederObservation {item.feeder_observation_id}<br /></>}
              </span>
            ))}
            {sourceIds.map((id) => <span key={id}>Source {id}<br /></span>)}
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
            <span className={`status ${trace.stance}`}>{trace.stance}</span>
            {source ? <a href={`#source-${source.id}`}>{source.title}</a> : <span>출처 정보를 불러오지 못했습니다</span>}
            <details className="audit-details">
              <summary>감사 ID</summary>
              <small>
                Evidence {trace.id}<br />
                {claimLabel && <>Claim {claimLabel}<br /></>}
                Source {trace.source_id}<br />
                {trace.snapshot_id && <>SourceSnapshot {trace.snapshot_id}<br /></>}
                {trace.feeder_observation_id && <>FeederObservation {trace.feeder_observation_id}</>}
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
        {source.publisher} <span>·</span> {source.published_at ? `공개일 ${formatDay(source.published_at)}` : "공개일 미기재"} <span>·</span> {source.source_class}
      </p>
      <p className="source-license">License: {source.license ?? "License not specified"}</p>
      <p className="source-license">출처 정책 {policyText(source)}</p>
      <p className="source-license">확인 시각 {formatDateTime(source.terms_checked_at) ?? "미기재"}</p>
      <details className="audit-details">
        <summary>감사 ID</summary>
        <small>Source {source.id}<br />URL {source.url}</small>
      </details>
    </article>
  );
}

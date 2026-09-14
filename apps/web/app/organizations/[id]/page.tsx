import Link from "next/link";
import { notFound } from "next/navigation";

import { getOrganization, getOrganizationMoney, getSource } from "../../data";
import ReadState from "../../components/read-state";
import type { Claim, Evidence, MoneyProjection, Source } from "../../types";

export const dynamic = "force-dynamic";

function formatKrw(value: number): string {
  return `${new Intl.NumberFormat("ko-KR").format(value)}원`;
}

function formatThousandKrw(value: number): string {
  return `${new Intl.NumberFormat("ko-KR").format(value)}천원`;
}

function EvidenceTrace({
  evidence,
  sourceById,
  claimId,
}: {
  evidence: Evidence[];
  sourceById: Map<string, Source>;
  claimId?: string;
}) {
  if (evidence.length === 0) return null;

  return (
    <div className="evidence-list">
      <div className="evidence-list-heading">
        <strong>Evidence trace</strong>
        <span>{evidence.length} trace{evidence.length === 1 ? "" : "s"}</span>
      </div>
      {evidence.map((item) => {
        const source = sourceById.get(item.source_id);
        return (
          <div className="evidence-trace" key={item.id}>
            <span className={`status ${item.stance}`}>{item.stance}</span>
            {source ? (
              <Link href={`#source-${source.id}`}>{source.title}</Link>
            ) : (
              <span>Source unavailable</span>
            )}
            <details className="audit-details">
              <summary>Audit trace</summary>
              <small>
                Evidence {item.id}<br />
                Claim {claimId ?? "see linked annual input"}<br />
                Source {item.source_id}<br />
                {item.snapshot_id && <>SourceSnapshot {item.snapshot_id}<br /></>}
                {item.feeder_observation_id && <>FeederObservation {item.feeder_observation_id}</>}
              </small>
            </details>
          </div>
        );
      })}
    </div>
  );
}

function OrganizationClaimCard({
  claim,
  sourceById,
}: {
  claim: Claim;
  sourceById: Map<string, Source>;
}) {
  const fiscalYear = claim.qualifiers.fiscal_year ?? "연도 미기재";

  return (
    <article className="claim organization-claim-card">
      <div className="claim-heading">
        <span className="claim-kind">ORGANIZATION CLAIM</span>
        <span className={`status ${claim.epistemic_status}`}>{claim.epistemic_status}</span>
      </div>
      <div className="organization-claim-meta">
        <span>{fiscalYear} 회계연도</span>
        <span>{claim.publication_status}</span>
      </div>
      <p className="claim-title">{claim.proposition}</p>
      {claim.resolution_note && <p className="resolution">{claim.resolution_note}</p>}
      <EvidenceTrace evidence={claim.evidence} sourceById={sourceById} claimId={claim.id} />
    </article>
  );
}

function MoneyCard({
  money,
  sourceById,
}: {
  money: MoneyProjection;
  sourceById: Map<string, Source>;
}) {
  const { earlier, later } = money.details;
  const delta = money.details.absolute_delta_krw;
  const percent = money.details.percent_change;

  return (
    <article className="money-panel">
      <div className="claim-heading">
        <span className="claim-kind">DERIVED · MONEY</span>
        <span className="status AVAILABLE">AVAILABLE</span>
      </div>
      <h3>기관장 업무추진비 공시액의 회계연도 간 변화</h3>
      <p className="money-scope">
        {money.details.organization.role_scope} · {money.details.organization.code} · Claim-backed read
      </p>
      <div className="money-values" aria-label="Annual disclosed values">
        <div className="money-value">
          <span className="micro-label">EARLIER · {earlier.fiscal_year}</span>
          <strong>{formatThousandKrw(earlier.amount_thousand_krw)}</strong>
          <small>{formatKrw(earlier.amount_krw)} · {earlier.report_period}</small>
        </div>
        <span className="change-arrow" aria-hidden="true">→</span>
        <div className="money-value later">
          <span className="micro-label">LATER · {later.fiscal_year}</span>
          <strong>{formatThousandKrw(later.amount_thousand_krw)}</strong>
          <small>{formatKrw(later.amount_krw)} · {later.report_period}</small>
        </div>
      </div>
      <div className="money-delta-row">
        <div><span>Absolute delta</span><strong>{delta > 0 ? "+" : ""}{formatKrw(delta)}</strong></div>
        <div><span>Percentage</span><strong>{percent === null ? "계산 없음" : `${percent}%`}</strong></div>
      </div>
      <p className="money-note">
        이 카드는 두 개의 published organization Claim을 산술 비교한 파생 읽기 결과입니다.
        특정 개인의 지출, 낭비·부당집행·비리 또는 기관 간 우열을 뜻하지 않습니다.
      </p>
      <EvidenceTrace evidence={money.evidence} sourceById={sourceById} />
      <details className="audit-details">
        <summary>Methodology & coverage</summary>
        <small>
          Method {money.method_version}<br />
          Scope {money.details.input_scope.source_contract}<br />
          Correction semantics {money.details.input_scope.correction_semantics}<br />
          Identity rule {money.details.input_scope.identity_rule}<br />
          Claims {money.claim_ids.join(", ")}<br />
          Snapshots {money.snapshot_ids.join(", ")}<br />
          Observations {money.observation_ids.join(", ")}<br />
          {money.details.limitations.map((item) => <span key={item}>{item}<br /></span>)}
        </small>
      </details>
    </article>
  );
}

function SourceCard({ source }: { source: Source }) {
  return (
    <article className="source" id={`source-${source.id}`}>
      <div className="source-card-topline">
        <span className="micro-label">Source record</span>
        <span className="source-arrow" aria-hidden="true">↗</span>
      </div>
      <h3><a href={source.url} target="_blank" rel="noreferrer">{source.title}</a></h3>
      <p className="source-meta">{source.publisher} <span>·</span> {source.source_class}</p>
      <p className="source-license">License: {source.license ?? "License not specified"}</p>
      <div className="policy-summary">
        <span>Collection {source.policy_summary.collection}</span>
        <span>Metadata {source.policy_summary.metadata_storage}</span>
        <span>Fulltext {source.policy_summary.fulltext_storage}</span>
        <span>Excerpt {source.policy_summary.excerpt_display}</span>
      </div>
      <details className="audit-details">
        <summary>Source audit</summary>
        <small>Source {source.id}<br />URL {source.url}<br />Terms checked {source.terms_checked_at ?? "not recorded"}</small>
      </details>
    </article>
  );
}

export default async function OrganizationPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const [organizationResult, moneyResult] = await Promise.all([
    getOrganization(id),
    getOrganizationMoney(id),
  ]);
  if (organizationResult.state === "error") {
    if (organizationResult.error.code === "PUBLIC_RECORD_NOT_FOUND") notFound();
    return (
      <div className="site-page organization-page">
        <Link href="/" className="back-link"><span aria-hidden="true">←</span> Directory</Link>
        <ReadState error={organizationResult.error} />
      </div>
    );
  }
  const organization = organizationResult.data;
  const money = moneyResult.state === "success" ? moneyResult.data : null;
  const moneySummary = money
    ? "Claim-backed MONEY"
    : moneyResult.state === "error" && moneyResult.error.code === "INSUFFICIENT_ELIGIBLE_INPUTS"
      ? "insufficient eligible inputs"
      : moneyResult.state === "error" && moneyResult.error.code === "SOURCE_VERSION_CONFLICT"
        ? "comparison blocked"
        : "service unavailable";

  const claims = organization.claims ?? [];
  const claimSourceIds = claims.flatMap((claim) => [
    ...claim.source_ids,
    ...claim.evidence.map((item) => item.source_id),
  ]);
  const sourceIds = [...new Set([...claimSourceIds, ...(money?.source_ids ?? [])])];
  const sourceResults = await Promise.all(sourceIds.map(getSource));
  const sources = sourceResults.flatMap((item) => item.state === "success" ? [item.data] : []);
  const sourceError = sourceResults.find((item) => item.state === "error");
  const sourceById = new Map(sources.map((source) => [source.id, source]));

  return (
    <div className="site-page organization-page">
      <Link href="/" className="back-link"><span aria-hidden="true">←</span> Directory</Link>
      <header className="profile-header organization-header">
        <div>
          <div className="eyebrow"><span className="eyebrow-mark" aria-hidden="true">✦</span> Organization record / Published evidence</div>
          <div className="profile-title-row">
            <h1>{organization.name}</h1>
            <span className="status AVAILABLE">AVAILABLE</span>
          </div>
          <p className="profile-lede">현재 canonical organization에 연결된 published Claim과 근거 경로를 읽기 전용으로 표시합니다.</p>
        </div>
        <div className="profile-stamp" aria-hidden="true">
          <span className="micro-label">PUBLIC RECORD</span>
          <strong>ORG</strong>
          <span>evidence / read-only</span>
        </div>
      </header>

      <section className="signal-strip organization-signal-strip" aria-label="Organization record summary">
        <div className="signal-cell signal-primary">
          <span className="micro-label">Published claims</span>
          <strong>{claims.length}</strong>
          <span>current organization Claims</span>
        </div>
        <div className="signal-cell">
          <span className="micro-label">Derived view</span>
          <strong>{money ? "1" : "—"}</strong>
          <span>{moneySummary}</span>
        </div>
        <div className="signal-cell">
          <span className="micro-label">Source trace</span>
          <strong>{sources.length}</strong>
          <span>linked source records</span>
        </div>
      </section>

      <section className="organization-section" id="claims" aria-labelledby="organization-claims-title">
        <div className="section-intro">
          <div><span className="eyebrow">Published claims</span><h2 id="organization-claims-title">공시된 기관 기록</h2></div>
          <p>기관에 대해 현재 공개 가능한 Claim만 표시하며, 각 항목의 Evidence와 Source policy를 함께 제공합니다.</p>
        </div>
        {claims.length === 0 ? (
          <div className="empty-state">
            <span className="empty-state-mark" aria-hidden="true">∅</span>
            <div><strong>Published organization claims are unavailable.</strong><p><span className="status UNKNOWN">UNKNOWN</span> 현재 연결된 공개 Claim이 없습니다.</p></div>
          </div>
        ) : (
          <div className="organization-claim-list">
            {claims.map((claim) => <OrganizationClaimCard key={claim.id} claim={claim} sourceById={sourceById} />)}
          </div>
        )}
      </section>

      <section className="organization-section" id="money" aria-labelledby="organization-money-title">
        <div className="section-intro">
          <div><span className="eyebrow">Derived reading</span><h2 id="organization-money-title">회계연도 간 변화</h2></div>
          <p>두 개의 연간 공시 Claim을 비교한 읽기 전용 결과입니다. 파생 결과 자체는 새로운 Claim이 아닙니다.</p>
        </div>
        {money ? (
          <MoneyCard money={money} sourceById={sourceById} />
        ) : moneyResult.state === "error" ? <ReadState error={moneyResult.error} /> : null}
      </section>

      <section className="source-library organization-source-library" aria-labelledby="organization-sources-title">
        <div className="section-intro">
          <div><span className="eyebrow">Evidence & audit</span><h2 id="organization-sources-title">이 기록의 출처</h2></div>
          <p>출처 제목과 policy 요약은 바로 확인하고, snapshot·observation 식별자는 감사 세부정보에서 확인합니다.</p>
        </div>
        {sourceError?.state === "error" && <ReadState error={sourceError.error} />}
        {sources.length === 0 ? (
          !sourceError && <p className="empty">No source cards available.</p>
        ) : (
          <div className="source-grid">{sources.map((source) => <SourceCard key={source.id} source={source} />)}</div>
        )}
      </section>
    </div>
  );
}

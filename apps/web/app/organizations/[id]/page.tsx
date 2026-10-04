import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import {
  getGukgamCommittees,
  getGukgamTargets,
  getOrganization,
  getOrganizationMoney,
  getOrganizationOntology,
  getSource,
} from "../../data";
import { latestRecordedAt, predicateLabel } from "../../claim-labels";
import CommitteeMembers from "../../components/committee-members";
import EvidencePanel, { EvidenceTraceList, SourceCard } from "../../components/evidence-panel";
import FactBox, { type FactRow } from "../../components/fact-box";
import OntologyLocalGraph from "../../components/ontology-local-graph";
import OpenTargetDetails from "../../components/open-target-details";
import RecordHeader from "../../components/record-header";
import PendingLanes from "../../components/pending-lanes";
import ReadState from "../../components/read-state";
import { committeeHref } from "../../gukgam/2026/committees";
import { formatAuditDate } from "../../gukgam/2026/schedule";
import { buildPageMetadata } from "../../site-metadata";
import type { Claim, MoneyProjection, Source } from "../../types";

const ALIO_EXECUTIVE_PREDICATE = "ALIO_CURRENT_EXECUTIVE_DISCLOSURE";
const ALIO_CLASSIFICATION_PREDICATE = "ALIO_INSTITUTION_CLASSIFICATION";
const GUKGAM_TARGET_PREDICATE = "LISTED_AS_GUKGAM_AUDIT_TARGET";

export const dynamic = "force-dynamic";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ id: string }>;
}): Promise<Metadata> {
  const { id } = await params;
  const result = await getOrganization(id);
  if (result.state === "error") {
    return buildPageMetadata({
      title: "Organization record",
      description: "Civic Intel 공개 기관 기록",
      path: `/organizations/${id}`,
    });
  }
  return buildPageMetadata({
    title: result.data.name,
    description: `${result.data.name}의 공개 기관 기록, 임원 공시, Claim과 Evidence를 확인합니다.`,
    path: `/organizations/${id}`,
  });
}

function formatKrw(value: number): string {
  return `${new Intl.NumberFormat("ko-KR").format(value)}원`;
}

function formatThousandKrw(value: number): string {
  return `${new Intl.NumberFormat("ko-KR").format(value)}천원`;
}

function OrganizationClaim({
  claim,
  sourceById,
}: {
  claim: Claim;
  sourceById: Map<string, Source>;
}) {
  const fiscalYear = claim.qualifiers.fiscal_year;
  return (
    <EvidencePanel claim={claim} sourceById={sourceById} kind="ORGANIZATION CLAIM" className="organization-claim-card">
      {fiscalYear && <div className="organization-claim-meta"><span>{fiscalYear} 회계연도</span></div>}
    </EvidencePanel>
  );
}

function ExecutiveDisclosure({
  claim,
  sourceById,
}: {
  claim: Claim;
  sourceById: Map<string, Source>;
}) {
  const qualifiers = claim.qualifiers;
  return (
    <EvidencePanel
      claim={claim}
      sourceById={sourceById}
      kind="ALIO CURRENT EXECUTIVE"
      title={qualifiers.canonical_name || "공개 이름 없음"}
      className="organization-claim-card executive-disclosure-card"
    >
      <p className="executive-title">{qualifiers.title || "직책 정보 없음"}</p>
      <div className="organization-claim-meta">
        <span>{qualifiers.position_text || "직위 정보 없음"}</span>
        <span>{qualifiers.executive_kind || "역할 범주 정보 없음"}</span>
        <span>기준일 {qualifiers.as_of || "정보 없음"}</span>
      </div>
      <dl className="executive-facts">
        <div><dt>임기</dt><dd>{qualifiers.term_start || "시작일 정보 없음"} — {qualifiers.term_end || "종료일 정보 없음"}</dd></div>
        <div><dt>공시번호</dt><dd>{qualifiers.disclosure_no}</dd></div>
      </dl>
    </EvidencePanel>
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
      <EvidenceTraceList traces={money.evidence} sourceById={sourceById} claimLabel="연결된 연간 입력 참조" />
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

export default async function OrganizationPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const [organizationResult, moneyResult, ontologyResult, targetsResult, committeesResult] = await Promise.all([
    getOrganization(id),
    getOrganizationMoney(id),
    getOrganizationOntology(id),
    getGukgamTargets(),
    getGukgamCommittees(),
  ]);
  if (organizationResult.state === "error") {
    if (organizationResult.error.code === "PUBLIC_RECORD_NOT_FOUND") notFound();
    return (
      <div className="site-page organization-page">
        <Link href="/organizations" className="back-link"><span aria-hidden="true">←</span> Organizations</Link>
        <ReadState error={organizationResult.error} />
      </div>
    );
  }
  const organization = organizationResult.data;
  const money = moneyResult.state === "success" ? moneyResult.data : null;
  const ontology = ontologyResult.state === "success" ? ontologyResult.data : null;
  const moneyInsufficient = moneyResult.state === "error" && moneyResult.error.code === "INSUFFICIENT_ELIGIBLE_INPUTS";

  const gukgamItems = targetsResult.state === "success"
    ? targetsResult.data.items
        .filter((item) => item.organization.id === organization.id)
        .sort((left, right) => left.audit_date.localeCompare(right.audit_date) || left.claim_id.localeCompare(right.claim_id))
    : [];
  const gukgamCommitteeNames = [...new Set(gukgamItems.map((item) => item.committee_name))];
  const committeeByName = new Map(
    (committeesResult.state === "success" ? committeesResult.data.committees : []).map((committee) => [
      committee.committee_name,
      committee,
    ]),
  );
  const gukgamReadError = targetsResult.state === "error" ? targetsResult.error : null;
  const hasGukgam = gukgamItems.length > 0 || gukgamReadError !== null;

  const claims = organization.claims ?? [];
  const publishedClaims = claims.filter((claim) => claim.publication_status === "PUBLISHED");
  const executiveClaims = claims.filter((claim) => claim.predicate === ALIO_EXECUTIVE_PREDICATE);
  const recordClaims = claims.filter((claim) => claim.predicate !== ALIO_EXECUTIVE_PREDICATE);
  const classificationClaim = claims.find((claim) => claim.predicate === ALIO_CLASSIFICATION_PREDICATE);
  const gukgamClaims = claims
    .filter((claim) => claim.predicate === GUKGAM_TARGET_PREDICATE)
    .sort((left, right) => (left.qualifiers.audit_date ?? "").localeCompare(right.qualifiers.audit_date ?? ""));

  const factRows: FactRow[] = [
    ...(classificationClaim
      ? [{ key: classificationClaim.id, label: predicateLabel(ALIO_CLASSIFICATION_PREDICATE), value: classificationClaim.object_text, claim: classificationClaim }]
      : []),
    ...(executiveClaims.length > 0
      ? [{ key: "executive-count", label: predicateLabel(ALIO_EXECUTIVE_PREDICATE), value: `${executiveClaims.length}건`, derived: { href: "#executives" } }]
      : []),
    ...gukgamClaims.map((claim) => {
      const { audit_date: auditDate, committee_name: committeeName, time_text: timeText } = claim.qualifiers;
      return {
        key: claim.id,
        label: predicateLabel(GUKGAM_TARGET_PREDICATE),
        value: auditDate
          ? `${formatAuditDate(auditDate)} · ${committeeName ?? "위원회 미기재"}${timeText ? ` · ${timeText}` : ""}`
          : claim.object_text,
        claim,
      };
    }),
  ];

  const pendingLanes = [
    ...(executiveClaims.length === 0 ? ["현재 임원현황"] : []),
    ...(ontologyResult.state === "success" && ontology && ontology.edges.length === 0 ? ["임원 연결"] : []),
    ...(moneyInsufficient ? ["회계연도 간 변화"] : []),
  ];
  const showConnections = ontologyResult.state === "error" || (ontology !== null && ontology.edges.length > 0);
  const showMoney = money !== null || (moneyResult.state === "error" && !moneyInsufficient);

  const claimSourceIds = claims.flatMap((claim) => [
    ...claim.source_ids,
    ...claim.evidence.map((item) => item.source_id),
  ]);
  const ontologySourceIds = ontology?.edges.flatMap((edge) => edge.source_ids) ?? [];
  const sourceIds = [
    ...new Set([
      ...claimSourceIds,
      ...ontologySourceIds,
      ...(money?.source_ids ?? []),
    ]),
  ];
  const sourceResults = await Promise.all(sourceIds.map(getSource));
  const sources = sourceResults.flatMap((item) => item.state === "success" ? [item.data] : []);
  const sourceError = sourceResults.find((item) => item.state === "error");
  const sourceById = new Map(sources.map((source) => [source.id, source]));
  const sourceTitleById = Object.fromEntries(
    sources.map((source) => [source.id, source.title]),
  );

  return (
    <div className="site-page organization-page">
      <Link href="/organizations" className="back-link"><span aria-hidden="true">←</span> Organizations</Link>
      <RecordHeader
        kind="기관 기록"
        name={organization.name}
        status={<span className="status AVAILABLE">AVAILABLE</span>}
        lede="이 기관에 대해 공개된 Claim과 근거만 모았습니다. 각 항목의 근거에서 출처와 기준일을 확인할 수 있습니다."
        claimCount={publishedClaims.length}
        sourceCount={sources.length}
        recordedAt={latestRecordedAt(publishedClaims)}
      />

      <OpenTargetDetails />
      <div className="profile-layout">
        <aside className="profile-index" aria-label="이 페이지">
          <div className="index-heading"><span className="micro-label">이 페이지</span></div>
          <nav>
            <ul className="page-anchors">
              <li><a href="#key-facts">핵심 기록</a></li>
              {hasGukgam && <li><a href="#gukgam-2026">국정감사</a></li>}
              <li><a href="#records">기록</a></li>
              {showConnections && <li><a href="#official-connections">연결</a></li>}
              <li><a href="#sources">출처</a></li>
            </ul>
          </nav>
        </aside>

        <div className="profile-content">
          <section className="organization-section" id="key-facts" aria-labelledby="organization-overview-title">
            <div className="section-intro">
              <div><span className="eyebrow">Published claims</span><h2 id="organization-overview-title">핵심 기록</h2></div>
              <p>기관 분류와 국정감사 일정은 공개된 기관 Claim에서만 가져오며, 임원 공시 건수는 그 Claim을 센 집계입니다.</p>
            </div>
            {factRows.length > 0 ? <FactBox rows={factRows} /> : (
              <p className="empty"><span className="status UNKNOWN">UNKNOWN</span> 표시할 공개 Claim이 아직 없습니다.</p>
            )}
          </section>

          {hasGukgam && (
            <section className="organization-section" id="gukgam-2026" aria-labelledby="organization-gukgam-title">
              <div className="section-intro">
                <div><span className="eyebrow">Gukgam 2026 / Claim-backed</span><h2 id="organization-gukgam-title">2026 국정감사</h2></div>
                <p>공식 위원회 계획서에 피감대상으로 기재된 일정과, 그 위원회에 기재된 국회 명부상 위원을 보여줍니다.</p>
              </div>
              {gukgamReadError ? (
                <ReadState error={gukgamReadError} />
              ) : (
                <>
                  <ul className="organization-gukgam-rows">
                    {gukgamItems.map((item) => (
                      <li key={item.claim_id}>
                        <strong>{formatAuditDate(item.audit_date)}</strong>
                        <span>
                          <Link href={committeeHref(item.committee_name)}>{item.committee_name}</Link>
                          {item.time_text ? ` · ${item.time_text}` : ""}
                          {item.venue ? ` · ${item.venue}` : ""}
                        </span>
                        <span className="status FACT" title="공식 계획서상 피감대상이라는 계획 사실">FACT</span>
                        <Link className="inline-action" href={`#claim-${item.claim_id}`}>Claim / Evidence <span aria-hidden="true">↓</span></Link>
                      </li>
                    ))}
                  </ul>
                  <p className="gukgam-scope-note">
                    계획서상 일정이며 감사가 실제로 열렸거나 결과가 나왔다는 기록이 아닙니다.
                    위원은 국회 명부 기준이며 이 기관을 질의했다는 뜻이 아닙니다.
                  </p>
                  {gukgamCommitteeNames.map((name) => {
                    const committee = committeeByName.get(name);
                    return committee ? (
                      <div className="organization-gukgam-committee" key={name}>
                        <h3>{name}</h3>
                        <CommitteeMembers committee={committee} />
                      </div>
                    ) : committeesResult.state === "error" ? (
                      <ReadState key={name} error={committeesResult.error} />
                    ) : null;
                  })}
                  {executiveClaims.length > 0 && (
                    <p className="gukgam-scope-note">
                      이 기관의 임원은 <Link href="#executives">현재 임원현황</Link>의 공시상 이름이며,
                      위 위원 인물과 자동으로 연결하지 않습니다.
                    </p>
                  )}
                </>
              )}
            </section>
          )}

          <section className="organization-section" id="records" aria-labelledby="organization-records-title">
            <div className="section-intro">
              <div><span className="eyebrow">Published claims</span><h2 id="organization-records-title">기록</h2></div>
              <p>기관에 대해 현재 공개 가능한 Claim만 표시하며, 각 항목에서 근거와 출처 정책을 펼쳐 볼 수 있습니다.</p>
            </div>
            <PendingLanes lanes={pendingLanes} />
            {claims.length === 0 && (
              <p className="empty"><span className="status UNKNOWN">UNKNOWN</span> 현재 연결된 공개 Claim이 없습니다.</p>
            )}
            {executiveClaims.length > 0 && (
              <div className="organization-records-block" id="executives">
                <h3>현재 임원현황</h3>
                <p className="records-note">ALIO가 해당 기관에 대해 공개한 직위·성명·직책과 기준일을 표시합니다. 개인 Person으로 자동 연결하지 않습니다.</p>
                <div className="organization-claim-list">
                  {executiveClaims.map((claim) => <ExecutiveDisclosure key={claim.id} claim={claim} sourceById={sourceById} />)}
                </div>
              </div>
            )}
            {recordClaims.length > 0 && (
              <div className="organization-records-block" id="claims">
                <h3>공시된 기관 기록</h3>
                <div className="organization-claim-list">
                  {recordClaims.map((claim) => <OrganizationClaim key={claim.id} claim={claim} sourceById={sourceById} />)}
                </div>
              </div>
            )}
            {showMoney && (
              <div className="organization-records-block" id="money">
                <h3>회계연도 간 변화</h3>
                <p className="records-note">두 개의 연간 공시 Claim을 비교한 읽기 전용 결과입니다. 파생 결과 자체는 새로운 Claim이 아닙니다.</p>
                {money ? (
                  <MoneyCard money={money} sourceById={sourceById} />
                ) : moneyResult.state === "error" ? <ReadState error={moneyResult.error} /> : null}
              </div>
            )}
          </section>

          {showConnections && (
            <section className="organization-section ontology-section" id="official-connections" aria-labelledby="organization-ontology-title">
              <div className="section-intro">
                <div><span className="eyebrow">Governance ontology / local view</span><h2 id="organization-ontology-title">공식 기록상 연결</h2></div>
                <p>ALIO published Claim이 명시한 임원 기록만 기관 중심 local graph로 보여줍니다. 이름은 source-listed record이며 canonical Person으로 자동 연결하지 않습니다.</p>
              </div>
              {ontologyResult.state === "error" ? (
                <ReadState error={ontologyResult.error} />
              ) : ontology ? (
                <OntologyLocalGraph graph={ontology} sourceTitles={sourceTitleById} />
              ) : null}
            </section>
          )}

          <section className="source-library organization-source-library" id="sources" aria-labelledby="organization-sources-title">
            <div className="section-intro">
              <div><span className="eyebrow">Evidence & audit</span><h2 id="organization-sources-title">이 기록의 출처</h2></div>
              <p>출처의 공개일, 확인 시각과 출처 정책 요약을 보여줍니다. 내부 식별자는 감사 ID 안에 둡니다.</p>
            </div>
            {sourceError?.state === "error" && <ReadState error={sourceError.error} />}
            {sources.length === 0 ? (
              !sourceError && <p className="empty">No source cards available.</p>
            ) : (
              <div className="source-grid">{sources.map((source) => <SourceCard key={source.id} source={source} />)}</div>
            )}
          </section>
        </div>
      </div>
    </div>
  );
}

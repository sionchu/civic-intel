import { statusLabel } from "../../display-labels";
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
import CommitteeMembers from "../../components/committee-members";
import SourceLibrary from "../../components/source-library";
import EvidencePanel, { EvidenceTraceList } from "../../components/evidence-panel";
import FactBox, { type FactRow } from "../../components/fact-box";
import OntologyLocalGraph from "../../components/ontology-local-graph";
import OpenTargetDetails from "../../components/open-target-details";
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
      title: "기관 기록",
      description: "모두의국감 공개 기관 기록",
      path: `/organizations/${id}`,
    });
  }
  return buildPageMetadata({
    title: result.data.name,
    description: `${result.data.name}의 공개 기관 기록, 임원 공시, 기록과 근거를 확인합니다.`,
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
    <EvidencePanel claim={claim} sourceById={sourceById} kind="기관 공개 기록" className="organization-claim-card">
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
        <span className="claim-kind">공시 금액 비교</span>
        <span className="status AVAILABLE">{statusLabel("AVAILABLE")}</span>
      </div>
      <h3>기관장 업무추진비 공시액의 회계연도 간 변화</h3>
      <p className="money-scope">
        {money.details.organization.role_scope} · {money.details.organization.code} · 공개 기록 기반
      </p>
      <div className="money-values" aria-label="연도별 공시금액">
        <div className="money-value">
          <span className="micro-label">이전 · {earlier.fiscal_year}</span>
          <strong>{formatThousandKrw(earlier.amount_thousand_krw)}</strong>
          <small>{formatKrw(earlier.amount_krw)} · {earlier.report_period}</small>
        </div>
        <span className="change-arrow" aria-hidden="true">→</span>
        <div className="money-value later">
          <span className="micro-label">이후 · {later.fiscal_year}</span>
          <strong>{formatThousandKrw(later.amount_thousand_krw)}</strong>
          <small>{formatKrw(later.amount_krw)} · {later.report_period}</small>
        </div>
      </div>
      <div className="money-delta-row">
        <div><span>증감액</span><strong>{delta > 0 ? "+" : ""}{formatKrw(delta)}</strong></div>
        <div><span>증감률</span><strong>{percent === null ? "계산 없음" : `${percent}%`}</strong></div>
      </div>
      <p className="money-note">
        이 카드는 공개된 두 해의 기관 기록을 단순 비교한 계산 결과입니다.
        특정 개인의 지출, 낭비·부당집행·비리 또는 기관 간 우열을 뜻하지 않습니다.
      </p>
      <EvidenceTraceList traces={money.evidence} sourceById={sourceById} claimLabel="연결된 연간 입력 참조" />
      <details className="audit-details">
        <summary>계산 방법과 범위</summary>
        <small>
          방법 {money.method_version}<br />
          범위 {money.details.input_scope.source_contract}<br />
          정정 기준 {money.details.input_scope.correction_semantics}<br />
          인물 연결 규칙 {money.details.input_scope.identity_rule}<br />
          기록 {money.claim_ids.join(", ")}<br />
          출처 저장본 {money.snapshot_ids.join(", ")}<br />
          수집 기록 {money.observation_ids.join(", ")}<br />
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
        <Link href="/organizations" className="back-link"><span aria-hidden="true">←</span> 기관 목록</Link>
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
  const executiveClaims = claims.filter((claim) => claim.predicate === ALIO_EXECUTIVE_PREDICATE);
  const recordClaims = claims.filter((claim) => claim.predicate !== ALIO_EXECUTIVE_PREDICATE);
  const classificationClaim = claims.find((claim) => claim.predicate === ALIO_CLASSIFICATION_PREDICATE);
  const gukgamClaims = claims
    .filter((claim) => claim.predicate === GUKGAM_TARGET_PREDICATE)
    .sort((left, right) => (left.qualifiers.audit_date ?? "").localeCompare(right.qualifiers.audit_date ?? ""));

  const factRows: FactRow[] = [
    ...(classificationClaim
      ? [{ key: classificationClaim.id, label: "기관 분류(ALIO)", value: classificationClaim.object_text, claim: classificationClaim }]
      : []),
    ...(executiveClaims.length > 0
      ? [{ key: "executive-count", label: "현재 임원 공시", value: `${executiveClaims.length}건`, derived: { href: "#executives" } }]
      : []),
    ...gukgamClaims.map((claim) => {
      const { audit_date: auditDate, committee_name: committeeName, time_text: timeText } = claim.qualifiers;
      return {
        key: claim.id,
        label: "2026 국정감사 피감대상",
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
      <Link href="/organizations" className="back-link"><span aria-hidden="true">←</span> 기관 목록</Link>
      <header className="profile-header organization-header">
        <div>
          <div className="profile-title-row">
            <h1>{organization.name}</h1>
            <span className="status AVAILABLE">{statusLabel("AVAILABLE")}</span>
          </div>
        </div>
      </header>

      <OpenTargetDetails />
      <div className="profile-layout">
        <aside className="profile-index" aria-label="이 페이지">
          <h2 className="index-heading">이 페이지</h2>
          <nav>
            <ul className="page-anchors">
              {factRows.length > 0 && <li><a href="#key-facts">핵심 기록</a></li>}
              {hasGukgam && <li><a href="#gukgam-2026">국정감사</a></li>}
              <li><a href="#records">기록</a></li>
              {showConnections && <li><a href="#official-connections">연결</a></li>}
              <li><a href="#sources">출처</a></li>
            </ul>
          </nav>
        </aside>

        <div className="profile-content">
          {factRows.length > 0 && <section className="organization-section" id="key-facts" aria-labelledby="organization-overview-title">
            <div className="section-intro">
              <h2 id="organization-overview-title">핵심 기록</h2>
            </div>
            <FactBox rows={factRows} />
          </section>}

          {hasGukgam && (
            <section className="organization-section" id="gukgam-2026" aria-labelledby="organization-gukgam-title">
              <div className="section-intro">
                <h2 id="organization-gukgam-title">2026 국정감사</h2>
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
                        <span className="status FACT" title="공식 계획서상 피감대상이라는 계획 사실">{statusLabel("FACT")}</span>
                        <Link className="inline-action" href={`#claim-${item.claim_id}`}>근거 보기</Link>
                      </li>
                    ))}
                  </ul>
                  <p className="gukgam-scope-note">
                    위원회 계획서상 일정입니다.
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
                </>
              )}
            </section>
          )}

          <section className="organization-section" id="records" aria-labelledby="organization-records-title">
            <div className="section-intro">
              <h2 id="organization-records-title">기록</h2>
            </div>
            {claims.length === 0 && (
              <p className="empty"><span className="status UNKNOWN">{statusLabel("UNKNOWN")}</span> 현재 연결된 공개 기록이 없습니다.</p>
            )}
            {executiveClaims.length > 0 && (
              <div className="organization-records-block" id="executives">
                <h3>현재 임원현황</h3>
                <p className="records-note">ALIO가 해당 기관에 대해 공개한 직위·성명·직책과 기준일을 표시합니다. 등록된 개인으로 자동 연결하지 않습니다.</p>
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
                <p className="records-note">두 해의 공시를 비교한 계산 결과이며, 그 자체로 새로운 기록은 아닙니다.</p>
                {money ? (
                  <MoneyCard money={money} sourceById={sourceById} />
                ) : moneyResult.state === "error" ? <ReadState error={moneyResult.error} /> : null}
              </div>
            )}
            {pendingLanes.length > 0 && <details className="profile-coverage"><summary>자료 범위와 한계</summary><PendingLanes lanes={pendingLanes} /></details>}
          </section>

          {showConnections && (
            <section className="organization-section ontology-section" id="official-connections" aria-labelledby="organization-ontology-title">
              <div className="section-intro">
                <h2 id="organization-ontology-title">공식 기록상 연결</h2>
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
              <h2 id="organization-sources-title">이 기록의 출처</h2>
            </div>
            {sourceError?.state === "error" && <ReadState error={sourceError.error} />}
            {sources.length === 0 ? (
              !sourceError && <p className="empty">표시할 출처가 없습니다.</p>
            ) : (
              <SourceLibrary sources={sources} />
            )}
          </section>
        </div>
      </div>
    </div>
  );
}

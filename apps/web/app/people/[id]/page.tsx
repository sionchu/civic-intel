import { entryKindLabel, statusLabel } from "../../display-labels";
import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { getGukgamCommittees, getGukgamTargets, getPerson, getPersonOntology, getPersonRelationships, getSource } from "../../data";
import { careerAttribution, careerPeriodText } from "../../career-period";
import PersonEvidenceProvider from "../../components/person-evidence-context";
import PersonClaimLibrary from "../../components/person-claim-library";
import SourceLibrary from "../../components/source-library";
import EvidencePanel, { EvidenceTraceList } from "../../components/evidence-panel";
import FactBox, { type FactRow } from "../../components/fact-box";
import OntologyLocalGraph from "../../components/ontology-local-graph";
import OpenTargetDetails from "../../components/open-target-details";
import PendingLanes from "../../components/pending-lanes";
import PersonRelationshipsView from "../../components/person-relationships";
import PersonVoteExplorer from "../../components/person-vote-explorer";
import ReadState from "../../components/read-state";
import { committeeHref } from "../../gukgam/2026/committees";
import { formatAuditDate } from "../../gukgam/2026/schedule";
import { getReviewedPortrait } from "../../portrait";
import { predicateLabel } from "../../predicate-labels";
import { officialVoteRecords, recentOfficialActivity, supportingActivityEvidence } from "../../person-activity";
import { buildPageMetadata } from "../../site-metadata";
import type { Claim, ProfileEntry, ProfileSectionReason } from "../../types";

export const dynamic = "force-dynamic";


const FACT_PREDICATES: [string, string][] = [
  ["HELD_ROLE", "직위"],
  ["ASSEMBLY_PARTY", "정당"],
  ["ASSEMBLY_DISTRICT", "지역구"],
  ["ASSEMBLY_COMMITTEES", "소속 위원회"],
  ["ASSEMBLY_COMMITTEE_ROLE", "위원회 직책"],
  ["ASSEMBLY_REELECTION", "선수"],
  ["ALIO_REVIEWED_PERSON_ROLE", "공공기관 임원 공시"],
  ["OPENDART_DISCLOSED_EXECUTIVE_ROLE", "기업 임원 공시"],
];

// Person Claims linked to one exact source row after human identity review.
const LINKED_WITNESS_PREDICATE = "LISTED_AS_GUKGAM_WITNESS";

const EMPTY_LANE_REASONS: { reason: ProfileSectionReason; title: string; detail: string }[] = [
  {
    reason: "SOURCE_NOT_COLLECTED",
    title: "공식 출처 미수집",
    detail: "이 항목의 공식 자료가 아직 수집되지 않았습니다. 실제 기록이 없다는 뜻은 아닙니다.",
  },
  {
    reason: "INSUFFICIENT_EVIDENCE",
    title: "비교·분석할 근거 부족",
    detail: "공개된 근거가 비교나 분석의 최소 조건에 못 미쳐 결과를 만들지 않았습니다.",
  },
  {
    reason: "DERIVATION_NOT_AVAILABLE",
    title: "검토된 분석 결과 없음",
    detail: "이 항목에 연결된 공개 분석 결과가 없습니다.",
  },
  {
    reason: "NOT_APPLICABLE",
    title: "해당 없음",
    detail: "공개된 기록상 이 인물에게 적용되지 않는 항목입니다.",
  },
];

export async function generateMetadata({
  params,
}: {
  params: Promise<{ id: string }>;
}): Promise<Metadata> {
  const { id } = await params;
  const result = await getPerson(id);
  if (result.state === "error") {
    return buildPageMetadata({
      title: "인물 기록",
      description: "모두의국감 공개 인물 기록",
      path: `/people/${id}`,
    });
  }
  return buildPageMetadata({
    title: result.data.canonical_name,
    description: `${result.data.canonical_name}의 공개 기록, 근거와 출처를 확인합니다.`,
    path: `/people/${id}`,
  });
}

export default async function PersonPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const personResult = await getPerson(id);
  if (personResult.state === "error") {
    if (personResult.error.code === "PUBLIC_RECORD_NOT_FOUND") notFound();
    return (
      <div className="site-page profile-page">
        <Link href="/people" className="back-link"><span aria-hidden="true">←</span> 인물 찾기</Link>
        <ReadState error={personResult.error} />
      </div>
    );
  }
  const person = personResult.data;
  const [portrait, ontologyResult, relationshipsResult, committeesResult, targetsResult] = await Promise.all([
    getReviewedPortrait(person),
    getPersonOntology(id),
    getPersonRelationships(id),
    getGukgamCommittees(),
    getGukgamTargets(),
  ]);
  const gukgamCommittees = committeesResult.state === "success"
    ? committeesResult.data.committees.map((committee) => committee.committee_name)
    : [];
  const ontology = ontologyResult.state === "success" ? ontologyResult.data : null;
  const relationships = relationshipsResult.state === "success" ? relationshipsResult.data : null;

  const sectionSourceIds =
    person.profile?.sections.flatMap((section) =>
      section.entries.flatMap((entry) => entry.source_ids),
    ) ?? [];
  const claimSourceIds = (person.claims ?? []).flatMap((claim) => claim.source_ids);
  const ontologySourceIds = ontology?.edges.flatMap((edge) => edge.source_ids) ?? [];
  const relationshipSourceIds = relationships?.groups.flatMap((group) => group.relations.flatMap((relation) => relation.source_ids)) ?? [];
  const sourceIds = [...new Set([...sectionSourceIds, ...claimSourceIds, ...ontologySourceIds, ...relationshipSourceIds])];
  const sourceResults = await Promise.all(sourceIds.map(getSource));
  const sources = sourceResults.flatMap((item) => item.state === "success" ? [item.data] : []);
  const sourceError = sourceResults.find((item) => item.state === "error");
  const sourceById = new Map(sources.map((source) => [source.id, source]));
  const sourceTitleById = Object.fromEntries(sources.map((source) => [source.id, source.title]));
  const profile = person.profile;
  const claims = person.claims ?? [];
  const claimById = new Map(claims.map((claim) => [claim.id, claim]));
  const publishedClaims = claims.filter((claim) => claim.publication_status === "PUBLISHED");
  const recentActivity = recentOfficialActivity(person, claims);
  const votes = officialVoteRecords(person, claims);
  const factRows: FactRow[] = [
    ...FACT_PREDICATES.flatMap(([predicate, label]) =>
      publishedClaims.filter((claim) => claim.predicate === predicate).map((claim) => ({
        key: claim.id, label, value: claim.object_text, claim,
      })),
    ),
  ];
  const career = profile?.sections.find((section) => section.id === "career_timeline");
  const limitations = profile?.sections.find((section) => section.id === "limitations");
  const declaredAssets = profile?.sections.find((section) => section.id === "public_declared_assets");
  const representedClaims = new Set(profile?.sections.flatMap((section) => section.entries.flatMap((entry) => entry.claim_id ? [entry.claim_id] : [])) ?? []);
  const voteIds = new Set(votes.map((record) => record.claimId));
  const staticClaimIds = profile?.sections.filter((section) => section.id !== "legislative_activity").flatMap((section) => section.entries.flatMap((entry) => entry.claim_id ? [entry.claim_id] : [])) ?? [];
  const otherClaims = publishedClaims.filter((claim) => !representedClaims.has(claim.id) && !voteIds.has(claim.id));

  const memberCommittees = committeesResult.state === "success"
    ? committeesResult.data.committees.flatMap((committee) => {
        const member = committee.members.find((item) => item.person.id === person.id);
        return member ? [{ committee, member }] : [];
      })
    : [];
  const targetItems = targetsResult.state === "success" ? targetsResult.data.items : [];
  const witnessListings = publishedClaims.filter((claim) => claim.predicate === LINKED_WITNESS_PREDICATE);
  const hasGukgam = memberCommittees.length > 0 || witnessListings.length > 0;
  // Empty sections grouped by the projection's reason, so a missing source, too little evidence for
  // a comparison, an unreviewed analysis and a lane that does not apply are not read as one gap.
  const emptyLaneGroups = EMPTY_LANE_REASONS.map((group) => ({
    ...group,
    lanes: (profile?.sections ?? [])
      .filter((section) => section.entries.length === 0 && section.reason === group.reason)
      .map((section) => section.label),
  })).filter((group) => group.lanes.length > 0);

  const isPlenaryVote = (entry: ProfileEntry) =>
    entry.kind === "DECISION_EPISODE" && entry.details.action === "PLENARY_ROLL_CALL_VOTE";

  const renderedClaimIds = new Set<string>();
  const renderEntry = (entry: ProfileEntry) => {
    const claim: Claim | undefined = entry.claim_id ? claimById.get(entry.claim_id) : undefined;
    const claimAnchor = !entry.claim_id || !renderedClaimIds.has(entry.claim_id);
    if (entry.claim_id) renderedClaimIds.add(entry.claim_id);
    const changeDetails = entry.kind === "CHANGE" ? entry.details as {
      method_version?: string;
      derived_reason?: string;
      earlier?: { claim_id?: string; date?: string; predicate?: string; role_text?: string };
      later?: { claim_id?: string; date?: string; predicate?: string; role_text?: string };
      input_scope?: { correction_semantics?: string; provider_record_identity?: string };
      coverage?: { eligible_claim_count?: number; comparison?: string };
      limitations?: string[];
    } : null;
    const isLegislativeActivity = !changeDetails && entry.details.predicate === "ASSEMBLY_BILL_PARTICIPATION";
    const activityRole = isLegislativeActivity && typeof entry.details.participation_role === "string"
      ? entry.details.participation_role === "REPRESENTATIVE_PROPOSER" ? "대표 발의" : "공동 발의"
      : null;
    const activityTitle = isLegislativeActivity && typeof entry.details.object_text === "string"
      ? entry.details.object_text
      : null;

    if (changeDetails) {
      return (
        <article className="claim change-card" key={entry.id}>
          <div className="claim-heading">
            <span className="claim-kind">공개 기록의 변화</span>
            {entry.epistemic_status && <span className={`status ${entry.epistemic_status}`}>{statusLabel(entry.epistemic_status)}</span>}
          </div>
          <p className="claim-title">{entry.title}</p>
          <div className="change-sequence" aria-label="날짜별 기록 비교">
            <div className="change-point">
              <span className="micro-label">이전 · {changeDetails.earlier?.date ?? "미확인"}</span>
              <strong>{changeDetails.earlier?.role_text ?? "표시값 없음"}</strong>
              <small>{predicateLabel(changeDetails.earlier?.predicate ?? "")} · {changeDetails.earlier?.claim_id ? <a href={`#claim-${changeDetails.earlier.claim_id}`}>근거 기록 열기</a> : "근거 미확인"}</small>
            </div>
            <span className="change-arrow" aria-hidden="true">→</span>
            <div className="change-point later">
              <span className="micro-label">이후 · {changeDetails.later?.date ?? "미확인"}</span>
              <strong>{changeDetails.later?.role_text ?? "표시값 없음"}</strong>
              <small>{predicateLabel(changeDetails.later?.predicate ?? "")} · {changeDetails.later?.claim_id ? <a href={`#claim-${changeDetails.later.claim_id}`}>근거 기록 열기</a> : "근거 미확인"}</small>
            </div>
          </div>
          {changeDetails.derived_reason && <p className="change-reason">{changeDetails.derived_reason}</p>}
          <details className="audit-details">
            <summary>계산 방법과 범위</summary>
            <small>
              이전 기록 식별자 {changeDetails.earlier?.claim_id ?? "미확인"}<br />
              이후 기록 식별자 {changeDetails.later?.claim_id ?? "미확인"}<br />
              방법 식별자 {changeDetails.method_version ?? "미확인"}<br />
              범위 {changeDetails.input_scope?.provider_record_identity ?? "미확인"}<br />
              정정 기준 {changeDetails.input_scope?.correction_semantics ?? "미확인"}<br />
              비교 가능한 기록 {changeDetails.coverage?.eligible_claim_count ?? "미확인"}<br />
              {changeDetails.coverage?.comparison ?? "비교 기준 미기재"}<br />
              {(changeDetails.limitations ?? []).map((item) => <span key={item}>{item}<br /></span>)}
            </small>
          </details>
          {entry.evidence && <EvidenceTraceList traces={entry.evidence} sourceById={sourceById} />}
        </article>
      );
    }

    // Plenary votes are many short official rows: one compact row each, with the recorded vote,
    // the official bill link and the Claim/Evidence/Source trace one disclosure away.
    if (isPlenaryVote(entry)) {
      const trace = entry.evidence?.[0];
      const source = trace ? sourceById.get(trace.source_id) : undefined;
      return (
        <li className="vote-row" key={entry.id} id={claimAnchor ? `claim-${entry.claim_id}` : undefined}>
          <span className="vote-date">{entry.date ?? "날짜 미기재"}</span>
          <span className="vote-bill">
            {typeof entry.details.detail_url === "string"
              ? <a href={entry.details.detail_url} target="_blank" rel="noreferrer">{String(entry.details.target)}</a>
              : String(entry.details.target)}
          </span>
          <span className="status AVAILABLE vote-value">{String(entry.details.outcome)}</span>
          <details className="audit-details vote-trace evidence-disclosure">
            <summary>근거</summary>
            <small>
              {source ? <a href={`#source-${source.id}`}>{source.title}</a> : "출처"} · {statusLabel(entry.epistemic_status)}<br />
              기록 {entry.claim_id}<br />
              근거 {trace?.id ?? "없음"}<br />
              출처 저장본 {trace?.snapshot_id ?? "없음"}<br />
              수집 기록 {trace?.feeder_observation_id ?? "없음"}
            </small>
          </details>
        </li>
      );
    }

    if (claim) {
      const housingDetails = claim.predicate === "PETI_DECLARED_SELF_HOUSING" && entry.details.source_contract === "peti_public_self_housing_metadata_v1" && entry.details.value_semantics === "DECLARED_OWNERSHIP_NOT_RESIDENCE" ? entry.details : null;
      const pressDetails = claim.predicate === "ASSEMBLY_OFFICIAL_PRESS_RECORD" && entry.details.source_contract === "national_assembly_press_release_metadata_v1" ? entry.details : null;
      const assetDetails = claim.predicate === "ASSEMBLY_DECLARED_ASSET_TOTAL" ? entry.details : null;
      const assetAmount = assetDetails?.amount_unit === "THOUSAND_KRW" &&
        ["assembly_asset_gazette_reviewed_packet_v1", "peti_public_declared_total_metadata_v1"].includes(String(assetDetails.source_contract)) &&
        assetDetails.value_semantics === "DECLARED_VALUE_NOT_MARKET_WEALTH" &&
        typeof assetDetails.amount_thousand_krw === "number" && Number.isSafeInteger(assetDetails.amount_thousand_krw)
        ? assetDetails.amount_thousand_krw : null;
      return (
        <EvidencePanel
          key={entry.id}
          claim={claim}
          sourceById={sourceById}
          title={isLegislativeActivity ? activityTitle ?? entry.title : entry.title}
          kind={housingDetails ? "본인 소유 주택 신고" : pressDetails ? "국회 공식 보도자료" : assetDetails ? "신고재산" : isLegislativeActivity ? "공식 법안 기록" : entryKindLabel(entry.kind)}
          sourceConflict={entry.source_conflict}
          dateLabel={assetDetails || housingDetails || pressDetails || entry.details.career_semantics ? "기록 기준" : undefined}
          claimAnchor={claimAnchor}
        >
          {housingDetails && <>
            <dl className="activity-facts">
              <div><dt>신고 상태</dt><dd>{statusLabel(String(housingDetails.housing_status))}</dd></div>
              <div><dt>소유 주택 건수</dt><dd>{housingDetails.housing_status === "UNKNOWN" ? "미확인" : String(housingDetails.owned_housing_count ?? "미확인")}</dd></div>
              <div><dt>그중 공동 소유</dt><dd>{housingDetails.housing_status === "UNKNOWN" ? "미확인" : String(housingDetails.shared_housing_count ?? "미확인")}</dd></div>
              <div><dt>확인 범위</dt><dd>{statusLabel(String(housingDetails.self_scope_coverage))}</dd></div>
              <div><dt>공개일</dt><dd>{String(housingDetails.publication_date ?? "미기재")}</dd></div>
              <div><dt>등록일</dt><dd>{String(housingDetails.registration_date ?? "미기재")}</dd></div>
            </dl>
            <p className="section-note">공개 신고의 본인 소유 주택 기록입니다. 현재 거주지나 실거주 여부를 뜻하지 않습니다.</p>
          </>}
          {pressDetails && <>
            <dl className="activity-facts">
              <div><dt>게시일</dt><dd>{String(pressDetails.written_date ?? "미기재")}</dd></div>
              <div><dt>발행기관</dt><dd>{String(pressDetails.attribution ?? "미기재")}</dd></div>
              <div><dt>확인 범위</dt><dd>{statusLabel(String(pressDetails.coverage))}</dd></div>
            </dl>
            <p className="section-note">국회 공식 보도자료의 제목과 게시 정보입니다. 개인의 직접 발언이나 언론기사 전체를 뜻하지 않습니다.</p>
          </>}
          {assetDetails && (
            <>
              <dl className="activity-facts">
                <div><dt>공개 신고 총계</dt><dd>{assetAmount === null ? "금액·단위 확인 불가" : `${assetAmount.toLocaleString("ko-KR")}천원`}</dd></div>
                <div><dt>공개일</dt><dd>{typeof assetDetails.publication_date === "string" ? assetDetails.publication_date : "미기재"}</dd></div>
                <div><dt>등록일</dt><dd>{typeof assetDetails.registration_date === "string" ? assetDetails.registration_date : "미기재"}</dd></div>
                <div><dt>신고유형</dt><dd>{typeof assetDetails.report_type === "string" && assetDetails.report_type !== "UNKNOWN" ? assetDetails.report_type : "미확인 · 원자료에서 확인되지 않음"}</dd></div>
                {typeof assetDetails.reporting_period_text === "string" && <div><dt>신고 기준 기간</dt><dd>{assetDetails.reporting_period_text}</dd></div>}
              </dl>
              <p className="section-note">공개 서식에 인쇄된 신고 총계입니다. 본인만의 재산, 현재 시장가치 또는 순자산으로 해석하지 않습니다.</p>
            </>
          )}
          {entry.details.career_semantics ? (
            <p className="person-career-period"><strong>{careerPeriodText(entry.details.career_period)}</strong><span>{careerAttribution(entry.details.career_semantics)}</span></p>
          ) : null}
          {isLegislativeActivity && (
            <>
              <div className="activity-badges"><span className="status AVAILABLE">{activityRole}</span></div>
              <p className="activity-assertion">{entry.title}</p>
              <dl className="activity-facts">
                {typeof entry.details.bill_no === "string" && <div><dt>의안번호</dt><dd>{entry.details.bill_no}</dd></div>}
                {typeof entry.details.committee === "string" && <div><dt>소관 위원회</dt><dd>{entry.details.committee}</dd></div>}
                {typeof entry.details.process_result === "string" && <div><dt>처리 결과</dt><dd>{entry.details.process_result}</dd></div>}
              </dl>
              {typeof entry.details.detail_url === "string" && <a className="activity-link" href={entry.details.detail_url} target="_blank" rel="noreferrer">의안 원문 보기</a>}
            </>
          )}
        </EvidencePanel>
      );
    }

    return (
      <article className="claim" key={entry.id}>
        <div className="claim-heading">
          <span className="claim-kind">{entryKindLabel(entry.kind)}</span>
          {entry.epistemic_status && <span className={`status ${entry.epistemic_status}`}>{statusLabel(entry.epistemic_status)}</span>}
        </div>
        <p className="claim-title">{entry.title}</p>
        {entry.date && <small className="claim-date">기준 {entry.date}</small>}
        {entry.evidence && entry.evidence.length > 0 ? (
          <EvidenceTraceList traces={entry.evidence} sourceById={sourceById} claimLabel={entry.claim_id ?? "해당 없음"} />
        ) : entry.source_ids.length > 0 ? (
          <div className="source-links">
            <strong>출처 참조</strong>
            {entry.source_ids.map((sourceId) => (
              <a href={`#source-${sourceId}`} key={sourceId}>{sourceById.get(sourceId)?.title ?? "출처 기록"}</a>
            ))}
          </div>
        ) : null}
      </article>
    );
  };

  return (
    <PersonEvidenceProvider claims={publishedClaims} sources={sources}>
    <div className="site-page profile-page">
      <Link href="/people" className="back-link"><span aria-hidden="true">←</span> 인물 찾기</Link>
      <header className="profile-header">
        <div>
          <div className="profile-title-row">
            <h1>{person.canonical_name}</h1>
            <span className={`status identity ${person.identity_status}`}>{statusLabel(person.identity_status)}</span>
          </div>
        </div>
        {portrait ? (
          <figure className="profile-portrait">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={portrait.local_path}
              width={portrait.source_width}
              height={portrait.source_height}
              alt={`${person.canonical_name} 공개 사진`}
            />
            <figcaption className="portrait-credit">
              <span>사진: <a href={portrait.source_page_url} target="_blank" rel="noreferrer">{portrait.creator} · {portrait.source_kind === "WIKIMEDIA_COMMONS_REVIEWED" ? "Wikimedia Commons" : "출처"}</a> · <a href={portrait.license_url} target="_blank" rel="noreferrer">{portrait.license}</a></span>
              <details className="audit-details">
                <summary>사진 출처 정보</summary>
                <small>
                  파일 {portrait.file_title}<br />
                  판 {portrait.source_revision_timestamp}<br />
                  SHA-1 {portrait.source_sha1}<br />
                  {portrait.modification_note}
                </small>
              </details>
            </figcaption>
          </figure>
        ) : null}
      </header>

      <OpenTargetDetails />
      <div className="profile-layout">
        <aside className="profile-index" aria-label="이 페이지">
          <h2 className="index-heading">이 페이지</h2>
          <nav>
            <ul className="page-anchors">
              {factRows.length > 0 && <li><a href="#key-facts">핵심 기록</a></li>}
              {career && career.entries.length > 0 && <li><a href="#career">경력</a></li>}
              {recentActivity.items.length > 0 && <li><a href="#recent-activity">최근 공식 활동</a></li>}
              {person.identity_status === "RESOLVED" && <li><a href="#vote-records">법안별 표결 기록</a></li>}
              {declaredAssets && <li><a href="#section-public_declared_assets">신고재산</a></li>}
              {hasGukgam && <li><a href="#gukgam-2026">국정감사</a></li>}
              <li><a href="#records">기록</a></li>
              <li><a href="#official-connections">연결</a></li>
              <li><a href="#sources">출처</a></li>
            </ul>
          </nav>
        </aside>

        <div className="profile-content">
          {factRows.length > 0 && <section className="person-section" id="key-facts" aria-labelledby="key-facts-title">
            <div className="section-intro">
              <h2 id="key-facts-title">핵심 기록</h2>
            </div>
            <FactBox rows={factRows} />
          </section>}

          {career && career.entries.length > 0 && (
            <section className="person-section person-career" id="career" aria-labelledby="career-title">
              <div className="section-intro"><h2 id="career-title">경력 <span className="domain-label" lang="ko">연혁</span></h2><span className={`status ${career.status}`}>{statusLabel(career.status)}</span></div>
              {career.note && <p className="section-note">{career.note}</p>}
              {career.entries.map(renderEntry)}
            </section>
          )}

          {hasGukgam && (
            <section className="person-section" id="gukgam-2026" aria-labelledby="person-gukgam-title">
              <div className="section-intro">
                <h2 id="person-gukgam-title">2026 국정감사</h2>
                {memberCommittees.length === 0 && (
                  <p>위원회 증인·참고인 명단에 기재된 기록입니다. 출석 요구일 뿐 혐의·잘못·출석·증언을 뜻하지 않습니다.</p>
                )}
              </div>
              {witnessListings.map((claim) => (
                <div className="person-gukgam-committee" key={claim.id}>
                  <h3>
                    <Link href={committeeHref(claim.qualifiers.committee_name)}>{claim.qualifiers.committee_name}</Link>{" "}
                    {claim.qualifiers.category}
                  </h3>
                  {claim.qualifiers.provenance_label && (
                    <p className="committee-targets-pending" role="note">{claim.qualifiers.provenance_label}</p>
                  )}
                  <dl className="person-gukgam-facts">
                    <div><dt>명단 기재 소속·직위</dt><dd>{claim.qualifiers.affiliation_title ?? "미기재"}</dd></div>
                    <div>
                      <dt>출석 요구일</dt>
                      <dd>{claim.qualifiers.attendance_date_text ?? claim.qualifiers.attendance_date ?? "명단에 기재 없음"}</dd>
                    </div>
                    <div>
                      <dt>근거</dt>
                      <dd>
                        <a href={`#claim-${claim.id}`}>{claim.qualifiers.source_tag ?? "명단"} · {claim.qualifiers.list_version}</a>
                        {" · "}
                        <Link href={`/gukgam/2026#witness-${claim.qualifiers.source_claim_id}`}>명단에서 보기</Link>
                      </dd>
                    </div>
                  </dl>
                </div>
              ))}
              {targetsResult.state === "error" && <ReadState error={targetsResult.error} />}
              {memberCommittees.map(({ committee, member }) => {
                const items = targetItems.filter((item) => item.committee_name === committee.committee_name);
                const dates = [...new Set(items.map((item) => item.audit_date))].sort();
                const institutions = [...new Map(items.map((item) => [item.organization.id, item.organization])).values()]
                  .sort((left, right) => left.name.localeCompare(right.name, "ko"));
                return (
                  <div className="person-gukgam-committee" key={committee.committee_name}>
                    <h3><Link href={committeeHref(committee.committee_name)}>{committee.committee_name}</Link></h3>
                    {committee.target_claim_coverage === "NOT_YET_PUBLISHED" && (
                      <p className="committee-targets-pending" role="note">
                        피감대상 공개 기록 준비 중 — 위원 명단만 표시
                      </p>
                    )}
                    <dl className="person-gukgam-facts">
                      <div>
                        <dt>감사일</dt>
                        <dd>
                          {dates.length === 0 ? "공개된 일정 없음" : dates.map((date) => (
                            <Link key={date} href={`/gukgam/2026#audit-${date}`}>{formatAuditDate(date)}</Link>
                          ))}
                        </dd>
                      </div>
                      <div>
                        <dt>피감 기관</dt>
                        <dd>
                          {institutions.length === 0 ? "공개된 기관 없음" : (
                            <details className="person-gukgam-institutions">
                              <summary>{institutions.length}곳</summary>
                              <ul>
                                {institutions.map((organization) => (
                                  <li key={organization.id}><Link href={`/organizations/${organization.id}`}>{organization.name}</Link></li>
                                ))}
                              </ul>
                            </details>
                          )}
                        </dd>
                      </div>
                      <div>
                        <dt>근거</dt>
                        <dd><a href={`#claim-${member.claim_id}`}>국회 명부상 위원회 기재</a></dd>
                      </div>
                    </dl>
                  </div>
                );
              })}
              {memberCommittees.length > 0 && (
                <p className="gukgam-scope-note">
                  국회 명부 시점의 위원 표기이며 감사 당일 출석이 아닙니다. 일정은 공식 계획서상 일정입니다.
                </p>
              )}
            </section>
          )}

          {recentActivity.items.length > 0 && (
            <section className="person-section" id="recent-activity" aria-labelledby="recent-activity-title">
              <div className="section-intro"><h2 id="recent-activity-title">최근 공식 활동</h2></div>
              <p className="section-note">
                공개된 발의·표결 기록의 활동일 기준 {recentActivity.datedCount.toLocaleString("ko-KR")}건 중 최근 {recentActivity.items.length}건
                {recentActivity.undatedCount > 0 && ` · 날짜 미기재·형식 미확인 ${recentActivity.undatedCount.toLocaleString("ko-KR")}건은 정렬에서 제외`}
              </p>
              <ol className="vote-rows">
                {recentActivity.items.map(({ claim, date, action }) => (
                  <li className="vote-row" key={claim.id}>
                    <time className="vote-date" dateTime={date}>{date}</time>
                    <span className="vote-bill"><a href={`#claim-${claim.id}`}>{claim.object_text}</a><small className="claim-date">{action}</small></span>
                    <span className={`status ${claim.epistemic_status}`}>{statusLabel(claim.epistemic_status)}</span>
                    <div className="vote-trace source-links">
                      <a href={`#claim-${claim.id}`}>근거 기록 열기</a>
                      {claim.source_conflict && <span className="status conflict">{statusLabel("CONFLICT")}</span>}
                      {supportingActivityEvidence(claim)
                        .filter((item, index, items) => items.findIndex((other) => other.source_id === item.source_id) === index)
                        .map((item) => <a key={item.source_id} href={`#source-${item.source_id}`}>{sourceById.get(item.source_id)?.title ?? "출처"}</a>)}
                    </div>
                  </li>
                ))}
              </ol>
            </section>
          )}

          {person.identity_status === "RESOLVED" && <PersonVoteExplorer records={votes} eligibleCount={profile?.sections.find((section) => section.id === "decision_episodes")?.eligible_count} inputScope={profile?.sections.find((section) => section.id === "decision_episodes")?.input_scope}  existingClaimIds={[...representedClaims]} />}

          <section className="person-section" id="records" aria-labelledby="records-title">
            <div className="section-intro">
              <h2 id="records-title">기록</h2>
            </div>
            {profile ? (
              <>
                <div className="profile-sections">
                  {profile.sections.map((section) => section.id === "career_timeline" || section.id === "limitations" || (section.entries.length === 0 && !["public_declared_assets", "official_press_records", "public_self_housing"].includes(section.id)) ? null : (
                    <section className="profile-section" key={section.id} id={`section-${section.id}`} aria-labelledby={`heading-${section.id}`}>
                      <div className="section-heading">
                        <div><h3 id={`heading-${section.id}`}>{section.label}</h3></div>
                        <span className={`status ${section.status}`}>{statusLabel(section.status)}</span>
                      </div>
                      {section.note && <p className="section-note">{section.note}</p>}
                      {section.id === "public_declared_assets" && section.entries.length === 0 && <p className="empty-note">이 인물에게 근거가 연결된 공개 신고재산 기록이 없습니다. 재산이 없거나 0원이라는 뜻은 아닙니다.</p>}
                      {section.id === "legislative_activity" ? <PersonClaimLibrary claimIds={section.entries.flatMap((entry) => entry.claim_id ? [entry.claim_id] : [])} existingClaimIds={staticClaimIds} legislative /> : section.entries.some(isPlenaryVote)
                        ? <ol className="vote-rows">{section.entries.map(renderEntry)}</ol>
                        : section.entries.map(renderEntry)}
                    </section>
                  ))}
                </div>
              </>
            ) : (
              <p className="empty-state"><span><span className="status UNKNOWN">{statusLabel("UNKNOWN")}</span> <strong>아직 공개된 기록이 없습니다.</strong></span></p>
            )}
            {otherClaims.length > 0 && (
              <details className="profile-other-records">
                <summary>기타 공개 근거 기록 {otherClaims.length}건</summary>
                <PersonClaimLibrary claimIds={otherClaims.map((claim) => claim.id)} existingClaimIds={staticClaimIds} />
              </details>
            )}
            {(emptyLaneGroups.length > 0 || Boolean(limitations?.entries.length)) && (
              <details className="profile-coverage">
                <summary>자료 범위와 한계</summary>
                {limitations && limitations.entries.length > 0
                  ? limitations.entries.map(renderEntry)
                  : emptyLaneGroups.map((group) => <PendingLanes key={group.reason} title={group.title} lanes={group.lanes} detail={group.detail} />)}
              </details>
            )}
          </section>

          <section className="ontology-section person-section" id="official-connections" aria-labelledby="ontology-title">
            <div className="section-intro">
              <h2 id="ontology-title">공식 기록상 연결</h2>
            </div>
            {ontologyResult.state === "error" ? (
              <ReadState error={ontologyResult.error} />
            ) : ontology && ontology.edges.length > 0 ? (
              <OntologyLocalGraph graph={ontology} sourceTitles={sourceTitleById} gukgamCommittees={gukgamCommittees} claimAnchorsInRecords />
            ) : relationships && relationships.relation_count > 0 ? null : (
              <p className="empty-state" role="status">
                <span><strong>표시할 공개 직접 연결 기록이 없습니다.</strong></span>
              </p>
            )}
            {relationshipsResult.state === "error" ? <ReadState error={relationshipsResult.error} /> : relationships && <PersonRelationshipsView data={relationships} />}
          </section>

          <section className="source-library person-section" id="sources" aria-labelledby="sources-title">
            <div className="section-intro">
              <h2 id="sources-title">이 프로필의 출처</h2>
            </div>
            {sourceError?.state === "error" && <ReadState error={sourceError.error} />}
            {sources.length === 0 && !sourceError ? <p className="empty">표시할 출처가 없습니다.</p> : (
              <SourceLibrary />
            )}
          </section>
        </div>
      </div>
    </div>
    </PersonEvidenceProvider>
  );
}

import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { getGukgamCommittees, getGukgamTargets, getPerson, getPersonOntology, getSource } from "../../data";
import EvidencePanel, { EvidenceTraceList, SourceCard } from "../../components/evidence-panel";
import CareerTermStrip from "../../components/career-term-strip";
import FactBox, { type FactRow } from "../../components/fact-box";
import OntologyLocalGraph from "../../components/ontology-local-graph";
import OpenTargetDetails from "../../components/open-target-details";
import PendingLanes from "../../components/pending-lanes";
import ReadState from "../../components/read-state";
import ReviewedPortraitImage from "../../components/reviewed-portrait";
import { committeeHref } from "../../gukgam/2026/committees";
import { formatAuditDate } from "../../gukgam/2026/schedule";
import { getReviewedPortrait, portraitSourceLabel } from "../../portrait";
import { predicateLabel } from "../../predicate-labels";
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
];

// Per-bill activity records are listed in their own record sections, not as key facts.
const ACTIVITY_RECORD_PREDICATES = new Set(["ASSEMBLY_BILL_PARTICIPATION", "ASSEMBLY_PLENARY_VOTE"]);

// Person Claims linked to one exact source row after human identity review.
const LINKED_WITNESS_PREDICATE = "LISTED_AS_GUKGAM_WITNESS";

const EMPTY_LANE_REASONS: { reason: ProfileSectionReason; title: string; detail: string }[] = [
  {
    reason: "SOURCE_NOT_COLLECTED",
    title: "공식 근거 출처 미연결",
    detail: "기록이 없다는 뜻이 아니라 이 항목을 뒷받침할 공식 출처가 아직 이 인물에게 연결되지 않았다는 뜻입니다.",
  },
  {
    reason: "INSUFFICIENT_EVIDENCE",
    title: "비교·분석할 근거 부족",
    detail: "공개된 근거가 비교나 분석의 최소 조건에 못 미쳐 결과를 만들지 않았습니다.",
  },
  {
    reason: "DERIVATION_NOT_AVAILABLE",
    title: "검토된 분석 결과 없음",
    detail: "근거에서 만든 질문·패턴·시나리오는 검토를 거친 경우에만 표시합니다.",
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
    description: `${result.data.canonical_name}의 공개 기록, Claim, Evidence와 출처를 확인합니다.`,
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
  const [portrait, ontologyResult, committeesResult, targetsResult] = await Promise.all([
    getReviewedPortrait(person),
    getPersonOntology(id),
    getGukgamCommittees(),
    getGukgamTargets(),
  ]);
  const gukgamCommittees = committeesResult.state === "success"
    ? committeesResult.data.committees.map((committee) => committee.committee_name)
    : [];
  const ontology = ontologyResult.state === "success" ? ontologyResult.data : null;

  const sectionSourceIds =
    person.profile?.sections.flatMap((section) =>
      section.entries.flatMap((entry) => entry.source_ids),
    ) ?? [];
  const claimSourceIds = (person.claims ?? []).flatMap((claim) => claim.source_ids);
  const ontologySourceIds = ontology?.edges.flatMap((edge) => edge.source_ids) ?? [];
  const sourceIds = [...new Set([...sectionSourceIds, ...claimSourceIds, ...ontologySourceIds])];
  const sourceResults = await Promise.all(sourceIds.map(getSource));
  const sources = sourceResults.flatMap((item) => item.state === "success" ? [item.data] : []);
  const sourceError = sourceResults.find((item) => item.state === "error");
  const sourceById = new Map(sources.map((source) => [source.id, source]));
  const sourceTitleById = Object.fromEntries(sources.map((source) => [source.id, source.title]));
  const profile = person.profile;
  const claims = person.claims ?? [];
  const claimById = new Map(claims.map((claim) => [claim.id, claim]));
  const publishedClaims = claims.filter((claim) => claim.publication_status === "PUBLISHED");
  const knownPredicates = new Set(FACT_PREDICATES.map(([predicate]) => predicate));
  const factRows: FactRow[] = [
    ...FACT_PREDICATES.flatMap(([predicate, label]) =>
      publishedClaims.filter((claim) => claim.predicate === predicate).map((claim) => ({
        key: claim.id, label, value: claim.object_text, claim,
      })),
    ),
    ...publishedClaims
      .filter((claim) => !knownPredicates.has(claim.predicate) && !ACTIVITY_RECORD_PREDICATES.has(claim.predicate))
      .map((claim) => ({ key: claim.id, label: predicateLabel(claim.predicate), value: claim.object_text, claim })),
  ];

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
      .filter((section) => section.entries.length === 0 && (section.reason ?? "SOURCE_NOT_COLLECTED") === group.reason)
      .map((section) => section.label),
  })).filter((group) => group.lanes.length > 0);

  const isPlenaryVote = (entry: ProfileEntry) =>
    entry.kind === "DECISION_EPISODE" && entry.details.action === "PLENARY_ROLL_CALL_VOTE";

  const renderEntry = (entry: ProfileEntry) => {
    const claim: Claim | undefined = entry.claim_id ? claimById.get(entry.claim_id) : undefined;
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
            <span className="claim-kind">DERIVED · CHANGE</span>
            {entry.epistemic_status && <span className={`status ${entry.epistemic_status}`}>{entry.epistemic_status}</span>}
          </div>
          <p className="claim-title">{entry.title}</p>
          <div className="change-sequence" aria-label="Compared dated sequence">
            <div className="change-point">
              <span className="micro-label">이전 · {changeDetails.earlier?.date ?? "UNKNOWN"}</span>
              <strong>{changeDetails.earlier?.role_text ?? "표시값 없음"}</strong>
              <small>{changeDetails.earlier?.predicate ?? "UNKNOWN"} · Claim {changeDetails.earlier?.claim_id ?? "UNKNOWN"}</small>
            </div>
            <span className="change-arrow" aria-hidden="true">→</span>
            <div className="change-point later">
              <span className="micro-label">이후 · {changeDetails.later?.date ?? "UNKNOWN"}</span>
              <strong>{changeDetails.later?.role_text ?? "표시값 없음"}</strong>
              <small>{changeDetails.later?.predicate ?? "UNKNOWN"} · Claim {changeDetails.later?.claim_id ?? "UNKNOWN"}</small>
            </div>
          </div>
          {changeDetails.derived_reason && <p className="change-reason">{changeDetails.derived_reason}</p>}
          <details className="audit-details">
            <summary>계산 방법과 범위</summary>
            <small>
              Method {changeDetails.method_version ?? "UNKNOWN"}<br />
              Scope {changeDetails.input_scope?.provider_record_identity ?? "UNKNOWN"}<br />
              Correction semantics {changeDetails.input_scope?.correction_semantics ?? "UNKNOWN"}<br />
              Eligible inputs {changeDetails.coverage?.eligible_claim_count ?? "UNKNOWN"}<br />
              {changeDetails.coverage?.comparison ?? "Comparison rule unavailable"}<br />
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
        <li className="vote-row" key={entry.id} id={`claim-${entry.claim_id}`}>
          <span className="vote-date">{entry.date ?? "날짜 미기재"}</span>
          <span className="vote-bill">
            {typeof entry.details.detail_url === "string"
              ? <a href={entry.details.detail_url} target="_blank" rel="noreferrer">{String(entry.details.target)}</a>
              : String(entry.details.target)}
          </span>
          <span className="status AVAILABLE vote-value">{String(entry.details.outcome)}</span>
          <details className="audit-details vote-trace">
            <summary>근거</summary>
            <small>
              {source ? <a href={`#source-${source.id}`}>{source.title}</a> : "출처"} · {entry.epistemic_status}<br />
              Claim {entry.claim_id}<br />
              Evidence {trace?.id ?? "없음"}<br />
              SourceSnapshot {trace?.snapshot_id ?? "없음"}<br />
              FeederObservation {trace?.feeder_observation_id ?? "없음"}
            </small>
          </details>
        </li>
      );
    }

    if (claim) {
      return (
        <EvidencePanel
          key={entry.id}
          claim={claim}
          sourceById={sourceById}
          title={isLegislativeActivity ? activityTitle ?? entry.title : entry.title}
          kind={isLegislativeActivity ? "OFFICIAL BILL RECORD" : entry.kind}
          sourceConflict={entry.source_conflict}
        >
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
      <article className="claim" key={entry.id} id={entry.claim_id ? `claim-${entry.claim_id}` : undefined}>
        <div className="claim-heading">
          <span className="claim-kind">{entry.kind}</span>
          {entry.epistemic_status && <span className={`status ${entry.epistemic_status}`}>{entry.epistemic_status}</span>}
        </div>
        <p className="claim-title">{entry.title}</p>
        {entry.date && <small className="claim-date">기준 {entry.date}</small>}
        {entry.evidence && entry.evidence.length > 0 ? (
          <EvidenceTraceList traces={entry.evidence} sourceById={sourceById} claimLabel={entry.claim_id ?? "not applicable"} />
        ) : entry.source_ids.length > 0 ? (
          <div className="source-links">
            <strong>출처 참조</strong>
            {entry.source_ids.map((sourceId) => (
              <a href={`#source-${sourceId}`} key={sourceId}>{sourceById.get(sourceId)?.title ?? "Source record"}</a>
            ))}
          </div>
        ) : null}
      </article>
    );
  };

  return (
    <div className="site-page profile-page">
      <Link href="/people" className="back-link"><span aria-hidden="true">←</span> 인물 찾기</Link>
      <header className="profile-header">
        <div>
          <div className="profile-title-row">
            <h1>{person.canonical_name}</h1>
            <span className={`status identity ${person.identity_status}`}>{person.identity_status}</span>
          </div>
        </div>
        {portrait ? (
          <figure className="profile-portrait" style={{ maxWidth: portrait.source_width }}>
            <ReviewedPortraitImage
              src={portrait.local_path}
              width={portrait.source_width}
              height={portrait.source_height}
              alt={`${person.canonical_name} 공개 사진`}
            />
            <figcaption className="portrait-credit">
              <span>사진: <a href={portrait.source_page_url} target="_blank" rel="noreferrer">{portrait.creator} · {portraitSourceLabel(portrait)}</a> · <a href={portrait.license_url} target="_blank" rel="noreferrer">{portrait.license}</a></span>
              <details className="audit-details">
                <summary>사진 출처 정보</summary>
                <small>
                  File {portrait.file_title}<br />
                  Revision {portrait.source_revision_timestamp}<br />
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
              <li><a href="#key-facts">핵심 기록</a></li>
              {hasGukgam && <li><a href="#gukgam-2026">국정감사</a></li>}
              <li><a href="#records">기록</a></li>
              <li><a href="#official-connections">연결</a></li>
              <li><a href="#sources">출처</a></li>
            </ul>
          </nav>
        </aside>

        <div className="profile-content">
          <section className="person-section" id="key-facts" aria-labelledby="key-facts-title">
            <div className="section-intro">
              <h2 id="key-facts-title">핵심 기록</h2>
            </div>
            {factRows.length > 0 ? <FactBox rows={factRows} /> : (
              <p className="empty"><span className="status UNKNOWN">UNKNOWN</span> 표시할 공개 기록이 아직 없습니다.</p>
            )}
          </section>

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

          <section className="person-section" id="records" aria-labelledby="records-title">
            <div className="section-intro">
              <h2 id="records-title">기록</h2>
            </div>
            {profile ? (
              <>
                <CareerTermStrip entries={[
                  ...(profile.sections.find((section) => section.id === "career_timeline")?.entries ?? []),
                  ...(profile.sections.find((section) => section.id === "current_role")?.entries ?? []),
                ]} claims={publishedClaims} />
                {emptyLaneGroups.map((group) => (
                  <PendingLanes key={group.reason} title={group.title} lanes={group.lanes} detail={group.detail} />
                ))}
                <div className="profile-sections">
                  {profile.sections.map((section) => section.entries.length === 0 ? null : (
                    <section className="profile-section" key={section.id} id={`section-${section.id}`} aria-labelledby={`heading-${section.id}`}>
                      <div className="section-heading">
                        <div><h3 id={`heading-${section.id}`}>{section.label}</h3></div>
                        <span className={`status ${section.status}`}>{section.status}</span>
                      </div>
                      {section.note && <p className="section-note">{section.note}</p>}
                      {section.entries.some(isPlenaryVote)
                        ? <ol className="vote-rows">{section.entries.map(renderEntry)}</ol>
                        : section.entries.map(renderEntry)}
                    </section>
                  ))}
                </div>
              </>
            ) : (
              <p className="empty-state"><span><span className="status UNKNOWN">UNKNOWN</span> <strong>아직 공개된 기록이 없습니다.</strong></span></p>
            )}
          </section>

          <section className="ontology-section person-section" id="official-connections" aria-labelledby="ontology-title">
            <div className="section-intro">
              <h2 id="ontology-title">공식 기록상 연결</h2>
            </div>
            {ontologyResult.state === "error" ? (
              <ReadState error={ontologyResult.error} />
            ) : ontology && ontology.edges.length > 0 ? (
              <OntologyLocalGraph graph={ontology} sourceTitles={sourceTitleById} gukgamCommittees={gukgamCommittees} />
            ) : (
              <p className="empty-state" role="status">
                <span><strong>아직 공개된 연결이 없습니다.</strong></span>
              </p>
            )}
          </section>

          <section className="source-library person-section" id="sources" aria-labelledby="sources-title">
            <div className="section-intro">
              <h2 id="sources-title">이 프로필의 출처</h2>
            </div>
            {sourceError?.state === "error" && <ReadState error={sourceError.error} />}
            {sources.length === 0 && !sourceError ? <p className="empty">표시할 출처가 없습니다.</p> : (
              <div className="source-grid">
                {sources.map((source) => <SourceCard key={source.id} source={source} />)}
              </div>
            )}
          </section>
        </div>
      </div>
    </div>
  );
}

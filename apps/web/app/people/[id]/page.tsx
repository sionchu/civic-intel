import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { latestRecordedAt, predicateLabel } from "../../claim-labels";
import { getGukgamCommittees, getGukgamTargets, getPerson, getPersonOntology, getSource } from "../../data";
import EvidencePanel, { EvidenceTraceList, SourceCard } from "../../components/evidence-panel";
import FactBox, { type FactRow } from "../../components/fact-box";
import OntologyLocalGraph from "../../components/ontology-local-graph";
import OpenTargetDetails from "../../components/open-target-details";
import PendingLanes from "../../components/pending-lanes";
import ReadState from "../../components/read-state";
import RecordHeader from "../../components/record-header";
import { committeeHref } from "../../gukgam/2026/committees";
import { formatAuditDate } from "../../gukgam/2026/schedule";
import { getReviewedPortrait } from "../../portrait";
import { buildPageMetadata } from "../../site-metadata";
import type { Claim, ProfileEntry } from "../../types";

export const dynamic = "force-dynamic";

// Identity-header facts first, in this reading order; other published Claims follow.
const FACT_PREDICATES = ["HELD_ROLE", "ASSEMBLY_PARTY", "ASSEMBLY_DISTRICT", "ASSEMBLY_COMMITTEES", "ASSEMBLY_REELECTION"];

export async function generateMetadata({
  params,
}: {
  params: Promise<{ id: string }>;
}): Promise<Metadata> {
  const { id } = await params;
  const result = await getPerson(id);
  if (result.state === "error") {
    return buildPageMetadata({
      title: "Person record",
      description: "Civic Intel 공개 Person 기록",
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
        <Link href="/people" className="back-link"><span aria-hidden="true">←</span> People</Link>
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
  const knownPredicates = new Set(FACT_PREDICATES);
  const factRows: FactRow[] = [
    ...FACT_PREDICATES.flatMap((predicate) =>
      publishedClaims.filter((claim) => claim.predicate === predicate).map((claim) => ({
        key: claim.id, label: predicateLabel(predicate), value: claim.object_text, claim,
      })),
    ),
    ...publishedClaims
      .filter((claim) => !knownPredicates.has(claim.predicate) && claim.predicate !== "ASSEMBLY_BILL_PARTICIPATION")
      .map((claim) => ({ key: claim.id, label: predicateLabel(claim.predicate), value: claim.object_text, claim })),
  ];

  const memberCommittees = committeesResult.state === "success"
    ? committeesResult.data.committees.flatMap((committee) => {
        const member = committee.members.find((item) => item.person.id === person.id);
        return member ? [{ committee, member }] : [];
      })
    : [];
  const targetItems = targetsResult.state === "success" ? targetsResult.data.items : [];
  const emptyLanes = profile ? profile.sections.filter((section) => section.entries.length === 0).map((section) => section.label) : [];

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
              <span className="micro-label">EARLIER · {changeDetails.earlier?.date ?? "UNKNOWN"}</span>
              <strong>{changeDetails.earlier?.role_text ?? "표시값 없음"}</strong>
              <small>{changeDetails.earlier?.predicate ?? "UNKNOWN"} · Claim {changeDetails.earlier?.claim_id ?? "UNKNOWN"}</small>
            </div>
            <span className="change-arrow" aria-hidden="true">→</span>
            <div className="change-point later">
              <span className="micro-label">LATER · {changeDetails.later?.date ?? "UNKNOWN"}</span>
              <strong>{changeDetails.later?.role_text ?? "표시값 없음"}</strong>
              <small>{changeDetails.later?.predicate ?? "UNKNOWN"} · Claim {changeDetails.later?.claim_id ?? "UNKNOWN"}</small>
            </div>
          </div>
          {changeDetails.derived_reason && <p className="change-reason">{changeDetails.derived_reason}</p>}
          <details className="audit-details">
            <summary>Methodology & coverage</summary>
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
                {typeof entry.details.bill_no === "string" && <div><dt>Bill no.</dt><dd>{entry.details.bill_no}</dd></div>}
                {typeof entry.details.committee === "string" && <div><dt>Committee</dt><dd>{entry.details.committee}</dd></div>}
                {typeof entry.details.process_result === "string" && <div><dt>Result / status</dt><dd>{entry.details.process_result}</dd></div>}
              </dl>
              {typeof entry.details.detail_url === "string" && <a className="activity-link" href={entry.details.detail_url} target="_blank" rel="noreferrer">Official bill detail <span aria-hidden="true">↗</span></a>}
            </>
          )}
        </EvidencePanel>
      );
    }

    return (
      <article className="claim" key={entry.id}>
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
      <Link href="/people" className="back-link"><span aria-hidden="true">←</span> People</Link>
      <RecordHeader
        kind="인물 기록"
        name={person.canonical_name}
        status={<span className={`status identity ${person.identity_status}`}>{person.identity_status}</span>}
        lede="공개된 Claim과 근거만 모았습니다. 각 항목의 근거에서 출처와 기준일을 확인할 수 있습니다."
        claimCount={publishedClaims.length}
        sourceCount={sources.length}
        recordedAt={latestRecordedAt(publishedClaims)}
        aside={portrait ? (
            <figure className="profile-portrait">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={portrait.local_path}
                width={portrait.source_width}
                height={portrait.source_height}
                alt={`${person.canonical_name} 공개 사진`}
              />
              <figcaption className="portrait-credit">
                <span>사진: <a href={portrait.source_page_url} target="_blank" rel="noreferrer">{portrait.creator} · Wikimedia Commons</a> · <a href={portrait.license_url} target="_blank" rel="noreferrer">{portrait.license}</a></span>
                <details className="audit-details">
                  <summary>Portrait source audit</summary>
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
      />

      <OpenTargetDetails />
      <div className="profile-layout">
        <aside className="profile-index" aria-label="이 페이지">
          <div className="index-heading"><span className="micro-label">이 페이지</span></div>
          <nav>
            <ul className="page-anchors">
              <li><a href="#key-facts">핵심 기록</a></li>
              {memberCommittees.length > 0 && <li><a href="#gukgam-2026">국정감사</a></li>}
              <li><a href="#records">기록</a></li>
              <li><a href="#official-connections">연결</a></li>
              <li><a href="#sources">출처</a></li>
            </ul>
          </nav>
        </aside>

        <div className="profile-content">
          <section className="person-section" id="key-facts" aria-labelledby="key-facts-title">
            <div className="section-intro">
              <div><span className="eyebrow">Published claims</span><h2 id="key-facts-title">핵심 기록</h2></div>
              <p>현재 공개된 Claim만 항목별로 모았습니다. 각 행의 근거를 누르면 아래 기록에서 출처까지 펼쳐집니다.</p>
            </div>
            {factRows.length > 0 ? <FactBox rows={factRows} /> : (
              <p className="empty"><span className="status UNKNOWN">UNKNOWN</span> 표시할 공개 Claim이 아직 없습니다.</p>
            )}
          </section>

          {memberCommittees.length > 0 && (
            <section className="person-section" id="gukgam-2026" aria-labelledby="person-gukgam-title">
              <div className="section-intro">
                <div><span className="eyebrow">Gukgam 2026 / Claim-backed</span><h2 id="person-gukgam-title">2026 국정감사</h2></div>
                <p>위원회 소속 기록이며 해당 기관 질의 여부를 뜻하지 않습니다.</p>
              </div>
              {targetsResult.state === "error" && <ReadState error={targetsResult.error} />}
              {memberCommittees.map(({ committee, member }) => {
                const items = targetItems.filter((item) => item.committee_name === committee.committee_name);
                const dates = [...new Set(items.map((item) => item.audit_date))].sort();
                const institutions = [...new Map(items.map((item) => [item.organization.id, item.organization])).values()]
                  .sort((left, right) => left.name.localeCompare(right.name, "ko"));
                return (
                  <div className="person-gukgam-committee" key={committee.committee_name}>
                    <h3><Link href={committeeHref(committee.committee_name)}>{committee.committee_name}</Link></h3>
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
              <p className="gukgam-scope-note">
                국회 명부 시점의 위원 표기이며 감사 당일 출석이 아닙니다. 일정은 공식 계획서상 일정입니다.
              </p>
            </section>
          )}

          <section className="person-section" id="records" aria-labelledby="records-title">
            <div className="section-intro">
              <div><span className="eyebrow">Evidence profile</span><h2 id="records-title">기록</h2></div>
              <p>공개된 기록과 아직 근거가 연결되지 않은 영역을 구분합니다.</p>
            </div>
            {profile ? (
              <>
                <PendingLanes lanes={emptyLanes} />
                <div className="profile-sections">
                  {profile.sections.map((section) => section.entries.length === 0 ? null : (
                    <section className="profile-section" key={section.id} id={`section-${section.id}`} aria-labelledby={`heading-${section.id}`}>
                      <div className="section-heading">
                        <div><h3 id={`heading-${section.id}`}>{section.label}</h3></div>
                        <span className={`status ${section.status}`}>{section.status}</span>
                      </div>
                      {section.note && <p className="section-note">{section.note}</p>}
                      {(() => {
                        // Coverage gaps without their own Claim read as one compact list, so absent
                        // evidence never takes more room than the evidence itself.
                        const gaps = section.entries.filter((entry) => entry.kind === "LIMITATION" && !entry.claim_id);
                        const rest = section.entries.filter((entry) => !gaps.includes(entry));
                        return (
                          <>
                            {rest.map(renderEntry)}
                            {gaps.length > 0 && (
                              <ul className="limitation-list" aria-label={`${section.label} 미확인 항목`}>
                                {gaps.map((entry) => (
                                  <li key={entry.id} id={`entry-${entry.id}`}>
                                    <span>{entry.title}</span>
                                    {entry.epistemic_status && <span className={`status ${entry.epistemic_status}`}>{entry.epistemic_status}</span>}
                                  </li>
                                ))}
                              </ul>
                            )}
                          </>
                        );
                      })()}
                    </section>
                  ))}
                </div>
              </>
            ) : (
              <p className="empty-state"><span className="empty-state-mark" aria-hidden="true">∅</span><span><strong>Profile projection unavailable.</strong><small><span className="status UNKNOWN">UNKNOWN</span> 공개 profile을 구성할 근거가 없습니다.</small></span></p>
            )}
          </section>

          <section className="ontology-section person-section" id="official-connections" aria-labelledby="ontology-title">
            <div className="section-intro">
              <div>
                <span className="eyebrow">Governance ontology / local view</span>
                <h2 id="ontology-title">공식 기록상 연결</h2>
              </div>
              <p>현재 공개 Claim/Evidence에서 직접 지원되는 관계만 local graph와 동일한 텍스트 목록으로 보여줍니다.</p>
            </div>
            {ontologyResult.state === "error" ? (
              <ReadState error={ontologyResult.error} />
            ) : ontology && ontology.edges.length > 0 ? (
              <OntologyLocalGraph graph={ontology} sourceTitles={sourceTitleById} gukgamCommittees={gukgamCommittees} />
            ) : (
              <p className="empty-state" role="status">
                <span className="empty-state-mark" aria-hidden="true">∅</span>
                <span><strong>현재 공개 가능한 연결이 없습니다.</strong><small>관계가 없다는 뜻이 아니라, 현재 공개 Claim · Evidence로 확인되는 연결이 없다는 뜻입니다.</small></span>
              </p>
            )}
          </section>

          <section className="source-library person-section" id="sources" aria-labelledby="sources-title">
            <div className="section-intro">
              <div><span className="eyebrow">Evidence & audit</span><h2 id="sources-title">이 프로필의 출처</h2></div>
              <p>출처의 공개일, 확인 시각과 출처 정책 요약을 보여줍니다. 내부 식별자는 감사 ID 안에 둡니다.</p>
            </div>
            {sourceError?.state === "error" && <ReadState error={sourceError.error} />}
            {sources.length === 0 && !sourceError ? <p className="empty">No source cards available.</p> : (
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

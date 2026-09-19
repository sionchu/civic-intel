import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { getPerson, getPersonOntology, getSource } from "../../data";
import OntologyLocalGraph from "../../components/ontology-local-graph";
import ReadState from "../../components/read-state";
import { getReviewedPortrait } from "../../portrait";
import { buildPageMetadata } from "../../site-metadata";

export const dynamic = "force-dynamic";

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
  const [portrait, ontologyResult] = await Promise.all([
    getReviewedPortrait(person),
    getPersonOntology(id),
  ]);
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

  return (
    <div className="site-page profile-page">
      <Link href="/people" className="back-link"><span aria-hidden="true">←</span> People</Link>
      <header className="profile-header">
        <div>
          <div className="eyebrow"><span className="eyebrow-mark" aria-hidden="true">✦</span> Evidence profile / Resolved identity</div>
          <div className="profile-title-row">
            <h1>{person.canonical_name}</h1>
            <span className={`status identity ${person.identity_status}`}>{person.identity_status}</span>
          </div>
          <p className="profile-lede">canonical identity에 연결된 published evidence를 현재 읽기 화면으로 투영합니다.</p>
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
        ) : (
          <div className="profile-stamp" aria-hidden="true">
            <span className="micro-label">PUBLIC RECORD</span>
            <strong>CI</strong>
            <span>directory / 01</span>
          </div>
        )}
      </header>

      {profile ? (
        <div className="profile-layout">
          <aside className="profile-index" aria-label="Profile sections">
            <div className="index-heading"><span className="micro-label">Profile map</span><span>{profile.sections.length} sections</span></div>
            <nav>
              <ol>
                {profile.sections.map((section, index) => (
                  <li key={section.id}>
                    <a href={`#section-${section.id}`}>
                      <span className="index-number">{String(index + 1).padStart(2, "0")}</span>
                      <span>{section.label}</span>
                      <span className={`status ${section.status}`}>{section.status}</span>
                    </a>
                  </li>
                ))}
              </ol>
            </nav>
            <a className="profile-source-index-link" href="#official-connections">공식 연결</a>
            <a className="profile-source-index-link" href="#sources-title">Evidence &amp; Sources</a>
          </aside>

          <div className="profile-content">
            <section className="coverage-overview" aria-labelledby="coverage-title">
              <div className="overview-heading">
                <span className="eyebrow">Coverage</span>
                <h2 id="coverage-title">{profile.profile_kind === "ASSEMBLY_MEMBER" ? "What this profile can show" : "What the directory can show"}</h2>
                <p>published Claim/Evidence 범위와 아직 비어 있는 영역을 구분합니다.</p>
              </div>
              <div className="coverage">
                <div className="coverage-card available-card"><span className="status AVAILABLE">AVAILABLE</span><strong>{profile.coverage.available}</strong><small>sections with entries</small></div>
                <div className="coverage-card partial-card"><span className="status PARTIAL">PARTIAL</span><strong>{profile.coverage.partial}</strong><small>sections with limits</small></div>
                <div className="coverage-card unknown-card"><span className="status UNKNOWN">UNKNOWN</span><strong>{profile.coverage.unknown}</strong><small>sections without evidence</small></div>
              </div>
            </section>

            <div className="profile-sections">
              {profile.sections.map((section) => (
                <section className="profile-section" key={section.id} id={`section-${section.id}`} aria-labelledby={`heading-${section.id}`}>
                  <div className="section-heading">
                    <div><span className="section-index">{String(profile.section_order.indexOf(section.id) + 1).padStart(2, "0")}</span><h2 id={`heading-${section.id}`}>{section.label}</h2></div>
                    <span className={`status ${section.status}`}>{section.status}</span>
                  </div>
                  {section.note && <p className="section-note">{section.note}</p>}
                  {section.entries.length === 0 ? (
                    <p className="empty"><span className="status UNKNOWN">UNKNOWN</span> 검토된 항목이 없습니다.</p>
                  ) : (
                    section.entries.map((entry) => {
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
                      return (
                      <article className={`claim${changeDetails ? " change-card" : ""}`} key={entry.id}>
                        <div className="claim-heading">
                          <span className="claim-kind">{changeDetails ? "DERIVED · CHANGE" : entry.kind}</span>
                          {entry.epistemic_status && <span className={`status ${entry.epistemic_status}`}>{entry.epistemic_status}</span>}
                        </div>
                        {!changeDetails && entry.source_conflict && (
                          <div className="conflict-note">
                            <span className="status CONFLICT">SOURCE CONFLICT</span>
                            <span>서로 다른 근거가 상충하며 자동으로 어느 한쪽을 진실로 판정하지 않습니다.</span>
                          </div>
                        )}
                        {changeDetails ? (
                          <>
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
                          </>
                        ) : isLegislativeActivity ? (
                          <>
                            <div className="activity-badges">
                              <span className="status AVAILABLE">{activityRole}</span>
                              <span className="claim-kind">OFFICIAL BILL RECORD</span>
                            </div>
                            <p className="claim-title">{activityTitle ?? entry.title}</p>
                            <p className="activity-assertion">{entry.title}</p>
                            {entry.date && <small className="claim-date">Proposal date / {entry.date}</small>}
                            <dl className="activity-facts">
                              {typeof entry.details.bill_no === "string" && <div><dt>Bill no.</dt><dd>{entry.details.bill_no}</dd></div>}
                              {typeof entry.details.committee === "string" && <div><dt>Committee</dt><dd>{entry.details.committee}</dd></div>}
                              {typeof entry.details.process_result === "string" && <div><dt>Result / status</dt><dd>{entry.details.process_result}</dd></div>}
                            </dl>
                            {typeof entry.details.detail_url === "string" && <a className="activity-link" href={entry.details.detail_url} target="_blank" rel="noreferrer">Official bill detail <span aria-hidden="true">↗</span></a>}
                          </>
                        ) : (
                          <>
                            <p className="claim-title">{entry.title}</p>
                            {entry.date && <small className="claim-date">Date / {entry.date}</small>}
                          </>
                        )}
                        {!changeDetails && typeof entry.details.resolution_note === "string" && entry.details.resolution_note && (
                          <p className="resolution">{entry.details.resolution_note}</p>
                        )}
                        {entry.evidence && entry.evidence.length > 0 ? (
                          <div className="evidence-list">
                            <div className="evidence-list-heading"><strong>Evidence trace</strong><span>{entry.evidence.length} trace{entry.evidence.length === 1 ? "" : "s"}</span></div>
                            {entry.evidence.map((trace) => {
                              const source = sourceById.get(trace.source_id);
                              return (
                                <div className="evidence-trace" key={trace.id}>
                                  <span className={`status ${trace.stance}`}>{trace.stance}</span>
                                  {source ? <Link href={`#source-${source.id}`}>{source.title}</Link> : <span>Source unavailable</span>}
                                  <details className="audit-details">
                                    <summary>Audit trace</summary>
                                    <small>
                                      Evidence {trace.id}<br />
                                      Claim {entry.claim_id ?? "not applicable"}<br />
                                      Source {trace.source_id}<br />
                                      {trace.snapshot_id && <>SourceSnapshot {trace.snapshot_id}<br /></>}
                                      {trace.feeder_observation_id && <>FeederObservation {trace.feeder_observation_id}</>}
                                    </small>
                                  </details>
                                </div>
                              );
                            })}
                          </div>
                        ) : entry.source_ids.length > 0 ? (
                          <div className="source-links">
                            <strong>Source references</strong>
                            {entry.source_ids.map((sourceId) => {
                              const source = sourceById.get(sourceId);
                              return <Link href={`#source-${sourceId}`} key={sourceId}>{source?.title ?? "Source record"}</Link>;
                            })}
                          </div>
                        ) : null}
                      </article>
                      );
                    })
                  )}
                </section>
              ))}
            </div>
          </div>
        </div>
      ) : (
        <p className="empty-state"><span className="empty-state-mark" aria-hidden="true">∅</span><span><strong>Profile projection unavailable.</strong><small><span className="status UNKNOWN">UNKNOWN</span> 공개 profile을 구성할 근거가 없습니다.</small></span></p>
      )}


      <section className="ontology-section" id="official-connections" aria-labelledby="ontology-title">
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
          <OntologyLocalGraph graph={ontology} sourceTitles={sourceTitleById} />
        ) : (
          <p className="empty-state" role="status">
            <span className="empty-state-mark" aria-hidden="true">∅</span>
            <span><strong>현재 공개 가능한 연결이 없습니다.</strong><small>관계가 없다는 뜻이 아니라, 현재 ontology projection에 표시할 published Claim/Evidence가 없다는 뜻입니다.</small></span>
          </p>
        )}
      </section>

      <section className="source-library" aria-labelledby="sources-title">
        <div className="section-intro">
          <div><span className="eyebrow">Evidence & audit</span><h2 id="sources-title">Sources behind this profile</h2></div>
          <p>Source policy는 수집·저장·표시 범위를 함께 보여줍니다. 세부 식별자는 audit trace 안에 둡니다.</p>
        </div>
        {sourceError?.state === "error" && <ReadState error={sourceError.error} />}
        {sources.length === 0 && !sourceError ? <p className="empty">No source cards available.</p> : (
          <div className="source-grid">
            {sources.map((source) => (
              <article className="source" id={`source-${source.id}`} key={source.id}>
                <div className="source-card-topline"><span className="micro-label">Source record</span><span className="source-arrow" aria-hidden="true">↗</span></div>
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
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

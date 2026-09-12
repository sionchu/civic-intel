import Link from "next/link";
import { notFound } from "next/navigation";

import { getPerson, getSource } from "../../data";

export const dynamic = "force-dynamic";

export default async function PersonPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const person = await getPerson(id);
  if (!person) notFound();

  const sectionSourceIds =
    person.profile?.sections.flatMap((section) =>
      section.entries.flatMap((entry) => entry.source_ids),
    ) ?? [];
  const claimSourceIds = (person.claims ?? []).flatMap((claim) => claim.source_ids);
  const sourceIds = [...new Set([...sectionSourceIds, ...claimSourceIds])];
  const sources = (await Promise.all(sourceIds.map(getSource))).filter((item) => item !== null);
  const sourceById = new Map(sources.map((source) => [source.id, source]));

  return (
    <>
      <Link href="/" className="back">← Roster</Link>
      <div className="eyebrow">Evidence profile</div>
      <h1>{person.canonical_name}</h1>
      <span className={`status identity ${person.identity_status}`}>
        Identity: {person.identity_status}
      </span>

      {person.profile ? (
        <>
          <p className="lede">
            검토된 canonical evidence를 12개 프로파일 섹션으로 투영한 read model입니다.
            근거가 없는 섹션은 UNKNOWN으로 남습니다.
          </p>
          <div className="coverage">
            <span className="status AVAILABLE">AVAILABLE {person.profile.coverage.available}</span>
            <span className="status PARTIAL">PARTIAL {person.profile.coverage.partial}</span>
            <span className="status UNKNOWN">UNKNOWN {person.profile.coverage.unknown}</span>
          </div>
          <div className="profile-sections">
            {person.profile.sections.map((section) => (
              <section className="profile-section" key={section.id} id={`section-${section.id}`}>
                <div className="section-heading">
                  <h2>{section.label}</h2>
                  <span className={`status ${section.status}`}>{section.status}</span>
                </div>
                {section.note && <p className="section-note">{section.note}</p>}
                {section.entries.length === 0 ? (
                  <p className="empty"><span className="status UNKNOWN">UNKNOWN</span> 검토된 항목이 없습니다.</p>
                ) : (
                  section.entries.map((entry) => (
                    <article className="claim" key={entry.id}>
                      {entry.epistemic_status && (
                        <span className={`status ${entry.epistemic_status}`}>
                          {entry.epistemic_status}
                        </span>
                      )}
                      {entry.source_conflict && (
                        <div className="conflict-note">
                          <span className="status CONFLICT">SOURCE CONFLICT</span>
                          <span>서로 다른 근거가 상충하며 자동으로 어느 한쪽을 진실로 판정하지 않습니다.</span>
                        </div>
                      )}
                      <p>{entry.title}</p>
                      {entry.date && <small>Date {entry.date}</small>}
                      {typeof entry.details.resolution_note === "string" && entry.details.resolution_note && (
                        <p className="resolution">{entry.details.resolution_note}</p>
                      )}
                      {entry.evidence && entry.evidence.length > 0 ? (
                        <div className="evidence-list">
                          <strong>Evidence trace</strong>
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
                  ))
                )}
              </section>
            ))}
          </div>
        </>
      ) : (
        <p className="empty"><span className="status UNKNOWN">UNKNOWN</span> Profile projection unavailable.</p>
      )}

      <section>
        <h2>Evidence & audit</h2>
        {sources.length === 0 && <p className="empty">No source cards available.</p>}
        {sources.map((source) => (
          <article className="source" id={`source-${source.id}`} key={source.id}>
            <h3><a href={source.url} target="_blank" rel="noreferrer">{source.title}</a></h3>
            <p>{source.publisher} · {source.policy.source_class}</p>
            <p>License: {source.policy.license ?? "License not specified"}</p>
            {source.policy_summary && (
              <div className="policy-summary">
                <span>Collection {source.policy_summary.collection}</span>
                <span>Metadata {source.policy_summary.metadata_storage}</span>
                <span>Fulltext {source.policy_summary.fulltext_storage}</span>
                <span>Excerpt {source.policy_summary.excerpt_display}</span>
              </div>
            )}
            <details className="audit-details">
              <summary>Source audit</summary>
              <small>Source {source.id}<br />URL {source.url}<br />Policy mode {source.policy.collection_mode}</small>
            </details>
          </article>
        ))}
      </section>
    </>
  );
}

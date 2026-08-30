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
                      <p>{entry.title}</p>
                      <small>
                        {entry.date && <>Date {entry.date}<br /></>}
                        {entry.claim_id && <>Claim {entry.claim_id}<br /></>}
                        {entry.evidence_ids.length > 0 && (
                          <>Evidence {entry.evidence_ids.join(", ")}<br /></>
                        )}
                        {entry.source_ids.map((sourceId) => (
                          <span key={sourceId}>
                            <Link href={`#source-${sourceId}`}>Source {sourceId}</Link><br />
                          </span>
                        ))}
                      </small>
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
            <h3><a href={source.url}>{source.title}</a></h3>
            <p>{source.publisher} · {source.policy.source_class} · {source.policy.license ?? "License unknown"}</p>
            <small>Source {source.id}</small>
          </article>
        ))}
      </section>
    </>
  );
}

import Link from "next/link";

import { getReviewReport } from "../../data";

export const dynamic = "force-dynamic";

export default async function ReviewPage() {
  const report = await getReviewReport();

  return (
    <>
      <Link href="/" className="back">← Roster</Link>
      <div className="eyebrow">Identity review</div>
      <h1>Review queue</h1>
      <p className="lede">Read-only provenance for observations that did not pass automatic materialization.</p>
      <aside className="review-intro">
        <strong>Read-only surface</strong>
        <span>No approval, merge, or publication action is available here.</span>
      </aside>
      {!report ? (
        <p className="empty">Review data is unavailable.</p>
      ) : report.review_items.length === 0 ? (
        <p className="empty">No identity review items are recorded.</p>
      ) : (
        <section className="review-grid">
          {report.review_items.map((item) => {
            const source = item.provenance?.source;
            const candidate = item.candidate_person;
            return (
              <article className="review-item" key={item.id}>
                <div className="review-badges">
                  <span className={`status ${item.action ?? "REVIEW"}`}>{item.action ?? "REVIEW"}</span>
                  <span className={`status ${item.status}`}>{item.status}</span>
                </div>
                <h2>{item.reason_code}</h2>
                {item.reasons.length > 0 && <p>{item.reasons.join(" · ")}</p>}
                {item.observation && (
                  <dl className="review-facts">
                    <div><dt>Feeder</dt><dd>{item.observation.feeder}</dd></div>
                    <div><dt>Scope</dt><dd>{item.observation.semantic_scope} · {item.observation.scope_key}</dd></div>
                    <div><dt>Provider record</dt><dd>{item.observation.provider_record_key}</dd></div>
                  </dl>
                )}
                {candidate && (
                  <p>
                    Candidate Person: {candidate.identity_status === "RESOLVED" ? (
                      <Link href={`/people/${candidate.id}`}>{candidate.canonical_name}</Link>
                    ) : candidate.canonical_name}
                  </p>
                )}
                {source && (
                  <div className="review-provenance">
                    <strong>Observation provenance</strong>
                    <a href={source.url} target="_blank" rel="noreferrer">{source.title}</a>
                    <span>{source.publisher} · {source.source_class} · {source.license ?? "License not specified"}</span>
                    <div className="policy-summary">
                      <span>Collection {source.policy_summary.collection}</span>
                      <span>Metadata {source.policy_summary.metadata_storage}</span>
                      <span>Fulltext {source.policy_summary.fulltext_storage}</span>
                      <span>Excerpt {source.policy_summary.excerpt_display}</span>
                    </div>
                  </div>
                )}
                {item.provenance && item.observation && (
                  <details className="audit-details">
                    <summary>Audit provenance</summary>
                    <small>
                      Review item {item.id}<br />
                      Observation {item.observation.id}<br />
                      Run {item.observation.run_id}<br />
                      SourceSnapshot {item.provenance.snapshot.id}<br />
                      Content hash {item.provenance.snapshot.content_hash}
                    </small>
                  </details>
                )}
              </article>
            );
          })}
        </section>
      )}
    </>
  );
}

import Link from "next/link";

import { getReviewReport } from "../../data";
import ReadState from "../../components/read-state";

export const dynamic = "force-dynamic";

export default async function ReviewPage() {
  const reportResult = await getReviewReport();
  const report = reportResult.state === "success" ? reportResult.data : null;

  return (
    <div className="site-page review-page">
      <Link href="/" className="back-link"><span aria-hidden="true">←</span> Roster</Link>
      <header className="review-header">
        <div>
          <div className="eyebrow"><span className="eyebrow-mark" aria-hidden="true">✦</span> Internal surface / Read-only</div>
          <h1>Review queue</h1>
          <p className="profile-lede">자동 materialization을 통과하지 못한 observation의 provenance만 읽습니다.</p>
        </div>
        <div className="review-lock"><span aria-hidden="true">⌁</span><strong>NO WRITE</strong><small>approval / merge / publish unavailable</small></div>
      </header>
      <aside className="review-intro"><strong>Read-only surface</strong><span>No approval, merge, or publication action is available here.</span></aside>
      {!report ? (
        <ReadState error={reportResult.state === "error" ? reportResult.error : { code: "SERVICE_UNAVAILABLE", message: "Unavailable", request_id: null }} />
      ) : (
        <>
          <div className="review-metrics" aria-label="Review queue summary">
            <div><span className="micro-label">Open items</span><strong>{report.review_items.filter((item) => item.status === "OPEN").length}</strong></div>
            <div><span className="micro-label">Contradictions</span><strong>{report.contradictions.length}</strong></div>
            <div><span className="micro-label">Policy blocks</span><strong>{report.source_policy_blocks.length}</strong></div>
          </div>
          {report.review_items.length === 0 ? (
            <p className="empty-state"><span className="empty-state-mark" aria-hidden="true">∅</span><span><strong>No identity review items are recorded.</strong><small>Nothing is waiting in this read-only projection.</small></span></p>
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
                      <p>Candidate Person: {candidate.identity_status === "RESOLVED" ? <Link href={`/people/${candidate.id}`}>{candidate.canonical_name}</Link> : candidate.canonical_name}</p>
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
      )}
    </div>
  );
}

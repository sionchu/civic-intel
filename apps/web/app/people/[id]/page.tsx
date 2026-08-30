import Link from "next/link";
import { notFound } from "next/navigation";
import { getPerson, getSource } from "../../data";

export const dynamic = "force-dynamic";

export default async function PersonPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const person = await getPerson(id);
  if (!person) notFound();
  const sourceIds = [...new Set((person.claims ?? []).flatMap((claim) => claim.source_ids))];
  const sources = (await Promise.all(sourceIds.map(getSource))).filter((item) => item !== null);
  return <><Link href="/" className="back">← Roster</Link><div className="eyebrow">Canonical profile</div><h1>{person.canonical_name}</h1><span className={`status identity ${person.identity_status}`}>Identity: {person.identity_status}</span><div className="profile"><section><h2>Quick facts & timeline</h2>{(person.claims ?? []).map((claim) => <article className="claim" key={claim.id}><span className={`status ${claim.epistemic_status}`}>{claim.epistemic_status}</span><p>{claim.proposition}</p>{claim.resolution_note && <p className="resolution"><strong>Unresolved:</strong> {claim.resolution_note}</p>}<small>Publication: {claim.publication_status} · Asserted as true: {claim.asserted_as_true ? "yes" : "no"}<br/>Claim {claim.id}</small>{claim.evidence.map((evidence) => <blockquote key={evidence.id}><strong>{evidence.stance}</strong> · {evidence.excerpt ?? "Metadata-only evidence"}<br/><Link href={`#source-${evidence.source_id}`}>Source {evidence.source_id}</Link></blockquote>)}</article>)}</section><aside><section><h2>Assets</h2><p className="empty"><span className="status UNKNOWN">UNKNOWN</span> No publishable disclosure in this fixture.</p></section><section><h2>Relationships</h2><p className="empty"><span className="status UNKNOWN">UNKNOWN</span> No strong relationship asserted.</p></section></aside></div><section><h2>Evidence & audit</h2>{sources.map((source) => <article className="source" id={`source-${source.id}`} key={source.id}><h3><a href={source.url}>{source.title}</a></h3><p>{source.publisher} · {source.policy.source_class} · {source.policy.license ?? "License unknown"}</p><small>Source {source.id}</small></article>)}</section></>;
}

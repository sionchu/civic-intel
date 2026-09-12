import Link from "next/link";
import { getPeople } from "./data";

export const dynamic = "force-dynamic";

export default async function RosterPage() {
  const people = await getPeople();
  return <><div className="eyebrow">Public roster</div><h1>People</h1><p className="lede">Only resolved canonical identities appear here. Profiles remain tied to published evidence.</p><section className="grid">{people.length === 0 ? <p className="empty">No resolved public identities are available.</p> : people.map((person) => <Link className="card" href={`/people/${person.id}`} key={person.id}><span className="status identity RESOLVED">RESOLVED</span><h2>{person.canonical_name}</h2><span>Open evidence profile →</span></Link>)}</section></>;
}

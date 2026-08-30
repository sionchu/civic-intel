import Link from "next/link";
import { getPeople } from "./data";

export const dynamic = "force-dynamic";

export default async function RosterPage() {
  const people = await getPeople();
  return <><div className="eyebrow">Public roster</div><h1>People</h1><p className="lede">Profiles are published only when identity and evidence gates pass.</p><section className="grid">{people.map((person) => <Link className="card" href={`/people/${person.id}`} key={person.id}><span className={`status identity ${person.identity_status}`}>{person.identity_status}</span><h2>{person.canonical_name}</h2><span>Open evidence profile →</span></Link>)}</section></>;
}

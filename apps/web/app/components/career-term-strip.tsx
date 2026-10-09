import type { Claim, ProfileEntry } from "../types";

function dateTime(value: string | undefined): number | null {
  if (!value || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return null;
  const time = Date.parse(`${value}T00:00:00Z`);
  return Number.isFinite(time) && new Date(time).toISOString().slice(0, 10) === value ? time : null;
}

export default function CareerTermStrip({ entries, claims }: {
  entries: ProfileEntry[];
  claims: Claim[];
}) {
  const claimById = new Map(claims.map((claim) => [claim.id, claim]));
  const terms = entries.flatMap((entry) => {
    const claim = entry.claim_id ? claimById.get(entry.claim_id) : undefined;
    if (!claim || (claim.predicate !== "ASSEMBLY_HISTORICAL_TERM" &&
      !(claim.predicate === "HELD_ROLE" && /^제22대(?:\s|$)/.test(claim.object_text)))) return [];
    const start = dateTime(claim.qualifiers.term_start);
    const end = dateTime(claim.qualifiers.term_end);
    const party = claim.qualifiers.party;
    // Historical term text already names the party ("제18대 한나라당 부산 중구동구").
    const label = party && !claim.object_text.includes(party) ? `${claim.object_text} · ${party}` : claim.object_text;
    return [{ entry, claim, label, start, end }];
  });
  if (terms.length === 0) return null;

  const dated = terms.filter((term) => term.start !== null && term.end !== null && term.end >= term.start);
  const undated = terms.filter((term) => !dated.includes(term));
  const axisStart = dated.length ? Math.min(...dated.map((term) => term.start!)) : 0;
  const axisEnd = dated.length ? Math.max(...dated.map((term) => term.end!)) : 0;
  const span = Math.max(1, axisEnd - axisStart);
  const firstYear = dated.length ? new Date(axisStart).getUTCFullYear() : 0;
  const lastYear = dated.length ? new Date(axisEnd).getUTCFullYear() : 0;

  return (
    <div className="career-term-strip" aria-label="국회의원 임기 기간">
      {dated.length > 0 && (
        <>
          <div className="career-term-axis" aria-hidden="true"><span>{firstYear}</span><span>{lastYear}</span></div>
          <ol className="career-term-rows">
            {dated.map((term) => (
              <li key={term.entry.id}>
                <a href={`#claim-${term.claim.id}`}>
                  <span className="career-term-label">{term.label}</span>
                  <span className="career-term-track" role="img" aria-label={`${term.label}: ${term.claim.qualifiers.term_start} ~ ${term.claim.qualifiers.term_end}`}>
                    <span className="career-term-bar" style={{ left: `${(term.start! - axisStart) / span * 100}%`, width: `${Math.max(1, (term.end! - term.start!) / span * 100)}%` }} />
                  </span>
                  <span className="career-term-dates">{term.claim.qualifiers.term_start} ~ {term.claim.qualifiers.term_end}</span>
                </a>
              </li>
            ))}
          </ol>
        </>
      )}
      {undated.length > 0 && (
        <ul className="career-term-undated">
          {undated.map((term) => <li key={term.entry.id}><a href={`#claim-${term.claim.id}`}>{term.label}</a> · 날짜 미기재</li>)}
        </ul>
      )}
    </div>
  );
}

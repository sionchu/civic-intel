// One bounded public read shared by the page, exporter and D1 replay transport.
export const PERSON_RELATIONSHIP_QUERY = "include_candidates=false&limit_per_via=3";

export function personRelationshipPath(id) {
  return `/relationships/people/${id}?${PERSON_RELATIONSHIP_QUERY}`;
}

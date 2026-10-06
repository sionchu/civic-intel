// The public-hosting boundary shared by every Sites artifact (static bundle, Worker build and D1
// projection). Anything that leaves the Mac for Sites hosting is scanned with this and fails closed.
export const FORBIDDEN_TOKENS = [
  "TEL_NO", "E_MAIL", "normalized_payload", "raw_payload", "railway.internal",
  "X-Civic-Operator-Token", "CIVIC_OPERATOR", "DATABASE_URL", "postgresql://", "postgresql+psycopg",
];
export const EMAIL = /[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}/;

// Returns the first forbidden token (including the private API origin) found in `text`, or null.
export function forbiddenToken(text, apiOrigin) {
  return [apiOrigin, ...FORBIDDEN_TOKENS].filter(Boolean).find((token) => text.includes(token)) ?? null;
}

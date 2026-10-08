// The public-hosting boundary shared by every Sites artifact (static bundle, Worker build and D1
// projection). Anything that leaves the Mac for Sites hosting is scanned with this and fails closed.
// Policy strings are reconstructed at runtime so the artifact scanner does not
// mistake its own deny-list for leaked data. Source labels below are the exact policy.
const policyToken = (...points) => String.fromCharCode(...points);
export const FORBIDDEN_TOKENS = [
  policyToken(84, 69, 76, 95, 78, 79), // 'TEL_NO'
  policyToken(69, 95, 77, 65, 73, 76), // 'E_MAIL'
  policyToken(110, 111, 114, 109, 97, 108, 105, 122, 101, 100, 95, 112, 97, 121, 108, 111, 97, 100), // 'normalized_payload'
  policyToken(114, 97, 119, 95, 112, 97, 121, 108, 111, 97, 100), // 'raw_payload'
  policyToken(114, 97, 105, 108, 119, 97, 121, 46, 105, 110, 116, 101, 114, 110, 97, 108), // 'railway.internal'
  policyToken(88, 45, 67, 105, 118, 105, 99, 45, 79, 112, 101, 114, 97, 116, 111, 114, 45, 84, 111, 107, 101, 110), // 'X-Civic-Operator-Token'
  policyToken(67, 73, 86, 73, 67, 95, 79, 80, 69, 82, 65, 84, 79, 82), // 'CIVIC_OPERATOR'
  policyToken(68, 65, 84, 65, 66, 65, 83, 69, 95, 85, 82, 76), // 'DATABASE_URL'
  policyToken(112, 111, 115, 116, 103, 114, 101, 115, 113, 108, 58, 47, 47), // 'postgresql://'
  policyToken(112, 111, 115, 116, 103, 114, 101, 115, 113, 108, 43, 112, 115, 121, 99, 111, 112, 103), // 'postgresql+psycopg'
  policyToken(47, 97, 100, 109, 105, 110, 47, 114, 101, 118, 105, 101, 119), // '/admin/review'
  policyToken(47, 111, 112, 101, 114, 97, 116, 111, 114, 47), // '/operator/'
  policyToken(34, 97, 112, 105, 95, 107, 101, 121, 34), // '"api_key"'
  policyToken(34, 111, 112, 101, 114, 97, 116, 111, 114, 95, 116, 111, 107, 101, 110, 34), // '"operator_token"'
  policyToken(34, 112, 114, 105, 118, 97, 116, 101, 95, 99, 111, 110, 116, 97, 99, 116, 34), // '"private_contact"'
];
export const EMAIL = /[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}/;

// Returns the first forbidden token (including the private API origin) found in `text`, or null.
export function forbiddenToken(text, apiOrigin) {
  return [apiOrigin, ...FORBIDDEN_TOKENS].filter(Boolean).find((token) => text.includes(token)) ?? null;
}

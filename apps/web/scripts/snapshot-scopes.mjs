import { PERSON_RELATIONSHIP_QUERY } from '../app/relationship-path.mjs';
const UUID = '[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}';
const MONEY_QUERY = 'earlier_fiscal_year=2024&later_fiscal_year=2025';
export const SCOPES = [
  `^/people/${UUID}$`, `^/ontology/people/${UUID}$`,
  `^/relationships/people/${UUID}\\?${PERSON_RELATIONSHIP_QUERY.replace(/[?&]/g, '\\$&')}$`,
  `^/organizations/${UUID}$`, `^/ontology/organizations/${UUID}$`,
  `^/organizations/${UUID}/money\\?${MONEY_QUERY.replace(/[?&]/g, '\\$&')}$`,
  `^/sources/${UUID}$`,
];

export type Status = "FACT" | "CLAIM" | "INFERENCE" | "HYPOTHESIS" | "UNKNOWN" | "ENTITY_UNRESOLVED";
export type ProfileSectionStatus = "AVAILABLE" | "PARTIAL" | "UNKNOWN";

export type ApiErrorCode =
  | "PUBLIC_RECORD_NOT_FOUND"
  | "INSUFFICIENT_ELIGIBLE_INPUTS"
  | "SOURCE_VERSION_CONFLICT"
  | "ACCESS_DENIED"
  | "INVALID_INPUT"
  | "SERVICE_UNAVAILABLE";

export type ApiError = {
  code: ApiErrorCode;
  message: string;
  request_id: string | null;
};

export type ApiResult<T> =
  | { state: "success"; data: T }
  | { state: "error"; error: ApiError };

export type Evidence = {
  id: string;
  source_id: string;
  snapshot_id: string | null;
  feeder_observation_id: string | null;
  stance: "SUPPORT" | "REFUTE" | "NEUTRAL";
  excerpt: string | null;
};

export type EvidenceTrace = {
  id: string;
  stance: "SUPPORT" | "REFUTE" | "NEUTRAL";
  source_id: string;
  snapshot_id: string | null;
  feeder_observation_id: string | null;
};

export type Claim = {
  id: string;
  person_id?: string | null;
  organization_id?: string | null;
  proposition: string;
  subject: string;
  predicate: string;
  object_text: string;
  epistemic_status: Status;
  publication_status: "DRAFT" | "REVIEW" | "PUBLISHED" | "WITHHELD";
  asserted_as_true: boolean;
  resolution_note: string | null;
  qualifiers: Record<string, string>;
  evidence: Evidence[];
  source_ids: string[];
};

export type Organization = {
  id: string;
  name: string;
  valid_from: string;
  valid_to: string | null;
  recorded_at: string;
  superseded_at: string | null;
  claims: Claim[];
};

export type OrganizationSummary = {
  id: string;
  name: string;
  classification: string | null;
  classification_code: string | null;
  executive_count: number;
  published_claim_count: number;
  as_of: string | null;
  evidence_count: number;
};

export type MoneyInput = {
  fiscal_year: number;
  amount_thousand_krw: number;
  amount_krw: number;
  report_period: string;
  as_of_date: string;
  submission_date: string;
  disclosure_no: string;
  observation_id: string;
  snapshot_id: string;
  source_id: string;
  claim_id?: string;
  evidence_ids?: string[];
};

export type MoneyProjection = {
  id: string;
  kind: "MONEY";
  method_version: string;
  availability: "AVAILABLE";
  epistemic_status: null;
  claim_ids: string[];
  evidence_ids: string[];
  evidence: Evidence[];
  source_ids: string[];
  snapshot_ids: string[];
  observation_ids: string[];
  details: {
    organization: {
      id: string;
      name: string;
      code: string;
      role_scope: string;
    };
    earlier: MoneyInput;
    later: MoneyInput;
    absolute_delta_krw: number;
    percent_change: string | null;
    coverage: {
      input_claim_count: number;
      compared_fiscal_years: number[];
      semantic_scope: string;
    };
    limitations: string[];
    input_scope: {
      source_contract: string;
      required_publication: string;
      correction_semantics: string;
      identity_rule: string;
    };
  };
};

export type ProfileEntry = {
  id: string;
  kind: "IDENTITY" | "CLAIM" | "CHANGE" | "DECISION_EPISODE" | "RELATIONSHIP" | "LIMITATION";
  title: string;
  epistemic_status: Status | null;
  claim_id: string | null;
  evidence_ids: string[];
  source_ids: string[];
  evidence?: EvidenceTrace[];
  source_conflict?: boolean;
  date: string | null;
  details: Record<string, unknown>;
};

export type ProfileSection = {
  id: string;
  label: string;
  status: ProfileSectionStatus;
  note: string | null;
  entries: ProfileEntry[];
};

export type ProfileProjection = {
  profile_kind?: "ASSEMBLY_MEMBER" | "LEGACY_PERSON";
  section_order: string[];
  sections: ProfileSection[];
  coverage: { available: number; partial: number; unknown: number };
  semantics: "DERIVED_READ_MODEL_FROM_CANONICAL_EVIDENCE";
};

export type DiscoveryFacet = {
  value: string;
  claim_id: string;
  evidence_ids: string[];
  source_ids: string[];
  as_of: string;
};

export type PeopleDiscovery = {
  facets: {
    role: DiscoveryFacet | null;
    party: DiscoveryFacet | null;
    district: DiscoveryFacet | null;
    committees: DiscoveryFacet | null;
    reelection: DiscoveryFacet | null;
  };
  as_of: string | null;
  evidence_ids: string[];
  source_ids: string[];
  missing_fields: string[];
  ambiguous_fields: string[];
};

export type Person = {
  id: string;
  canonical_name: string;
  identity_status: "RESOLVED" | "REVIEW" | "UNRESOLVED";
  discovery?: PeopleDiscovery;
  claims?: Claim[];
  profile?: ProfileProjection;
};

export type OntologyNode = {
  id: string;
  kind: "PERSON" | "ORGANIZATION" | "EDUCATIONAL_INSTITUTION" | "COMPANY" | "COMMITTEE" | "OFFICE" | "HEARING" | "ISSUE" | "SOURCE_LISTED_ROLE_HOLDER";
  label: string;
  canonical_id: string | null;
  claim_ids: string[];
};

export type OntologyEdge = {
  id: string;
  source: string;
  target: string;
  relation_type: "HELD_ROLE" | "WORKED_AT" | "STUDIED_AT" | "SERVED_ON" | "DIRECTOR_OF" | "APPOINTED_TO" | "APPEARED_AT" | "QUESTIONED" | "AUDITED_BY" | "LISTS_EXECUTIVE";
  label: string;
  claim_id: string;
  evidence_ids: string[];
  source_ids: string[];
  epistemic_status: Status;
  publication_status: "PUBLISHED";
  source_conflict: boolean;
  valid_from: string | null;
  valid_to: string | null;
};

export type OntologyGraph = {
  center_node_id: string;
  nodes: OntologyNode[];
  edges: OntologyEdge[];
  semantics: "READ_ONLY_PROJECTION_FROM_CANONICAL_CLAIM_EVIDENCE";
  limitations: string[];
};

export type Source = {
  id: string;
  url: string;
  title: string;
  publisher: string;
  published_at: string | null;
  source_class: string;
  license: string | null;
  terms_checked_at: string | null;
  policy_summary: {
    collection: "PERMITTED" | "NOT_PERMITTED";
    metadata_storage: "PERMITTED" | "NOT_PERMITTED";
    fulltext_storage: "PERMITTED" | "NOT_PERMITTED";
    excerpt_display: "PERMITTED" | "NOT_PERMITTED";
  };
};

export type ReviewSource = {
  id: string;
  title: string;
  publisher: string;
  url: string;
  source_class: string;
  license: string | null;
  policy_summary: {
    collection: "PERMITTED" | "NOT_PERMITTED";
    metadata_storage: "PERMITTED" | "NOT_PERMITTED";
    fulltext_storage: "PERMITTED" | "NOT_PERMITTED";
    excerpt_display: "PERMITTED" | "NOT_PERMITTED";
  };
};

export type ReviewItem = {
  id: string;
  status: "OPEN" | "RESOLVED" | "REJECTED";
  action: "REVIEW_REQUIRED" | "HARD_CONFLICT" | null;
  reason_code: string;
  reasons: string[];
  candidate_person: {
    id: string;
    canonical_name: string;
    identity_status: "RESOLVED" | "REVIEW" | "UNRESOLVED";
  } | null;
  observation: {
    id: string;
    feeder: string;
    scope_key: string;
    semantic_scope: string;
    provider_record_key: string;
    run_id: string;
    recorded_at: string;
    provider_observed_at: string | null;
  } | null;
  provenance: {
    source: ReviewSource;
    snapshot: {
      id: string;
      source_id: string;
      fetched_at: string;
      content_hash: string;
    };
  } | null;
  resolution_note: string | null;
};

export type ReviewReport = {
  unresolved_identities: string[];
  unpublishable_claims: string[];
  origin_candidates: string[];
  contradictions: string[];
  source_policy_blocks: string[];
  review_items: ReviewItem[];
};

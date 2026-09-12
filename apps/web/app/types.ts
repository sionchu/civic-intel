export type Status = "FACT" | "CLAIM" | "INFERENCE" | "HYPOTHESIS" | "UNKNOWN" | "ENTITY_UNRESOLVED";
export type ProfileSectionStatus = "AVAILABLE" | "PARTIAL" | "UNKNOWN";

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
  proposition: string;
  epistemic_status: Status;
  publication_status: "DRAFT" | "REVIEW" | "PUBLISHED" | "WITHHELD";
  asserted_as_true: boolean;
  resolution_note: string | null;
  evidence: Evidence[];
  source_ids: string[];
};

export type ProfileEntry = {
  id: string;
  kind: "IDENTITY" | "CLAIM" | "DECISION_EPISODE" | "RELATIONSHIP" | "LIMITATION";
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
  section_order: string[];
  sections: ProfileSection[];
  coverage: { available: number; partial: number; unknown: number };
  semantics: "DERIVED_READ_MODEL_FROM_CANONICAL_EVIDENCE";
};

export type Person = {
  id: string;
  canonical_name: string;
  identity_status: "RESOLVED" | "REVIEW" | "UNRESOLVED";
  claims?: Claim[];
  profile?: ProfileProjection;
};

export type Source = {
  id: string;
  url: string;
  title: string;
  publisher: string;
  policy: {
    source_class: string;
    collection_mode: string;
    license: string | null;
    can_fetch: boolean;
    can_store_metadata: boolean;
    can_store_fulltext: boolean;
    can_show_excerpt: boolean;
  };
  policy_summary?: {
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

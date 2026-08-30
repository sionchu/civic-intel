export type Status = "FACT" | "CLAIM" | "INFERENCE" | "HYPOTHESIS" | "UNKNOWN" | "ENTITY_UNRESOLVED";
export type ProfileSectionStatus = "AVAILABLE" | "PARTIAL" | "UNKNOWN";

export type Evidence = {
  id: string;
  source_id: string;
  stance: "SUPPORT" | "REFUTE" | "NEUTRAL";
  excerpt: string | null;
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
  policy: { source_class: string; license: string | null; can_show_excerpt: boolean };
};

export type Status = "FACT" | "CLAIM" | "INFERENCE" | "HYPOTHESIS" | "UNKNOWN" | "ENTITY_UNRESOLVED";

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
  evidence: Evidence[];
  source_ids: string[];
};

export type Person = {
  id: string;
  canonical_name: string;
  identity_status: "RESOLVED" | "REVIEW" | "UNRESOLVED";
  claims?: Claim[];
};

export type Source = {
  id: string;
  url: string;
  title: string;
  publisher: string;
  policy: { source_class: string; license: string | null; can_show_excerpt: boolean };
};

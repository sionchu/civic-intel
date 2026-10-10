"use client";

import { createContext, useContext, useMemo, type ReactNode } from "react";
import type { Claim, Source } from "../types";

const PersonEvidenceContext = createContext<{ claims: Claim[]; sources: Source[] } | null>(null);
export function usePersonEvidence() { return useContext(PersonEvidenceContext); }
// The same canonical DTO is a single RSC text value, avoiding per-property Flight
// serialization of thousands of nested Claim/Evidence records. It is parsed once for
// the existing consumers; this changes transport representation, never record semantics.
export default function PersonEvidenceProvider({ dataJson, children }: { dataJson: string; children: ReactNode }) {
  const value = useMemo(() => JSON.parse(dataJson) as { claims: Claim[]; sources: Source[] }, [dataJson]);
  return <PersonEvidenceContext.Provider value={value}>{children}</PersonEvidenceContext.Provider>;
}

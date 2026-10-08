"use client";

import { createContext, useContext, useMemo, type ReactNode } from "react";
import type { Claim, Source } from "../types";

const PersonEvidenceContext = createContext<{ claims: Claim[]; sources: Source[] } | null>(null);
export function usePersonEvidence() { return useContext(PersonEvidenceContext); }
export default function PersonEvidenceProvider({ claims, sources, children }: { claims: Claim[]; sources: Source[]; children: ReactNode }) {
  const value = useMemo(() => ({ claims, sources }), [claims, sources]);
  return <PersonEvidenceContext.Provider value={value}>{children}</PersonEvidenceContext.Provider>;
}

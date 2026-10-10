"use client";

import { useEffect, useState } from "react";
import { usePersonEvidence } from "./person-evidence-context";
import EvidencePanel from "./evidence-panel";
import { predicateLabel } from "../predicate-labels";

export default function PersonClaimLibrary({ claimIds, existingClaimIds = [], legislative = false }: { claimIds: string[]; existingClaimIds?: string[]; legislative?: boolean }) {
  const evidence = usePersonEvidence();
  const [query, setQuery] = useState("");
  const [limit, setLimit] = useState(20);
  const [activeId, setActiveId] = useState<string | null>(null);
  const claimById = new Map((evidence?.claims ?? []).map((claim) => [claim.id, claim]));
  const claims = [...new Set(claimIds)].flatMap((id) => { const claim = claimById.get(id); return claim ? [claim] : []; });
  const selected = claims.filter((claim) => !query.trim() || `${claim.object_text ?? ""} ${claim.proposition}`.includes(query.trim()));
  const shown = selected.slice(0, limit);
  const active = claims.find((claim) => claim.id === activeId);
  const cards = active && !shown.some((claim) => claim.id === active.id) ? [...shown, active] : shown;
  const sourceById = new Map((evidence?.sources ?? []).map((source) => [source.id, source]));
  useEffect(() => {
    const reveal = (hash: string) => {
      if (!hash.startsWith("#claim-")) return;
      let id: string;
      try { id = decodeURIComponent(hash.slice(7)); } catch { return; }
      if (!claimIds.includes(id) || existingClaimIds.includes(id)) return;
      setActiveId(id);
    };
    const fromHash = () => reveal(window.location.hash);
    const onClick = (event: MouseEvent) => {
      const href = (event.target as Element | null)?.closest('a[href^="#claim-"]')?.getAttribute("href");
      if (href) reveal(href);
    };
    fromHash(); window.addEventListener("hashchange", fromHash); document.addEventListener("click", onClick);
    return () => { window.removeEventListener("hashchange", fromHash); document.removeEventListener("click", onClick); };
  }, [claimIds, existingClaimIds]);
  useEffect(() => {
    if (!activeId) return;
    const target = document.getElementById(`claim-${activeId}`);
    const disclosure = target?.querySelector<HTMLDetailsElement>(":scope > details.evidence-disclosure");
    if (disclosure) disclosure.open = true;
    if (target) {
      for (let parent = target.parentElement; parent; parent = parent.parentElement) if (parent instanceof HTMLDetailsElement) parent.open = true;
      requestAnimationFrame(() => target.scrollIntoView({ block: "start", behavior: "instant" }));
    }
  }, [activeId, limit, query]);
  return <div className="person-claim-library">
    <label>기록 제목<input type="search" value={query} placeholder="제목에 포함된 단어" onChange={(event) => { setQuery(event.target.value); setLimit(20); }} /></label>
    {evidence ? <p className="section-note" role="status" aria-live="polite">검색 결과 {selected.length.toLocaleString("ko-KR")}건 / 연결된 공개 기록 {claims.length.toLocaleString("ko-KR")}건 · 현재 {cards.length.toLocaleString("ko-KR")}건 표시</p> : <p className="section-note" role="status">공개 기록 범위 미확인</p>}
    {evidence && new Set(claimIds).size !== claims.length && <p className="empty-note">일부 근거 기록을 확인하지 못했습니다. 표시된 목록이 전체 기록을 뜻하지 않습니다.</p>}
    {!evidence && <p className="empty-note">기록을 확인할 수 없습니다. 실제 기록이 없다는 뜻은 아닙니다.</p>}
    {evidence && selected.length === 0 && <p className="empty-note">제목에 맞는 공개 기록이 없습니다.</p>}
    {cards.map((claim) => existingClaimIds.includes(claim.id) ? <p key={claim.id}><a href={`#claim-${claim.id}`}>{claim.object_text ?? claim.proposition} · 근거 기록 열기</a></p> : <EvidencePanel key={claim.id} claim={claim} sourceById={sourceById} title={legislative ? claim.object_text ?? claim.proposition : undefined} kind={legislative ? "공식 법안 기록" : predicateLabel(claim.predicate)} />)}
    {selected.length > limit && <button className="load-more" type="button" onClick={() => setLimit(limit + 20)}>기록 더 보기</button>}
  </div>;
}

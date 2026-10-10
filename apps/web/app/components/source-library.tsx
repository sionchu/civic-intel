"use client";

import { useEffect, useState } from "react";
import { usePersonEvidence } from "./person-evidence-context";
import { SourceCard } from "./evidence-panel";
import type { Source } from "../types";

const EMPTY_SOURCES: Source[] = [];

export default function SourceLibrary({ sources: providedSources }: { sources?: Source[] }) {
  const shared = usePersonEvidence();
  const available = providedSources !== undefined || shared !== null;
  const sources = providedSources ?? shared?.sources ?? EMPTY_SOURCES;
  const [limit, setLimit] = useState(20);
  const [activeId, setActiveId] = useState<string | null>(null);
  const shown = sources.slice(0, limit);
  const active = sources.find((source) => source.id === activeId);
  const cards = active && !shown.some((source) => source.id === active.id) ? [...shown, active] : shown;
  useEffect(() => {
    const scroll = (id: string) => {
      const target = document.getElementById(`source-${id}`);
      target?.scrollIntoView({ block: "start", behavior: "instant" });
    };
    const reveal = (hash: string) => {
      if (!hash.startsWith("#source-")) return;
      let id: string;
      try { id = decodeURIComponent(hash.slice(8)); } catch { return; }
      if (!sources.some((source) => source.id === id)) return;
      setActiveId(id);
      requestAnimationFrame(() => scroll(id));
    };
    const fromHash = () => reveal(window.location.hash);
    const onClick = (event: MouseEvent) => {
      const href = (event.target as Element | null)?.closest('a[href^="#source-"]')?.getAttribute("href");
      if (href) setTimeout(() => reveal(href), 0);
    };
    fromHash(); window.addEventListener("hashchange", fromHash); document.addEventListener("click", onClick);
    return () => { window.removeEventListener("hashchange", fromHash); document.removeEventListener("click", onClick); };
  }, [sources]);
  useEffect(() => {
    if (activeId) requestAnimationFrame(() => document.getElementById(`source-${activeId}`)?.scrollIntoView({ block: "start", behavior: "instant" }));
  }, [activeId, limit]);
  return <>
    {available ? <p className="section-note" role="status" aria-live="polite">연결된 출처 {sources.length.toLocaleString("ko-KR")}건 · 현재 {cards.length.toLocaleString("ko-KR")}건 표시</p> : <p className="section-note" role="status">연결된 출처 범위 미확인</p>}
    <div className="source-grid">{cards.map((source) => <SourceCard key={source.id} source={source} />)}</div>
    {shown.length < sources.length && <button className="load-more" type="button" onClick={() => setLimit(limit + 20)}>출처 더 보기</button>}
  </>;
}

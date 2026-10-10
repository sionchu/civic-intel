"use client";

import { useEffect } from "react";

// Native <details> cannot open from :target, so open the evidence disclosure that the URL hash
// (or a clicked in-page anchor) names.
function openById(rawId: string) {
  let id: string;
  try { id = decodeURIComponent(rawId); } catch { return; }
  const target = id ? document.getElementById(id) : null;
  const disclosure = target?.querySelector<HTMLDetailsElement>(":scope > details.evidence-disclosure");
  if (!target || !disclosure) return;
  // Evidence can be inside the collapsed supplementary record list.
  for (let parent = target.parentElement; parent; parent = parent.parentElement) {
    if (parent instanceof HTMLDetailsElement) parent.open = true;
  }
  disclosure.open = true;
  requestAnimationFrame(() => target.scrollIntoView({ block: "start" }));
}

export default function OpenTargetDetails() {
  useEffect(() => {
    const fromHash = () => openById(window.location.hash.slice(1));
    // Same-page <Link> hash navigation uses pushState, which fires no hashchange.
    const onClick = (event: MouseEvent) => {
      const href = (event.target as Element | null)?.closest('a[href^="#"]')?.getAttribute("href");
      if (href) setTimeout(() => openById(href.slice(1)), 0);
    };
    fromHash();
    window.addEventListener("hashchange", fromHash);
    document.addEventListener("click", onClick);
    return () => {
      window.removeEventListener("hashchange", fromHash);
      document.removeEventListener("click", onClick);
    };
  }, []);
  return null;
}

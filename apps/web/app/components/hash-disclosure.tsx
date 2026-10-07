"use client";

import { useEffect } from "react";

// Opens the closed <details> ancestors of the URL-hash target so a deep link such as
// #witness-{claim_id} lands on a visible row. Renders nothing; it adds no state of its own.
export default function HashDisclosure({ prefix }: { prefix: string }) {
  useEffect(() => {
    function reveal() {
      const id = decodeURIComponent(window.location.hash.slice(1));
      if (!id.startsWith(prefix)) return;
      const target = document.getElementById(id);
      if (!target) return;
      for (let node = target.parentElement; node; node = node.parentElement) {
        if (node instanceof HTMLDetailsElement) node.open = true;
      }
      target.scrollIntoView({ block: "start" });
    }
    reveal();
    window.addEventListener("hashchange", reveal);
    return () => window.removeEventListener("hashchange", reveal);
  }, [prefix]);
  return null;
}

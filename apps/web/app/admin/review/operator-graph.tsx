"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import type { Core } from "cytoscape";
import { FIELD_LABELS, KIND_LABELS, fieldText, type OperatorDetail, type OperatorGraph } from "./operator-types";

const NODE_LABELS: Record<string, string> = { ...KIND_LABELS, OFFICE: "직책 기록", SOURCE_LISTED_ROLE_HOLDER: "공시상 임원 기록" };

export default function OperatorGraphView({ detail, contextQuery }: { detail: OperatorDetail; contextQuery: string }) {
  const container = useRef<HTMLDivElement>(null);
  const graphApi = useRef<Core | null>(null);
  const [selectedId, setSelectedId] = useState(detail.graph.center);
  const [loadError, setLoadError] = useState(false);
  const selected = detail.graph.nodes.find((node) => node.id === selectedId) ?? detail.graph.nodes[0];
  const publicRelations = detail.graph.semantics === "PUBLIC_CANONICAL_CLAIM_EVIDENCE_RELATIONS";
  const params = new URLSearchParams(contextQuery);
  if (selected) { params.set("focus_kind", selected.inspect_kind ?? selected.kind); params.set("focus_id", selected.inspect_id ?? selected.record_id); params.set("view", "lineage"); }

  useEffect(() => {
    let disposed = false;
    let observer: ResizeObserver | undefined;
    import("cytoscape").then(({ default: cytoscape }) => {
      if (disposed || !container.current) return;
      const css = getComputedStyle(container.current);
      const ink = css.getPropertyValue("--color-ink").trim() || "#183331";
      const accent = css.getPropertyValue("--color-accent").trim() || "#166658";
      const line = css.getPropertyValue("--color-line-strong").trim() || "#93aaa0";
      const cy = cytoscape({ container: container.current,
        elements: [
          ...detail.graph.nodes.map((node) => ({ data: { ...node, caption: `${NODE_LABELS[node.kind] ?? node.kind}\n${node.label.slice(0, 24)}` } })),
          ...detail.graph.edges.map((edge) => ({ data: edge, classes: edge.review_only ? "review-edge" : "" })),
        ],
        layout: { name: "breadthfirst", directed: false, roots: [detail.graph.center], animate: false, padding: 35, spacingFactor: 1.25 },
        minZoom: 0.15, maxZoom: 2.5, wheelSensitivity: 0.18, autoungrabify: true,
        style: [
          { selector: "node", style: { "background-color": accent, "label": "data(caption)", "color": ink,
            "font-size": 12, "text-wrap": "wrap", "text-max-width": "145px", "text-valign": "bottom",
            "text-margin-y": 9, "width": 24, "height": 24, "border-width": 2, "border-color": "#ffffff" } },
          { selector: 'node[kind = "claims"]', style: { "shape": "round-rectangle", "background-color": "#45667d" } },
          { selector: 'node[kind = "observations"]', style: { "shape": "diamond", "background-color": "#967143" } },
          { selector: 'node[kind = "sources"], node[kind = "snapshots"], node[kind = "policies"]', style: { "background-color": "#76746d" } },
          { selector: "edge", style: { "width": 1.3, "line-color": line, "target-arrow-color": line,
            "target-arrow-shape": "triangle", "curve-style": "bezier", "arrow-scale": 0.7 } },
          { selector: ".review-edge", style: { "line-style": "dashed" } },
          { selector: ".dimmed", style: { "opacity": 0.16 } },
          { selector: ":selected", style: { "border-color": ink, "border-width": 4 } },
          { selector: "edge:selected", style: { "label": "data(label)", "font-size": 12, "color": ink, "width": 3 } },
        ],
      });
      graphApi.current = cy;
      cy.on("tap", "node", (event) => {
        setSelectedId(event.target.id());
        cy.elements().addClass("dimmed");
        event.target.closedNeighborhood().removeClass("dimmed");
      });
      cy.on("tap", (event) => { if (event.target === cy) cy.elements().removeClass("dimmed"); });
      observer = new ResizeObserver(() => cy.resize());
      observer.observe(container.current);
    }).catch(() => { if (!disposed) setLoadError(true); });
    return () => { disposed = true; observer?.disconnect(); graphApi.current?.destroy(); graphApi.current = null; };
  }, [detail]);

  function downloadGraph(graph: OperatorGraph) {
    const url = URL.createObjectURL(new Blob([JSON.stringify({ scope: "SELECTED_BOUNDED_LINEAGE", ...graph }, null, 2)], { type: "application/json" }));
    const anchor = document.createElement("a"); anchor.href = url; anchor.download = "civic-selected-lineage.json"; anchor.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  return <section className="operator-graph-panel" aria-label="선택 기록 연결과 근거">
    <div className="operator-section-head"><div><span className="micro-label">{publicRelations ? "PUBLISHED RELATIONS" : "DATABASE LINEAGE"}</span><h2>{detail.record.label}</h2></div>
      <span className="operator-tag">{detail.record.status}</span></div>
    <p className="operator-note">{publicRelations ? "기존 공개 온톨로지의 직책·ALIO 임원 공시 관계입니다. 출처 기록 노드는 canonical Person이 아니며 같은 이름을 합치지 않습니다." : "실선: 저장된 참조 · 점선: 검토 후보. 선은 원본 DB 참조 방향이며 사회적 관계를 뜻하지 않습니다."}</p>
    <div className="operator-toolbar" aria-label="연결 지도 조작">
      <button type="button" onClick={() => graphApi.current?.zoom((graphApi.current?.zoom() ?? 1) * 1.3)}>확대 +</button>
      <button type="button" onClick={() => graphApi.current?.zoom((graphApi.current?.zoom() ?? 1) / 1.3)}>축소 −</button>
      <button type="button" onClick={() => { graphApi.current?.elements().removeClass("dimmed"); graphApi.current?.fit(undefined, 35); }}>전체 맞춤</button>
      <button type="button" onClick={() => downloadGraph(detail.graph)}>현재 지도 JSON</button>
    </div>
    <div ref={container} className="operator-canvas" aria-hidden="true" />
    {publicRelations && detail.graph.edges.length === 0 && <p className="operator-note">현재 지원하는 공개 직책·임원 공시 관계가 없습니다. 수집 기록이나 기관 자체가 없다는 뜻은 아닙니다.</p>}
    {loadError && <p role="alert">시각화 로드 실패. 아래 연결 목록과 근거는 계속 확인할 수 있습니다.</p>}
    <p className="operator-note">{detail.graph.nodes.length}개 노드 · {detail.graph.edges.length}개 참조 · 최대 {detail.graph.max_depth}단계 / {detail.graph.max_nodes}개 노드.
      {detail.graph.truncated ? " 일부 연결은 제한되어 있습니다. 노드를 선택해 중심을 옮기면 이어서 확인할 수 있습니다." : " 현재 선택 범위의 저장된 참조를 표시합니다."}</p>
    {selected && <div className="operator-inspector"><div className="operator-section-head">
      <div><span className="micro-label">{NODE_LABELS[selected.kind] ?? selected.kind}</span><h3>{selected.label}</h3></div>
      <Link href={`/admin/review?${params}`} prefetch={false}>이 기록 중심으로 보기 →</Link></div>
      <dl className="operator-fields"><div><dt>레코드 ID</dt><dd>{selected.record_id || "없음 · 출처 기록 노드"}</dd></div>
        {Object.entries(selected.fields).map(([name, value]) => <div key={name}><dt>{FIELD_LABELS[name] ?? name}</dt>
          <dd>{name === "url" && typeof value === "string" ? <a href={value} target="_blank" rel="noreferrer">공식 출처 열기 ↗</a> : fieldText(value)}</dd></div>)}
      </dl></div>}
    <details className="operator-text-graph"><summary>키보드용 노드·연결 목록 ({detail.graph.nodes.length})</summary>
      <div className="operator-node-list">{detail.graph.nodes.map((node) => <button key={node.id} type="button" aria-pressed={selectedId === node.id}
        onClick={() => setSelectedId(node.id)}>{NODE_LABELS[node.kind] ?? node.kind} · {node.label}</button>)}</div>
      <ul>{detail.graph.edges.map((edge) => <li key={edge.id}>
        {detail.graph.nodes.find((node) => node.id === edge.source)?.label} → <strong>{edge.label}</strong> → {detail.graph.nodes.find((node) => node.id === edge.target)?.label}
      </li>)}</ul></details>
  </section>;
}

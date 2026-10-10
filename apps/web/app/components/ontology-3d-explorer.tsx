"use client";

import { useEffect, useId, useRef, useState, type ReactNode } from "react";

import { relationLabel, statusLabel } from "../display-labels";
import type { NodeObject, LinkObject, ForceGraph3DInstance } from "3d-force-graph";
import type { OntologyEdge, OntologyGraph, OntologyNode } from "../types";

type BoundedGraph = Pick<OntologyGraph, "center_node_id" | "nodes" | "edges">;
interface RenderNode extends NodeObject {
  id: string;
  name: string;
  kind: OntologyNode["kind"];
}
interface RenderLink extends LinkObject<RenderNode> {
  id: string;
  relation_type: OntologyEdge["relation_type"];
}

function escapeLabel(label: string): string {
  return label.replace(/[&<>"']/g, (value) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[value] ?? value);
}

function supportedWebGL(): boolean {
  try {
    const canvas = document.createElement("canvas");
    return Boolean(canvas.getContext("webgl2") || canvas.getContext("webgl"));
  } catch {
    return false;
  }
}

export default function Ontology3DExplorer({
  graph,
  totalEdges,
  children,
}: {
  graph: BoundedGraph;
  totalEdges: number;
  children: ReactNode;
}) {
  const [mode, setMode] = useState<"diagram" | "spatial">("diagram");
  const [renderState, setRenderState] = useState<"loading" | "ready" | "unavailable">("loading");
  const [selectedNodeId, setSelectedNodeId] = useState(graph.center_node_id);
  const mountRef = useRef<HTMLDivElement>(null);
  const selectId = useId();

  useEffect(() => {
    if (mode !== "spatial") return;
    let disposed = false;
    let disposeGraph: (() => void) | undefined;
    let observer: ResizeObserver | undefined;

    async function mount() {
      setRenderState("loading");
      if (!supportedWebGL()) {
        setRenderState("unavailable");
        return;
      }
      const { default: ForceGraph3D } = await import("3d-force-graph");
      const container = mountRef.current;
      if (disposed || !container) return;

      const tokens = getComputedStyle(document.documentElement);
      const color = (name: string, fallback: string) =>
        tokens.getPropertyValue(name).trim() || fallback;
      const accent = color("--color-accent", "#1d645a");
      const ink = color("--color-ink-muted", "#55645e");
      const surface = color("--color-surface", "#fff");
      const line = color("--color-line-strong", "#7d8791");
      const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

      // Copy the server's bounded public projection: the graph engine mutates coordinates.
      const nodes = graph.nodes.map((node) => ({
        id: node.id,
        name: node.label,
        kind: node.kind,
      }));
      const links = graph.edges.map((edge) => ({
        id: edge.id,
        source: edge.source,
        target: edge.target,
        relation_type: edge.relation_type,
      }));
      // The library constructor exposes its non-generic default types; our payload is bounded and typed.
      const view = new ForceGraph3D(container, { controlType: "orbit" }) as unknown as ForceGraph3DInstance<RenderNode, RenderLink>;
      disposeGraph = () => view._destructor();
      view
        .width(container.clientWidth)
        .height(container.clientHeight)
        .backgroundColor(surface)
        .showNavInfo(false)
        .nodeId("id")
        .nodeVal((node) => node.id === graph.center_node_id ? 18 : 9)
        .nodeColor((node) => node.id === graph.center_node_id ? accent : ink)
        .nodeLabel((node) => escapeLabel(String(node.name ?? "")))
        .linkColor(() => line)
        .linkWidth(1.3)
        .linkOpacity(0.55)
        .cooldownTicks(60)
        .onEngineStop(() => view.zoomToFit(reducedMotion ? 0 : 250, 80))
        .linkLabel((link) => escapeLabel(relationLabel(String(link.relation_type))))
        .onNodeClick((node) => setSelectedNodeId(String(node.id)))
        .onLinkClick((link) => {
          const target = link.target;
          const id = typeof target === "object" && target !== null ? target.id : target;
          if (id !== undefined) setSelectedNodeId(String(id));
        })
        .graphData({ nodes, links });
      view.cameraPosition({ z: 180 });
      if (disposed) {
        view._destructor();
        return;
      }
      if (typeof ResizeObserver !== "undefined") {
        observer = new ResizeObserver(() => {
          if (container.clientWidth > 0) {
            view.width(container.clientWidth).height(container.clientHeight);
          }
        });
        observer.observe(container);
      }
      setRenderState("ready");
    }

    void mount().catch(() => {
      if (!disposed) setRenderState("unavailable");
    });
    return () => {
      disposed = true;
      observer?.disconnect();
      disposeGraph?.();
    };
  }, [mode, graph]);

  const selectedNode = graph.nodes.find((node) => node.id === selectedNodeId);
  const selectedEdges: OntologyEdge[] = graph.edges
    .filter((edge) => edge.source === selectedNodeId || edge.target === selectedNodeId)
    .slice(0, 6);
  const nodeLabels = new Map(graph.nodes.map((node) => [node.id, node.label]));

  return (
    <div className="ontology-viewer">
      <div className="ontology-view-modes" role="group" aria-label="관계 그래프 보기 방식">
        <button type="button" aria-pressed={mode === "diagram"} onClick={() => setMode("diagram")}>
          2D 관계도
        </button>
        <button type="button" aria-pressed={mode === "spatial"} onClick={() => setMode("spatial")}>
          3D 탐색
        </button>
      </div>
      {mode === "diagram" ? children : (
        <div className="ontology-spatial">
          <div className="ontology-spatial-canvas" ref={mountRef} aria-hidden="true" />
          {renderState === "loading" && <p className="ontology-spatial-state" role="status">3D 관계도를 준비하고 있습니다.</p>}
          {renderState === "unavailable" && (
            <p className="ontology-spatial-state" role="status">
              이 환경에서는 3D를 표시할 수 없습니다. 2D 관계도와 아래 공개 기록 목록을 이용해 주세요.
            </p>
          )}
          <div className="ontology-spatial-details">
            <p className="ontology-limit-note">드래그해서 회전하고 스크롤로 확대할 수 있습니다. 아래 선택 메뉴로도 관계를 탐색할 수 있습니다.</p>
            <label htmlFor={selectId}>연결 대상 선택</label>
            <select id={selectId} value={selectedNodeId} onChange={(event) => setSelectedNodeId(event.target.value)}>
              {graph.nodes.map((node) => (
                <option key={node.id} value={node.id}>{node.label}</option>
              ))}
            </select>
            {selectedNode && (
              <div className="ontology-spatial-selection" aria-live="polite">
                <strong>{selectedNode.label}</strong>
                {selectedNode.kind === "SOURCE_LISTED_ROLE_HOLDER" && <p>공시상 이름으로, 동일인 식별이 확정된 인물 기록은 아닙니다.</p>}
                {selectedEdges.length > 0 && (
                  <ul>
                    {selectedEdges.map((edge) => {
                      const otherId = edge.source === selectedNodeId ? edge.target : edge.source;
                      return (
                        <li key={edge.id}>
                          <span>{relationLabel(edge.relation_type)} · {nodeLabels.get(otherId) ?? "공개 기록"}</span>
                          <span className={`status ${edge.epistemic_status}`}>{statusLabel(edge.epistemic_status)}</span>
                          {edge.source_conflict && <span className="status CONFLICT">{statusLabel("CONFLICT")}</span>}
                          <a href={`#claim-${edge.claim_id}`}>근거 기록</a>
                          {edge.source_ids[0] && <a href={`#source-${edge.source_ids[0]}`}>원문 출처</a>}
                        </li>
                      );
                    })}
                  </ul>
                )}
              </div>
            )}
            <p className="ontology-limit-note">3D에는 공개 연결 {graph.edges.length}건을 표시합니다{totalEdges > graph.edges.length ? ` (전체 ${totalEdges}건)` : ""}. 전체 기록은 아래 목록에서 확인할 수 있습니다.</p>
          </div>
        </div>
      )}
    </div>
  );
}

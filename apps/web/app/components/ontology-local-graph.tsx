import { statusLabel, relationLabel } from "../display-labels";
import Link from "next/link";

import Ontology3DExplorer from "./ontology-3d-explorer";

import { committeeHref } from "../gukgam/2026/committees";
import type { OntologyGraph } from "../types";

function shortLabel(value: string, length = 16): string {
  return value.length > length ? `${value.slice(0, length - 1)}…` : value;
}

export default function OntologyLocalGraph({
  graph,
  sourceTitles,
  gukgamCommittees = [],
  claimAnchorsInRecords = false,
}: {
  graph: OntologyGraph;
  sourceTitles: Record<string, string>;
  gukgamCommittees?: string[];
  claimAnchorsInRecords?: boolean;
}) {
  const gukgamCommitteeNames = new Set(gukgamCommittees);
  const nodeById = new Map(graph.nodes.map((node) => [node.id, node]));
  const center = nodeById.get(graph.center_node_id);
  const visibleEdges = graph.edges.slice(0, 6);
  const relationKinds = new Set(visibleEdges.map((edge) => edge.relation_type));
  const singleRelationType = relationKinds.size === 1 ? visibleEdges[0]?.relation_type : null;
  const height = Math.max(180, visibleEdges.length * 76 + 44);
  const centerY = height / 2;
  // The optional 3D view receives only the already-public, bounded read model.
  const spatialEdges = graph.edges.slice(0, 48);
  const spatialIds = new Set([graph.center_node_id, ...spatialEdges.flatMap((edge) => [edge.source, edge.target])]);
  const spatialGraph = {
    center_node_id: graph.center_node_id,
    nodes: graph.nodes.filter((node) => spatialIds.has(node.id)),
    edges: spatialEdges,
  };

  return (
    <div className="ontology-explorer">
      <Ontology3DExplorer graph={spatialGraph} key={graph.center_node_id} totalEdges={graph.edges.length}>
        <div className="ontology-visual" aria-hidden="true">
        <svg viewBox={`0 0 720 ${height}`} role="presentation">
          {visibleEdges.map((edge, index) => {
            const target = nodeById.get(edge.source === graph.center_node_id ? edge.target : edge.source);
            const targetY = 44 + index * 76;
            const relation = relationLabel(edge.relation_type)
            return (
              <g key={edge.id}>
                <line className="ontology-line" x1="250" y1={centerY} x2="470" y2={targetY} />
                {!singleRelationType && (
                  <text className="ontology-edge-label" x="360" y={(centerY + targetY) / 2 - 7} textAnchor="middle">
                    {relation}
                  </text>
                )}
                <rect className="ontology-node ontology-node-target" x="470" y={targetY - 23} width="210" height="46" rx="10" />
                <text className="ontology-node-label" x="575" y={targetY + 5} textAnchor="middle">
                  {shortLabel(target?.label ?? "공개 기록")}
                </text>
              </g>
            );
          })}
          {singleRelationType && (
            <text className="ontology-edge-label" x="360" y={centerY - 12} textAnchor="middle">
              {relationLabel(singleRelationType)}
            </text>
          )}
          <rect className="ontology-node ontology-node-center" x="40" y={centerY - 28} width="210" height="56" rx="12" />
          <text className="ontology-node-label ontology-node-label-center" x="145" y={centerY + 6} textAnchor="middle">
            {shortLabel(center?.label ?? "인물", 14)}
          </text>
        </svg>
        </div>
      </Ontology3DExplorer>

      <div className="ontology-relations" aria-label="공식 기록상 연결 목록">
        {graph.edges.map((edge, edgeIndex) => {
          const target = nodeById.get(edge.source === graph.center_node_id ? edge.target : edge.source);
          const firstSource = edge.source_ids[0];
          return (
            <article
              className="ontology-relation"
              key={edge.id}
              id={
                !claimAnchorsInRecords && edge.relation_type === "SERVED_ON"
                  && graph.edges.findIndex((item) => item.claim_id === edge.claim_id) === edgeIndex
                  ? `claim-${edge.claim_id}`
                  : undefined
              }
            >
              <div className="ontology-relation-heading">
                <span className="micro-label">{relationLabel(edge.relation_type)}</span>
                <span className={`status ${edge.epistemic_status}`}>{statusLabel(edge.epistemic_status)}</span>
              </div>
              <strong>
                {target?.kind === "COMMITTEE" && gukgamCommitteeNames.has(target.label) ? (
                  <Link href={committeeHref(target.label)}>{target.label}</Link>
                ) : (
                  target?.label ?? "연결 대상"
                )}
              </strong>
              <p>
                {edge.valid_from ? `기록 시작 ${edge.valid_from.slice(0, 10)}` : "기간 정보 없음"}
                {edge.valid_to ? ` · 종료 ${edge.valid_to.slice(0, 10)}` : ""}
              </p>
              {edge.source_conflict && (
                <p className="ontology-conflict"><span className="status CONFLICT">{statusLabel("CONFLICT")}</span> 근거가 서로 상충합니다.</p>
              )}
              {firstSource && (
                <Link className="ontology-source-link" href={`#source-${firstSource}`}>
                  {sourceTitles[firstSource] ?? "출처"}
                </Link>
              )}
            </article>
          );
        })}
      </div>

      {graph.edges.length > visibleEdges.length && (
        <p className="ontology-limit-note">2D 관계도에는 처음 {visibleEdges.length}개 연결만 그립니다. 아래 목록에는 공개된 연결이 모두 있습니다.</p>
      )}
      {graph.nodes.some((node) => node.kind === "SOURCE_LISTED_ROLE_HOLDER") && (
        <p className="ontology-limit-note">
          임원은 공식 공시에 적힌 이름이며 인물 기록이 아닙니다. 같은 이름이어도 자동으로 합치거나 인물 페이지에 연결하지 않습니다.
        </p>
      )}
      <p className="ontology-limit-note">표시된 연결은 공개된 기록과 근거에 따른 연결이며 친분, 영향력 또는 동기를 의미하지 않습니다.</p>
    </div>
  );
}

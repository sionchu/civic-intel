import Link from "next/link";

import type { OntologyGraph } from "../types";

const RELATION_LABELS: Record<string, string> = {
  HELD_ROLE: "직책",
  WORKED_AT: "경력",
  STUDIED_AT: "학력",
  SERVED_ON: "위원회",
  DIRECTOR_OF: "이사회",
  APPOINTED_TO: "임명",
  APPEARED_AT: "출석",
  QUESTIONED: "질의",
  AUDITED_BY: "감사",
};

function shortLabel(value: string, length = 16): string {
  return value.length > length ? `${value.slice(0, length - 1)}…` : value;
}

export default function OntologyLocalGraph({
  graph,
  sourceTitles,
}: {
  graph: OntologyGraph;
  sourceTitles: Record<string, string>;
}) {
  const nodeById = new Map(graph.nodes.map((node) => [node.id, node]));
  const center = nodeById.get(graph.center_node_id);
  const visibleEdges = graph.edges.slice(0, 6);
  const height = Math.max(180, visibleEdges.length * 76 + 44);
  const centerY = height / 2;

  return (
    <div className="ontology-explorer">
      <div className="ontology-visual" aria-hidden="true">
        <svg viewBox={`0 0 720 ${height}`} role="presentation">
          {visibleEdges.map((edge, index) => {
            const target = nodeById.get(edge.target);
            const targetY = 44 + index * 76;
            const relation = RELATION_LABELS[edge.relation_type] ?? edge.relation_type;
            return (
              <g key={edge.id}>
                <line className="ontology-line" x1="250" y1={centerY} x2="470" y2={targetY} />
                <text className="ontology-edge-label" x="360" y={(centerY + targetY) / 2 - 7} textAnchor="middle">
                  {relation}
                </text>
                <rect className="ontology-node ontology-node-target" x="470" y={targetY - 23} width="210" height="46" rx="10" />
                <text className="ontology-node-label" x="575" y={targetY + 5} textAnchor="middle">
                  {shortLabel(target?.label ?? "공개 기록")}
                </text>
              </g>
            );
          })}
          <rect className="ontology-node ontology-node-center" x="40" y={centerY - 28} width="210" height="56" rx="12" />
          <text className="ontology-node-label ontology-node-label-center" x="145" y={centerY + 6} textAnchor="middle">
            {shortLabel(center?.label ?? "Person", 14)}
          </text>
        </svg>
      </div>

      <div className="ontology-relations" aria-label="공식 기록상 연결 목록">
        {graph.edges.map((edge) => {
          const target = nodeById.get(edge.target);
          const firstSource = edge.source_ids[0];
          return (
            <article className="ontology-relation" key={edge.id}>
              <div className="ontology-relation-heading">
                <span className="micro-label">{RELATION_LABELS[edge.relation_type] ?? edge.relation_type}</span>
                <span className={`status ${edge.epistemic_status}`}>{edge.epistemic_status}</span>
              </div>
              <strong>{target?.label ?? "연결 대상"}</strong>
              <p>
                {edge.valid_from ? `기록 시작 ${edge.valid_from.slice(0, 10)}` : "기간 정보 없음"}
                {edge.valid_to ? ` · 종료 ${edge.valid_to.slice(0, 10)}` : ""}
              </p>
              {edge.source_conflict && (
                <p className="ontology-conflict"><span className="status CONFLICT">SOURCE CONFLICT</span> 근거가 서로 상충합니다.</p>
              )}
              {firstSource && (
                <Link className="ontology-source-link" href={`#source-${firstSource}`}>
                  {sourceTitles[firstSource] ?? "Evidence source"} <span aria-hidden="true">↓</span>
                </Link>
              )}
            </article>
          );
        })}
      </div>

      {graph.edges.length > visibleEdges.length && (
        <p className="ontology-limit-note">시각화는 읽기 쉬운 local graph를 위해 처음 {visibleEdges.length}개 연결만 그립니다. 아래 텍스트 목록에는 현재 공개 edge 전체를 유지합니다.</p>
      )}
      <p className="ontology-limit-note">표시된 연결은 공개 기록의 Claim/Evidence 관계이며 친분, 영향력 또는 동기를 의미하지 않습니다.</p>
    </div>
  );
}

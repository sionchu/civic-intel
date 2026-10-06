// One compact line for record lanes that have no connected source yet. It states a coverage gap,
// not a negative fact.
export default function PendingLanes({ lanes, detail }: { lanes: string[]; detail?: string }) {
  if (lanes.length === 0) return null;
  return (
    <p className="pending-lanes" role="status">
      <strong>아직 수집되지 않은 기록</strong>
      <span>{lanes.join(" · ")}</span>
      <small>{detail ?? "기록이 없다는 뜻이 아니라 아직 연결된 출처가 없다는 뜻입니다."}</small>
    </p>
  );
}

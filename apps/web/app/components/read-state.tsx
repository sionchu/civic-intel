import type { ApiError } from "../types";

const COPY: Record<ApiError["code"], { title: string; detail: string }> = {
  PUBLIC_RECORD_NOT_FOUND: {
    title: "공개 기록을 찾을 수 없습니다.",
    detail: "요청한 식별자에 해당하는 현재 공개 대상이 없습니다.",
  },
  INSUFFICIENT_ELIGIBLE_INPUTS: {
    title: "비교 가능한 입력이 부족합니다.",
    detail: "현재 공개 적격 Claim만으로는 이 비교를 만들 수 없습니다.",
  },
  SOURCE_VERSION_CONFLICT: {
    title: "서로 다른 출처 버전이 확인됐습니다.",
    detail: "어느 값을 최신 사실로 추정하지 않고 비교를 보류합니다.",
  },
  ACCESS_DENIED: {
    title: "이 작업에 접근할 수 없습니다.",
    detail: "공개 읽기 범위에 포함되지 않은 기능입니다.",
  },
  INVALID_INPUT: {
    title: "입력 조건을 확인해 주세요.",
    detail: "요청 값으로는 이 공개 읽기를 실행할 수 없습니다.",
  },
  SERVICE_UNAVAILABLE: {
    title: "공개 데이터 서비스에 일시적인 문제가 있습니다.",
    detail: "자료 없음이나 UNKNOWN으로 처리하지 않았습니다. 잠시 뒤 다시 시도해 주세요.",
  },
};

export default function ReadState({ error }: { error: ApiError }) {
  const copy = COPY[error.code];
  return (
    <div className={`read-state ${error.code}`} role={error.code === "SERVICE_UNAVAILABLE" ? "alert" : "status"}>
      <span className="status">{error.code}</span>
      <strong>{copy.title}</strong>
      <p>{copy.detail}</p>
      {error.request_id && <small>Request ID {error.request_id}</small>}
    </div>
  );
}

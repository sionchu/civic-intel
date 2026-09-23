import "server-only";
import { headers } from "next/headers";
import { notFound } from "next/navigation";
import type { ApiResult } from "../../types";

export async function requireOperator(): Promise<void> {
  const token = process.env.CIVIC_OPERATOR_TOKEN ?? "";
  const requestHeaders = await headers();
  let hostname = "";
  try { hostname = new URL(`http://${requestHeaders.get("host") ?? ""}`).hostname; } catch { /* fail closed */ }
  if (process.env.CIVIC_OPERATOR_ENABLED !== "1" || !/^[A-Za-z0-9_-]{32,128}$/.test(token)
    || !["localhost", "127.0.0.1", "[::1]"].includes(hostname)) notFound();
  const origin = requestHeaders.get("origin");
  if (origin && origin !== `http://${requestHeaders.get("host")}`) notFound();
}

export async function operatorRead<T>(path: string): Promise<ApiResult<T>> {
  await requireOperator();
  const base = process.env.CIVIC_OPERATOR_API_URL ?? "";
  try {
    const url = new URL(base);
    if (url.protocol !== "http:" || !["localhost", "127.0.0.1", "[::1]"].includes(url.hostname)
      || !(path.startsWith("/admin/operations") || /^\/ontology\/(people|organizations)\/[0-9a-f-]{36}$/i.test(path))) throw new Error("Private URL required");
    const response = await fetch(`${base}${path}`, {
      cache: "no-store", signal: AbortSignal.timeout(25000), redirect: "error",
      headers: { "X-Civic-Operator-Token": process.env.CIVIC_OPERATOR_TOKEN ?? "" },
    });
    if (response.ok) return { state: "success", data: await response.json() as T };
    return { state: "error", error: {
      code: response.status === 403 ? "ACCESS_DENIED" : response.status === 422 ? "INVALID_INPUT"
        : response.status === 404 ? "PUBLIC_RECORD_NOT_FOUND" : "SERVICE_UNAVAILABLE",
      message: "운영 데이터 조회에 실패했습니다. 필터, 연결 또는 접근 설정을 확인하세요.",
      request_id: response.headers.get("x-request-id"),
    } };
  } catch {
    return { state: "error", error: { code: "SERVICE_UNAVAILABLE",
      message: "운영 API에 연결할 수 없습니다. 자료 없음으로 처리하지 않았습니다.", request_id: null } };
  }
}

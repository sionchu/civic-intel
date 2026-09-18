import type {
  ApiErrorCode,
  ApiResult,
  MoneyProjection,
  OntologyGraph,
  Organization,
  OrganizationSummary,
  Person,
  ReviewReport,
  Source,
} from "./types";

const API = process.env.CIVIC_API_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const STATUS_CODE: Record<number, ApiErrorCode> = {
  403: "ACCESS_DENIED",
  404: "PUBLIC_RECORD_NOT_FOUND",
  409: "SOURCE_VERSION_CONFLICT",
  422: "INVALID_INPUT",
};

async function getJson<T>(path: string): Promise<ApiResult<T>> {
  try {
    const response = await fetch(`${API}${path}`, { cache: "no-store" });
    if (response.ok) return { state: "success", data: (await response.json()) as T };
    const payload = await response.json().catch(() => null) as {
      error?: { code?: ApiErrorCode; message?: string; request_id?: string };
    } | null;
    return {
      state: "error",
      error: {
        code: payload?.error?.code ?? STATUS_CODE[response.status] ?? "SERVICE_UNAVAILABLE",
        message: payload?.error?.message ?? "The public data service is temporarily unavailable.",
        request_id: payload?.error?.request_id ?? response.headers.get("x-request-id"),
      },
    };
  } catch {
    return {
      state: "error",
      error: {
        code: "SERVICE_UNAVAILABLE",
        message: "The public data service is temporarily unavailable.",
        request_id: null,
      },
    };
  }
}

export function getPeople(): Promise<ApiResult<Person[]>> { return getJson("/people"); }
export function getPerson(id: string): Promise<ApiResult<Person>> { return getJson(`/people/${id}`); }
export function getPersonOntology(id: string): Promise<ApiResult<OntologyGraph>> {
  return getJson(`/ontology/people/${id}`);
}
export function getOrganization(id: string): Promise<ApiResult<Organization>> {
  return getJson(`/organizations/${id}`);
}
export function getOrganizations(): Promise<ApiResult<OrganizationSummary[]>> {
  return getJson("/organizations");
}
export function getOrganizationMoney(
  id: string,
  earlierFiscalYear = 2024,
  laterFiscalYear = 2025,
): Promise<ApiResult<MoneyProjection>> {
  return getJson(
    `/organizations/${id}/money?earlier_fiscal_year=${earlierFiscalYear}&later_fiscal_year=${laterFiscalYear}`,
  );
}
export function getSource(id: string): Promise<ApiResult<Source>> { return getJson(`/sources/${id}`); }
export function getReviewReport(): Promise<ApiResult<ReviewReport>> { return getJson("/admin/review"); }

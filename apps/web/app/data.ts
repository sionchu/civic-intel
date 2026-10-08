import type {
  ApiErrorCode,
  ApiResult,
  GukgamCommitteeProjection,
  GukgamTargetProjection,
  GukgamWitnessProjection,
  MoneyProjection,
  OntologyGraph,
  Organization,
  OrganizationSummary,
  Person,
  PersonRelationships,
  Source,
} from "./types";
import { readPublic } from "./public-read";
import { personRelationshipPath } from "./relationship-path.mjs";

const DIRECTORY_REVALIDATE_SECONDS = 60;

const STATUS_CODE: Record<number, ApiErrorCode> = {
  403: "ACCESS_DENIED",
  404: "PUBLIC_RECORD_NOT_FOUND",
  409: "SOURCE_VERSION_CONFLICT",
  422: "INVALID_INPUT",
};

async function getJson<T>(
  path: string,
  options: { revalidateSeconds?: number } = {},
): Promise<ApiResult<T>> {
  try {
    const response = await readPublic(path, options);
    if (response.status >= 200 && response.status < 300) return { state: "success", data: response.body as T };
    const payload = response.body as {
      error?: { code?: ApiErrorCode; message?: string; request_id?: string };
    } | null;
    return {
      state: "error",
      error: {
        code: payload?.error?.code ?? STATUS_CODE[response.status] ?? "SERVICE_UNAVAILABLE",
        message: payload?.error?.message ?? "공개 데이터 서비스에 일시적으로 연결할 수 없습니다.",
        request_id: payload?.error?.request_id ?? response.requestId,
      },
    };
  } catch {
    return {
      state: "error",
      error: {
        code: "SERVICE_UNAVAILABLE",
        message: "공개 데이터 서비스에 일시적으로 연결할 수 없습니다.",
        request_id: null,
      },
    };
  }
}

export function getPeople(): Promise<ApiResult<Person[]>> {
  return getJson("/people", { revalidateSeconds: DIRECTORY_REVALIDATE_SECONDS });
}
export function getPerson(id: string): Promise<ApiResult<Person>> { return getJson(`/people/${id}`); }
export function getPersonOntology(id: string): Promise<ApiResult<OntologyGraph>> {
  return getJson(`/ontology/people/${id}`);
}
export function getPersonRelationships(id: string): Promise<ApiResult<PersonRelationships>> {
  return getJson(personRelationshipPath(id));
}
export function getOrganization(id: string): Promise<ApiResult<Organization>> {
  return getJson(`/organizations/${id}`);
}
export function getOrganizationOntology(id: string): Promise<ApiResult<OntologyGraph>> {
  return getJson(`/ontology/organizations/${id}`);
}
export function getOrganizations(): Promise<ApiResult<OrganizationSummary[]>> {
  return getJson("/organizations", {
    revalidateSeconds: DIRECTORY_REVALIDATE_SECONDS,
  });
}
export function getGukgamTargets(): Promise<ApiResult<GukgamTargetProjection>> {
  return getJson("/gukgam/2026/targets");
}
export function getGukgamCommittees(): Promise<ApiResult<GukgamCommitteeProjection>> {
  return getJson("/gukgam/2026/committees");
}
export function getGukgamWitnesses(): Promise<ApiResult<GukgamWitnessProjection>> {
  return getJson("/gukgam/2026/witnesses");
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

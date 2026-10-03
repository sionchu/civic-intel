import "server-only";

import type {
  ApiErrorCode,
  ApiResult,
  GukgamTargetProjection,
  MoneyProjection,
  OntologyGraph,
  Organization,
  OrganizationSummary,
  Person,
  Source,
} from "./types";

const DIRECTORY_REVALIDATE_SECONDS = 60;
const API_TIMEOUT_MS = 8000;
const UUID = "[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}";
const PUBLIC_READ_PATH = new RegExp(
  `^/(?:people(?:/${UUID})?|organizations(?:/${UUID})?|sources/${UUID}|ontology/(?:people|organizations)/${UUID}|gukgam/2026/targets|organizations/${UUID}/money\\?earlier_fiscal_year=[0-9]{4}&later_fiscal_year=[0-9]{4})$`,
  "i",
);

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
  if (!PUBLIC_READ_PATH.test(path)) {
    return { state: "error", error: {
      code: "INVALID_INPUT", message: "The public record identifier is invalid.", request_id: null,
    } };
  }
  try {
    const base = new URL(process.env.CIVIC_API_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000");
    if (!["http:", "https:"].includes(base.protocol) || base.username || base.password
      || base.pathname !== "/" || base.search || base.hash) throw new Error("Invalid API origin");
    const clientId = process.env.CIVIC_ACCESS_CLIENT_ID ?? "";
    const clientSecret = process.env.CIVIC_ACCESS_CLIENT_SECRET ?? "";
    const headers: Record<string, string> = { Accept: "application/json" };
    if (clientId || clientSecret || process.env.CIVIC_ACCESS_ORIGIN) {
      if (!clientId || !clientSecret || base.protocol !== "https:"
        || process.env.CIVIC_ACCESS_ORIGIN !== base.origin) throw new Error("Invalid service credential binding");
      headers["CF-Access-Client-Id"] = clientId;
      headers["CF-Access-Client-Secret"] = clientSecret;
    }
    const response = await fetch(
      `${base.origin}${path}`,
      {
        method: "GET",
        headers,
        redirect: "manual",
        signal: AbortSignal.timeout(API_TIMEOUT_MS),
        ...(options.revalidateSeconds && !clientSecret
          ? { next: { revalidate: options.revalidateSeconds } }
          : { cache: "no-store" as const }),
      },
    );
    if (response.status >= 300 && response.status < 400) throw new Error("API redirect rejected");
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

export function getPeople(): Promise<ApiResult<Person[]>> {
  return getJson("/people", { revalidateSeconds: DIRECTORY_REVALIDATE_SECONDS });
}
export function getPerson(id: string): Promise<ApiResult<Person>> { return getJson(`/people/${id}`); }
export function getPersonOntology(id: string): Promise<ApiResult<OntologyGraph>> {
  return getJson(`/ontology/people/${id}`);
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

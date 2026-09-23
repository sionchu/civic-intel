import { NextRequest, NextResponse } from "next/server";
import { requireOperator } from "../operator-data";

export const dynamic = "force-dynamic";
export async function POST(request: NextRequest) {
  await requireOperator();
  const host = request.headers.get("host");
  const origin = request.headers.get("origin");
  if (!host || origin !== `http://${host}` || request.headers.get("x-civic-admin-intent") !== "explicit"
    || !request.headers.get("content-type")?.startsWith("application/json")
    || ![null, "same-origin"].includes(request.headers.get("sec-fetch-site"))) {
    return NextResponse.json({ error: { message: "같은 운영 화면의 명시적 요청만 허용합니다." } }, { status: 403 });
  }
  let input: { operation?: string; payload?: unknown };
  try {
    const body = await request.text();
    if (body.length > 64000) throw new Error("too large");
    input = JSON.parse(body);
  } catch {
    return NextResponse.json({ error: { message: "잘못된 요청 형식입니다." } }, { status: 400 });
  }
  const allowed: Record<string, string> = { preview: "preview", commit: "commit" };
  let path = allowed[input.operation ?? ""];
  let method = "POST";
  if (input.operation === "lookup") {
    const lookup = input.payload as { kind?: string; q?: string; id?: string };
    if (!lookup || !["people", "evidence", "observations", "claims"].includes(lookup.kind ?? "")) {
      return NextResponse.json({ error: { message: "지원하지 않는 조회입니다." } }, { status: 400 });
    }
    method = "GET";
    path = lookup.id && /^[0-9a-f-]{36}$/i.test(lookup.id)
      ? `records/${lookup.kind}/${lookup.id}`
      : `records?${new URLSearchParams({ kind: lookup.kind!, q: (lookup.q ?? "").slice(0, 200), limit: "10" })}`;
    if (lookup.kind === "evidence" && !lookup.id) path = `evidence-options?${new URLSearchParams({ q: (lookup.q ?? "").slice(0, 200) })}`;
  }
  if (!path) return NextResponse.json({ error: { message: "지원하지 않는 작업입니다." } }, { status: 400 });
  try {
    const base = process.env.CIVIC_OPERATOR_API_URL ?? "";
    const parsed = new URL(base);
    if (parsed.protocol !== "http:" || !["127.0.0.1", "localhost", "[::1]"].includes(parsed.hostname)) throw new Error("private URL required");
    const response = await fetch(`${base}/admin/operations/${path}`, { method, cache: "no-store", redirect: "error",
      signal: AbortSignal.timeout(180000), headers: { "Content-Type": "application/json", "X-Civic-Operator-Token": process.env.CIVIC_OPERATOR_TOKEN ?? "" },
      body: method === "POST" ? JSON.stringify(input.payload) : undefined,
    });
    const output = await response.json();
    return NextResponse.json(output, { status: response.status, headers: { "Cache-Control": "private, no-store" } });
  } catch {
    return NextResponse.json({ error: { message: "연결 오류입니다. 변경 이력에서 같은 요청 ID의 처리 여부를 먼저 확인하세요. 성공으로 표시하지 않았습니다." } }, { status: 503 });
  }
}

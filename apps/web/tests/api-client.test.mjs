import assert from "node:assert/strict";
import { createServer } from "node:http";
import { afterEach, test } from "node:test";
import { getPeople, getPerson, getSource, getOrganizationMoney } from "../app/data.ts";

const originalFetch = globalThis.fetch;
const originalTimeout = AbortSignal.timeout;
const keys = ["CIVIC_API_URL", "NEXT_PUBLIC_API_URL", "CIVIC_ACCESS_ORIGIN",
  "CIVIC_ACCESS_CLIENT_ID", "CIVIC_ACCESS_CLIENT_SECRET"];
const originalEnvironment = Object.fromEntries(keys.map((key) => [key, process.env[key]]));
const id = "11000000-0000-0000-0000-000000000001";
const origin = "https://civic-api.example.test";

function configure(values = {}) {
  for (const key of keys) delete process.env[key];
  Object.assign(process.env, { CIVIC_API_URL: origin }, values);
}

afterEach(() => {
  globalThis.fetch = originalFetch;
  AbortSignal.timeout = originalTimeout;
  for (const key of keys) {
    if (originalEnvironment[key] === undefined) delete process.env[key];
    else process.env[key] = originalEnvironment[key];
  }
});

test("authenticated public reads bind credentials to one HTTPS origin and preserve DTOs", async () => {
  configure({ CIVIC_ACCESS_ORIGIN: origin, CIVIC_ACCESS_CLIENT_ID: "fixture-id",
    CIVIC_ACCESS_CLIENT_SECRET: "fixture-secret" });
  const calls = [];
  globalThis.fetch = async (url, options) => {
    calls.push({ url, options });
    return Response.json([{ id }]);
  };
  assert.deepEqual(await getPeople(), { state: "success", data: [{ id }] });
  assert.equal(calls[0].url, origin + "/people");
  assert.equal(calls[0].options.method, "GET");
  assert.equal(calls[0].options.headers["CF-Access-Client-Secret"], "fixture-secret");
  assert.equal(calls[0].options.cache, "no-store");
  assert.equal(calls[0].options.redirect, "manual");
});

test("credentials fail closed for missing pair, HTTP or mismatched destination", async () => {
  for (const values of [
    { CIVIC_ACCESS_ORIGIN: origin },
    { CIVIC_ACCESS_CLIENT_ID: "fixture-id" },
    { CIVIC_ACCESS_CLIENT_SECRET: "fixture-secret" },
    { CIVIC_ACCESS_CLIENT_ID: "fixture-id", CIVIC_ACCESS_CLIENT_SECRET: "fixture-secret" },
    { CIVIC_ACCESS_CLIENT_ID: "fixture-id", CIVIC_ACCESS_CLIENT_SECRET: "fixture-secret",
      CIVIC_ACCESS_ORIGIN: "https://other.example.test" },
    { CIVIC_API_URL: "http://127.0.0.1:8765", CIVIC_ACCESS_CLIENT_ID: "fixture-id",
      CIVIC_ACCESS_CLIENT_SECRET: "fixture-secret", CIVIC_ACCESS_ORIGIN: "http://127.0.0.1:8765" },
  ]) {
    configure(values);
    let called = false;
    globalThis.fetch = async () => { called = true; throw new Error("unexpected fetch"); };
    const result = await getPeople();
    assert.equal(result.error.code, "SERVICE_UNAVAILABLE");
    assert.equal(called, false);
    assert.doesNotMatch(JSON.stringify(result), /fixture|example|127\.0\.0\.1/);
  }
});

test("URL credentials, base paths and invalid record routes never trigger a request", async () => {
  let calls = 0;
  globalThis.fetch = async () => { calls++; return Response.json({}); };
  for (const url of ["https://user:secret@example.test", origin + "/admin", origin + "?key=secret",
    origin + "#secret", "file:///private/data"]) {
    configure({ CIVIC_API_URL: url });
    assert.equal((await getPeople()).error.code, "SERVICE_UNAVAILABLE");
  }
  configure();
  for (const invalidId of ["../admin/operations", "//other.example.test", id + "?key=secret"]) {
    assert.equal((await getPerson(invalidId)).error.code, "INVALID_INPUT");
    assert.equal((await getSource(invalidId)).error.code, "INVALID_INPUT");
  }
  assert.equal((await getOrganizationMoney(id, Number.NaN, 2025)).error.code, "INVALID_INPUT");
  assert.equal(calls, 0);
});

test("public API error semantics survive the service bridge", async () => {
  configure();
  for (const [status, code] of [[403, "ACCESS_DENIED"], [409, "SOURCE_VERSION_CONFLICT"],
    [404, "PUBLIC_RECORD_NOT_FOUND"], [422, "INVALID_INPUT"], [503, "SERVICE_UNAVAILABLE"]]) {
    globalThis.fetch = async () => Response.json({ error: { code, message: "fixture state",
      request_id: "fixture-request" } }, { status });
    const result = await getSource(id);
    assert.equal(result.error.code, code);
    assert.equal(result.error.request_id, "fixture-request");
  }
  globalThis.fetch = async () => new Response("<html>Access sign-in</html>", { status: 403 });
  assert.equal((await getPeople()).error.code, "ACCESS_DENIED");
});

async function fixtureServer(handler, run) {
  const server = createServer(handler);
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  configure({ CIVIC_API_URL: "http://127.0.0.1:" + server.address().port });
  try { await run(); }
  finally {
    server.closeAllConnections();
    await new Promise((resolve) => server.close(resolve));
  }
}

test("real HTTP redirect is rejected without requesting its destination", async () => {
  let redirectTargetRequests = 0;
  await fixtureServer((request, response) => {
    if (request.url === "/people") {
      response.writeHead(302, { Location: "/admin/operations" }).end();
    } else {
      redirectTargetRequests++;
      response.end("unexpected");
    }
  }, async () => {
    assert.equal((await getPeople()).error.code, "SERVICE_UNAVAILABLE");
    assert.equal(redirectTargetRequests, 0);
  });
});

test("real delayed HTTP response times out and is never reported as empty data", async () => {
  await fixtureServer(() => {}, async () => {
    AbortSignal.timeout = () => originalTimeout(25);
    const result = await getPeople();
    assert.equal(result.state, "error");
    assert.equal(result.error.code, "SERVICE_UNAVAILABLE");
    assert.equal(result.data, undefined);
  });
});

test("loopback development sends no service credentials and retains directory revalidation", async () => {
  configure({ CIVIC_API_URL: "http://localhost:8765" });
  globalThis.fetch = async (url, options) => {
    assert.equal(url, "http://localhost:8765/people");
    assert.deepEqual(options.headers, { Accept: "application/json" });
    assert.equal(options.next.revalidate, 60);
    return Response.json([]);
  };
  assert.deepEqual(await getPeople(), { state: "success", data: [] });
});

test("valid money query reaches the canonical route without changing its meaning", async () => {
  configure();
  globalThis.fetch = async (url) => {
    assert.equal(url, origin + "/organizations/" + id + "/money?earlier_fiscal_year=2024&later_fiscal_year=2025");
    return Response.json({ projection: "fixture" });
  };
  assert.deepEqual(await getOrganizationMoney(id), { state: "success", data: { projection: "fixture" } });
});

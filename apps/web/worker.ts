import handler from "vinext/server/fetch-handler";

const worker = {
  fetch(...args: Parameters<typeof handler.fetch>) {
    const request = args[0];
    let path: string;
    try {
      path = decodeURIComponent(new URL(request.url).pathname);
    } catch {
      return new Response("Bad Request", { status: 400 });
    }
    // The hosted surface has no operator capability, even if host bindings drift.
    if (path === "/admin" || path.startsWith("/admin/")) {
      return new Response("Not Found", { status: 404 });
    }
    if (request.method !== "GET" && request.method !== "HEAD") {
      return new Response("Method Not Allowed", {
        status: 405, headers: { Allow: "GET, HEAD" },
      });
    }
    return handler.fetch(...args);
  },
};

export default worker;

const DEFAULT_ORIGIN = "https://linguoren.com";

export default {
  async fetch(request, env) {
    const origin = request.headers.get("Origin") || "";
    const allowedOrigin = env.ALLOWED_ORIGIN || DEFAULT_ORIGIN;

    const cors = {
      "Access-Control-Allow-Origin": allowedOrigin,
      "Access-Control-Allow-Methods": "POST, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type",
      "Access-Control-Max-Age": "600",
      "Vary": "Origin",
    };

    if (request.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: cors });
    }

    if (origin && origin !== allowedOrigin) {
      return new Response("Origin not allowed", { status: 403, headers: cors });
    }

    const url = new URL(request.url);
    if (url.pathname !== "/recommend") {
      return new Response("Not found", { status: 404, headers: cors });
    }

    if (!env.BACKEND_URL || !env.EDGRANT_API_TOKEN) {
      return new Response("Backend not configured", { status: 500, headers: cors });
    }

    const backendResp = await fetch(`${env.BACKEND_URL}/recommend`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${env.EDGRANT_API_TOKEN}`,
      },
      body: await request.text(),
    });

    const body = await backendResp.text();
    return new Response(body, {
      status: backendResp.status,
      headers: { ...cors, "Content-Type": "application/json" },
    });
  },
};

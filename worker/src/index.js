const DEFAULT_ORIGIN = "https://linguoren.com";
const RATE_LIMIT_WINDOW_MS = 60 * 1000;
const DEFAULT_RATE_LIMIT_PER_MIN = 30;

const rateBuckets = new Map();

function parseAllowedOrigins(value) {
  if (!value) return [];
  return value.split(",").map((item) => item.trim()).filter(Boolean);
}

function originFromReferer(referer) {
  if (!referer) return "";
  try {
    return new URL(referer).origin;
  } catch (err) {
    return "";
  }
}

function extractClientIp(headers) {
  const cfIp = headers.get("CF-Connecting-IP");
  if (cfIp) return cfIp;
  const xff = headers.get("X-Forwarded-For");
  if (!xff) return "unknown";
  return xff.split(",")[0].trim() || "unknown";
}

function allowRequest(ip, limitPerMin) {
  const now = Date.now();
  const bucket = rateBuckets.get(ip);
  if (!bucket || now - bucket.windowStart >= RATE_LIMIT_WINDOW_MS) {
    rateBuckets.set(ip, { windowStart: now, count: 1 });
    return true;
  }
  if (bucket.count >= limitPerMin) {
    return false;
  }
  bucket.count += 1;
  return true;
}

async function verifyTurnstile(token, secret, ip) {
  if (!token) return false;
  try {
    const formData = new FormData();
    formData.append("secret", secret);
    formData.append("response", token);
    if (ip && ip !== "unknown") {
      formData.append("remoteip", ip);
    }
    const resp = await fetch("https://challenges.cloudflare.com/turnstile/v0/siteverify", {
      method: "POST",
      body: formData,
    });
    const data = await resp.json();
    return Boolean(data && data.success);
  } catch (err) {
    return false;
  }
}

export default {
  async fetch(request, env) {
    const origin = request.headers.get("Origin") || "";
    const referer = request.headers.get("Referer") || "";
    const refererOrigin = originFromReferer(referer);
    const allowedOrigins = parseAllowedOrigins(env.ALLOWED_ORIGIN) || [];
    const allowedOrigin = allowedOrigins.length > 0 ? allowedOrigins[0] : DEFAULT_ORIGIN;
    const originAllowed = origin && (allowedOrigins.includes(origin) || origin === allowedOrigin);
    const refererAllowed = !origin && refererOrigin && (allowedOrigins.includes(refererOrigin) || refererOrigin === allowedOrigin);
    const isAllowed = Boolean(originAllowed || refererAllowed);
    const corsOrigin = originAllowed ? origin : (refererAllowed ? refererOrigin : allowedOrigin);
    const limitPerMin = Number(env.RATE_LIMIT_PER_MIN || DEFAULT_RATE_LIMIT_PER_MIN);
    const ip = extractClientIp(request.headers);

    const cors = {
      "Access-Control-Allow-Origin": corsOrigin,
      "Access-Control-Allow-Methods": "POST, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type, X-EdGrant-Client, CF-Turnstile-Token, cf-turnstile-token",
      "Access-Control-Max-Age": "600",
      "Vary": "Origin, Referer",
    };

    if (request.method === "OPTIONS") {
      if (!isAllowed) {
        return new Response("Origin not allowed", { status: 403, headers: cors });
      }
      return new Response(null, { status: 204, headers: cors });
    }

    if (!isAllowed) {
      return new Response("Origin not allowed", { status: 403, headers: cors });
    }

    if (!allowRequest(ip, limitPerMin)) {
      return new Response("Rate limit exceeded", { status: 429, headers: cors });
    }

    const clientKey = (env.CLIENT_KEY || "").trim();
    if (clientKey) {
      const provided = (request.headers.get("X-EdGrant-Client") || "").trim();
      if (!provided || provided !== clientKey) {
        return new Response("Unauthorized", { status: 401, headers: cors });
      }
    }

    const url = new URL(request.url);
    if (url.pathname !== "/recommend") {
      return new Response("Not found", { status: 404, headers: cors });
    }

    if (!env.BACKEND_URL || !env.EDGRANT_API_TOKEN) {
      return new Response("Backend not configured", { status: 500, headers: cors });
    }

    const rawBody = await request.text();
    const turnstileSecret = (env.TURNSTILE_SECRET || "").trim();
    if (turnstileSecret) {
      let token = request.headers.get("CF-Turnstile-Token");
      if (!token) {
        try {
          const parsed = JSON.parse(rawBody);
          token = parsed && parsed.turnstile_token;
        } catch (err) {
          token = null;
        }
      }
      const ok = await verifyTurnstile(token, turnstileSecret, ip);
      if (!ok) {
        return new Response("Turnstile verification failed", { status: 403, headers: cors });
      }
    }

    const backendResp = await fetch(`${env.BACKEND_URL}/recommend`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${env.EDGRANT_API_TOKEN}`,
      },
      body: rawBody,
    });

    const body = await backendResp.text();
    return new Response(body, {
      status: backendResp.status,
      headers: { ...cors, "Content-Type": "application/json" },
    });
  },
};

const REDIRECT_STATUSES = new Set([301, 302, 303, 307, 308]);

export class HttpPolicyError extends Error {
  constructor(code, message, details = {}) {
    super(message);
    this.name = "HttpPolicyError";
    this.code = code;
    this.details = details;
  }
}

function validateUrl(rawUrl, allowedOrigins) {
  let url;
  try {
    url = new URL(rawUrl);
  } catch {
    throw new HttpPolicyError("INVALID_URL", "The requested URL is invalid");
  }
  if (url.protocol !== "https:") {
    throw new HttpPolicyError("HTTPS_REQUIRED", "Only HTTPS sources are permitted", { url: url.toString() });
  }
  if (url.username || url.password) {
    throw new HttpPolicyError("CREDENTIALS_IN_URL", "Credentials in source URLs are prohibited");
  }
  if (!allowedOrigins.has(url.origin)) {
    throw new HttpPolicyError("ORIGIN_NOT_ALLOWED", "The source origin is not allowlisted", { origin: url.origin });
  }
  return url;
}

async function readLimitedBody(response, maximumBytes) {
  const declaredLength = Number(response.headers.get("content-length"));
  if (Number.isFinite(declaredLength) && declaredLength > maximumBytes) {
    throw new HttpPolicyError("RESPONSE_TOO_LARGE", "Declared response size exceeds the configured maximum", {
      declaredLength,
      maximumBytes
    });
  }

  if (!response.body) return "";
  const reader = response.body.getReader();
  const chunks = [];
  let received = 0;
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    received += value.byteLength;
    if (received > maximumBytes) {
      await reader.cancel();
      throw new HttpPolicyError("RESPONSE_TOO_LARGE", "Downloaded response exceeds the configured maximum", {
        received,
        maximumBytes
      });
    }
    chunks.push(value);
  }

  const combined = new Uint8Array(received);
  let offset = 0;
  for (const chunk of chunks) {
    combined.set(chunk, offset);
    offset += chunk.byteLength;
  }
  return new TextDecoder("utf-8", { fatal: false }).decode(combined);
}

export class SafeHttpClient {
  constructor({
    allowedOrigins,
    fetchImpl = globalThis.fetch,
    timeoutMs = 15_000,
    maximumBytes = 2_000_000,
    maximumRedirects = 3,
    userAgent = "Zentryva-Research-Intelligence/0.1 (+https://zentryva.com)"
  }) {
    if (!fetchImpl) throw new TypeError("A fetch implementation is required");
    if (!allowedOrigins?.length) throw new TypeError("At least one allowed origin is required");
    this.allowedOrigins = new Set(allowedOrigins.map((origin) => new URL(origin).origin));
    this.fetchImpl = fetchImpl;
    this.timeoutMs = timeoutMs;
    this.maximumBytes = maximumBytes;
    this.maximumRedirects = maximumRedirects;
    this.userAgent = userAgent;
  }

  async get(rawUrl, { accept = "application/json" } = {}) {
    let url = validateUrl(rawUrl, this.allowedOrigins);

    for (let redirectCount = 0; redirectCount <= this.maximumRedirects; redirectCount += 1) {
      const response = await this.fetchImpl(url, {
        method: "GET",
        redirect: "manual",
        signal: AbortSignal.timeout(this.timeoutMs),
        headers: {
          accept,
          "user-agent": this.userAgent
        }
      });

      if (REDIRECT_STATUSES.has(response.status)) {
        const location = response.headers.get("location");
        if (!location) throw new HttpPolicyError("INVALID_REDIRECT", "Redirect response did not include a location");
        if (redirectCount === this.maximumRedirects) {
          throw new HttpPolicyError("TOO_MANY_REDIRECTS", "Maximum redirect count exceeded");
        }
        url = validateUrl(new URL(location, url).toString(), this.allowedOrigins);
        continue;
      }

      if (!response.ok) {
        throw new HttpPolicyError("UPSTREAM_HTTP_ERROR", `Upstream returned HTTP ${response.status}`, {
          status: response.status,
          url: url.toString()
        });
      }

      const body = await readLimitedBody(response, this.maximumBytes);
      return {
        url: url.toString(),
        status: response.status,
        contentType: response.headers.get("content-type") ?? "",
        body
      };
    }

    throw new HttpPolicyError("TOO_MANY_REDIRECTS", "Maximum redirect count exceeded");
  }

  async getJson(rawUrl) {
    const response = await this.get(rawUrl, { accept: "application/json" });
    try {
      return { ...response, data: JSON.parse(response.body) };
    } catch (cause) {
      throw new HttpPolicyError("INVALID_JSON", "Upstream response was not valid JSON", {
        url: response.url,
        cause: cause.message
      });
    }
  }
}

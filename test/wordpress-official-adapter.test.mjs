import test from "node:test";
import assert from "node:assert/strict";
import { HttpPolicyError, SafeHttpClient } from "../src/adapters/safe-http.mjs";
import { WordPressOfficialAdapter } from "../src/adapters/wordpress-official.mjs";

function jsonResponse(value, init = {}) {
  return new Response(JSON.stringify(value), {
    status: init.status ?? 200,
    headers: { "content-type": "application/json", ...(init.headers ?? {}) }
  });
}

test("SafeHttpClient rejects non-allowlisted and non-HTTPS origins", async () => {
  const client = new SafeHttpClient({
    allowedOrigins: ["https://api.wordpress.org"],
    fetchImpl: async () => jsonResponse({})
  });

  await assert.rejects(() => client.get("http://api.wordpress.org/a"), (error) => {
    assert.equal(error.code, "HTTPS_REQUIRED");
    return true;
  });
  await assert.rejects(() => client.get("https://evil.example/a"), (error) => {
    assert.equal(error.code, "ORIGIN_NOT_ALLOWED");
    return true;
  });
});

test("SafeHttpClient blocks oversized responses", async () => {
  const client = new SafeHttpClient({
    allowedOrigins: ["https://api.wordpress.org"],
    maximumBytes: 8,
    fetchImpl: async () => new Response("0123456789", {
      status: 200,
      headers: { "content-type": "text/plain" }
    })
  });

  await assert.rejects(() => client.get("https://api.wordpress.org/a"), HttpPolicyError);
});

test("WordPress adapter normalizes core version evidence", async () => {
  const http = new SafeHttpClient({
    allowedOrigins: ["https://api.wordpress.org"],
    fetchImpl: async () => jsonResponse({
      offers: [{
        response: "upgrade",
        current: "7.1",
        version: "7.1",
        php_version: "7.4.0",
        mysql_version: "5.5.5"
      }]
    })
  });

  const source = await new WordPressOfficialAdapter({ http }).collectCoreVersions();
  assert.equal(source.sourceClass, "release-notes-or-changelog");
  assert.equal(source.raw[0].current, "7.1");
  assert.equal(source.raw[0].phpVersion, "7.4.0");
});

test("WordPress plugin search is bounded and returns compatibility fields", async () => {
  let requested;
  const http = new SafeHttpClient({
    allowedOrigins: ["https://api.wordpress.org"],
    fetchImpl: async (url) => {
      requested = new URL(url);
      return jsonResponse({
        info: { page: 1, pages: 1, results: 1 },
        plugins: [{
          name: "Example",
          slug: "example",
          version: "2.0.0",
          requires: "6.6",
          tested: "7.1",
          requires_php: "8.0",
          active_installs: 1000,
          last_updated: "2026-09-01 1:00pm GMT"
        }]
      });
    }
  });

  const source = await new WordPressOfficialAdapter({ http }).searchPlugins("media manager", {
    page: -4,
    perPage: 500
  });

  assert.equal(requested.searchParams.get("request[page]"), "1");
  assert.equal(requested.searchParams.get("request[per_page]"), "100");
  assert.equal(source.raw.plugins[0].tested, "7.1");
  assert.equal(source.raw.plugins[0].requiresPhp, "8.0");
});

test("WordPress plugin slug validation prevents parameter abuse", async () => {
  const adapter = new WordPressOfficialAdapter({
    http: { async getJson() { throw new Error("must not execute"); } }
  });
  await assert.rejects(() => adapter.getPluginInformation("../bad?slug"), TypeError);
});

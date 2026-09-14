import { SafeHttpClient } from "./safe-http.mjs";

const API_ORIGIN = "https://api.wordpress.org";

function integerWithin(value, minimum, maximum, fallback) {
  const numeric = Number(value);
  if (!Number.isInteger(numeric)) return fallback;
  return Math.min(maximum, Math.max(minimum, numeric));
}

function assertSlug(slug) {
  const normalized = String(slug ?? "").trim().toLowerCase();
  if (!/^[a-z0-9][a-z0-9-]{0,199}$/.test(normalized)) {
    throw new TypeError("Plugin slug must contain only lowercase letters, numbers, and hyphens");
  }
  return normalized;
}

function sourceRecord({ url, title, publishedAt = null, raw, sourceClass = "official-documentation" }) {
  return {
    url,
    title,
    sourceClass,
    publishedAt,
    retrievedFrom: "WordPress.org API",
    raw
  };
}

export class WordPressOfficialAdapter {
  constructor({ http = new SafeHttpClient({ allowedOrigins: [API_ORIGIN] }) } = {}) {
    this.http = http;
  }

  async collectCoreVersions() {
    const endpoint = `${API_ORIGIN}/core/version-check/1.7/`;
    const response = await this.http.getJson(endpoint);
    const offers = Array.isArray(response.data?.offers) ? response.data.offers : [];

    return sourceRecord({
      url: response.url,
      title: "WordPress core version offers",
      sourceClass: "release-notes-or-changelog",
      raw: offers.map((offer) => ({
        response: offer.response ?? null,
        download: offer.download ?? null,
        locale: offer.locale ?? null,
        packages: offer.packages ?? null,
        current: offer.current ?? null,
        version: offer.version ?? null,
        phpVersion: offer.php_version ?? null,
        mysqlVersion: offer.mysql_version ?? null,
        newBundles: offer.new_bundles ?? null
      }))
    });
  }

  async searchPlugins(query, { page = 1, perPage = 24 } = {}) {
    const normalizedQuery = String(query ?? "").trim();
    if (!normalizedQuery) throw new TypeError("Plugin search query is required");

    const endpoint = new URL(`${API_ORIGIN}/plugins/info/1.2/`);
    endpoint.searchParams.set("action", "query_plugins");
    endpoint.searchParams.set("request[search]", normalizedQuery.slice(0, 200));
    endpoint.searchParams.set("request[page]", String(integerWithin(page, 1, 100, 1)));
    endpoint.searchParams.set("request[per_page]", String(integerWithin(perPage, 1, 100, 24)));
    endpoint.searchParams.set("request[fields][sections]", "0");
    endpoint.searchParams.set("request[fields][description]", "1");
    endpoint.searchParams.set("request[fields][icons]", "1");

    const response = await this.http.getJson(endpoint);
    const plugins = Array.isArray(response.data?.plugins) ? response.data.plugins : [];

    return sourceRecord({
      url: response.url,
      title: `WordPress plugin search: ${normalizedQuery}`,
      raw: {
        info: response.data?.info ?? {},
        plugins: plugins.map((plugin) => ({
          name: plugin.name ?? null,
          slug: plugin.slug ?? null,
          version: plugin.version ?? null,
          author: plugin.author ?? null,
          requires: plugin.requires ?? null,
          tested: plugin.tested ?? null,
          requiresPhp: plugin.requires_php ?? null,
          rating: plugin.rating ?? null,
          ratings: plugin.ratings ?? null,
          numRatings: plugin.num_ratings ?? null,
          supportThreads: plugin.support_threads ?? null,
          supportThreadsResolved: plugin.support_threads_resolved ?? null,
          activeInstalls: plugin.active_installs ?? null,
          downloaded: plugin.downloaded ?? null,
          lastUpdated: plugin.last_updated ?? null,
          added: plugin.added ?? null,
          homepage: plugin.homepage ?? null,
          shortDescription: plugin.short_description ?? plugin.description ?? null,
          icons: plugin.icons ?? null
        }))
      }
    });
  }

  async getPluginInformation(slug) {
    const normalizedSlug = assertSlug(slug);
    const endpoint = new URL(`${API_ORIGIN}/plugins/info/1.2/`);
    endpoint.searchParams.set("action", "plugin_information");
    endpoint.searchParams.set("request[slug]", normalizedSlug);
    endpoint.searchParams.set("request[fields][sections]", "1");
    endpoint.searchParams.set("request[fields][versions]", "0");
    endpoint.searchParams.set("request[fields][contributors]", "1");
    endpoint.searchParams.set("request[fields][ratings]", "1");
    endpoint.searchParams.set("request[fields][icons]", "1");

    const response = await this.http.getJson(endpoint);
    if (!response.data || response.data.error) {
      throw new Error(`WordPress.org did not return plugin information for ${normalizedSlug}`);
    }

    return sourceRecord({
      url: response.url,
      title: `WordPress plugin information: ${normalizedSlug}`,
      raw: response.data
    });
  }
}

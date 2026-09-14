import { createHash } from "node:crypto";
import {
  acknowledge,
  createCommandEnvelope,
  normalizeResearchRequest,
  stableStringify
} from "./contracts.mjs";
import { evaluateReleaseProof } from "./release-proof.mjs";

function digest(prefix, value) {
  return `${prefix}_${createHash("sha256").update(stableStringify(value)).digest("hex").slice(0, 16)}`;
}

function normalizeUrl(raw) {
  const url = new URL(raw);
  url.hash = "";
  for (const key of [...url.searchParams.keys()]) {
    if (key.startsWith("utm_") || ["ref", "source"].includes(key)) url.searchParams.delete(key);
  }
  return url.toString();
}

function dedupeClaims(claims) {
  const seen = new Map();
  for (const claim of claims) {
    const key = claim.statement.toLowerCase().replace(/\s+/g, " ").trim();
    const current = seen.get(key);
    if (!current || claim.confidence > current.confidence) seen.set(key, claim);
  }
  return [...seen.values()];
}

function findContradictions(claims) {
  const bySubject = new Map();
  for (const claim of claims.filter((item) => item.subject && item.stance)) {
    const values = bySubject.get(claim.subject) ?? [];
    values.push(claim);
    bySubject.set(claim.subject, values);
  }
  return [...bySubject.entries()].flatMap(([subject, values]) => {
    const stances = new Set(values.map((item) => item.stance));
    if (stances.size < 2) return [];
    return [{
      id: digest("contradiction", { subject, claimIds: values.map((item) => item.id).sort() }),
      subject,
      claimIds: values.map((item) => item.id),
      stances: [...stances].sort(),
      material: values.some((item) => item.material !== false)
    }];
  });
}

export class ResearchEngine {
  constructor({ discovery, fetcher, extractor, synthesizer, policy = {}, clock = () => new Date() }) {
    for (const [name, adapter] of Object.entries({ discovery, fetcher, extractor, synthesizer })) {
      if (!adapter) throw new TypeError(`${name} adapter is required`);
    }
    this.discovery = discovery;
    this.fetcher = fetcher;
    this.extractor = extractor;
    this.synthesizer = synthesizer;
    this.policy = policy;
    this.clock = clock;
  }

  async run(input, options = {}) {
    const request = normalizeResearchRequest(input);
    const issuedAt = this.clock().toISOString();
    const command = createCommandEnvelope("research.run", request, { ...options, issuedAt });
    const accepted = acknowledge(command, "accepted", { recordedAt: issuedAt });

    const discoveryBatches = await Promise.all(
      request.queries.map((query) => this.discovery.search({ query, request }))
    );
    const discoveries = discoveryBatches.flat();
    const urls = [...new Set(discoveries.map((item) => normalizeUrl(item.url)))];

    const pages = await Promise.all(
      urls.map(async (url) => {
        const result = await this.fetcher.fetch({ url, request });
        return { ...result, url, accessedAt: result.accessedAt ?? this.clock().toISOString() };
      })
    );

    const rawClaims = (await Promise.all(
      pages.map(async (page) => {
        const extracted = await this.extractor.extract({ page, request });
        return extracted.claims.map((claim) => ({
          ...claim,
          id: claim.id ?? digest("claim", {
            statement: claim.statement,
            sourceUrl: page.url,
            quote: claim.quote
          }),
          sourceUrl: page.url,
          accessedAt: claim.accessedAt ?? page.accessedAt,
          confidence: Number(claim.confidence)
        }));
      })
    )).flat();

    const claims = dedupeClaims(rawClaims);
    const sources = pages.map((page) => ({
      id: digest("source", page.url),
      url: page.url,
      title: page.title ?? "",
      sourceClass: page.sourceClass ?? "unclassified",
      publishedAt: page.publishedAt ?? null,
      accessedAt: page.accessedAt
    }));
    const contradictions = findContradictions(claims);
    const synthesis = await this.synthesizer.synthesize({ request, sources, claims, contradictions });

    const artifactId = digest("research", {
      request,
      claims: claims.map((claim) => claim.id),
      synthesis
    });
    const artifact = {
      artifactVersion: "1.0.0",
      artifactId,
      createdAt: this.clock().toISOString(),
      request,
      sources,
      claims,
      contradictions,
      synthesis
    };
    artifact.releaseProof = evaluateReleaseProof(artifact, this.policy, this.clock());

    return {
      command,
      acknowledgements: [
        accepted,
        acknowledge(command, artifact.releaseProof.status === "PASS" ? "succeeded" : "failed", {
          recordedAt: this.clock().toISOString(),
          artifactId,
          error: artifact.releaseProof.status === "PASS" ? null : {
            code: "RELEASE_PROOF_FAILED",
            blockers: artifact.releaseProof.blockers
          }
        })
      ],
      artifact
    };
  }
}

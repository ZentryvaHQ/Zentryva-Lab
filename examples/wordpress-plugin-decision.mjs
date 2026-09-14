import request from "./wordpress-plugin-decision.request.json" with { type: "json" };
import { ResearchEngine } from "../src/pipeline.mjs";

const now = new Date("2026-09-14T12:00:00.000Z");
const pages = new Map([
  ["https://developer.wordpress.org/block-editor/reference-guides/block-api/block-metadata/", {
    title: "Block metadata",
    sourceClass: "official-documentation",
    publishedAt: "2026-08-01T00:00:00.000Z",
    claims: [{
      statement: "WordPress exposes block metadata as a native registration contract.",
      quote: "Block metadata provides the canonical metadata needed to register a block.",
      confidence: 0.96,
      subject: "canonical-representation",
      stance: "native-block-contract",
      tags: ["time-sensitive"]
    }]
  }],
  ["https://make.wordpress.org/core/2026/08/01/wordpress-7-1-field-guide/", {
    title: "WordPress 7.1 field guide",
    sourceClass: "release-notes-or-changelog",
    publishedAt: "2026-08-01T00:00:00.000Z",
    claims: [{
      statement: "Core editor changes can affect plugin integration behavior across releases.",
      quote: "Developers should test editor integrations against the release changes.",
      confidence: 0.92,
      subject: "upgrade-risk",
      stance: "continuous-compatibility-testing",
      tags: ["time-sensitive"]
    }]
  }],
  ["https://wordpress.org/support/topic/page-builder-content-portability/", {
    title: "Page builder content portability",
    sourceClass: "issue-tracker-or-support-forum",
    publishedAt: "2026-07-20T00:00:00.000Z",
    claims: [{
      statement: "Making a third-party builder the canonical store creates portability risk.",
      quote: "Content may require cleanup or rebuilding when the builder is removed.",
      confidence: 0.78,
      subject: "canonical-representation",
      stance: "avoid-builder-canonical",
      tags: ["time-sensitive"]
    }]
  }]
]);

const discovery = {
  async search() {
    return [...pages.keys()].map((url) => ({ url }));
  }
};
const fetcher = {
  async fetch({ url }) {
    const page = pages.get(url);
    return { ...page, url, body: page.title, accessedAt: now.toISOString() };
  }
};
const extractor = {
  async extract({ page }) {
    return { claims: page.claims.map((claim) => ({ ...claim, publishedAt: page.publishedAt })) };
  }
};
const synthesizer = {
  async synthesize({ claims, contradictions }) {
    return {
      recommendation: "Keep ZWIR as the canonical representation and implement WordPress as a native block-first delivery adapter.",
      supportingClaimIds: claims.map((claim) => claim.id),
      resolvedContradictionIds: contradictions.map((item) => item.id),
      implications: [
        "Map validated ZWIR components to native blocks, custom blocks, and templates.",
        "Treat third-party builders as optional delivery adapters, never the master data model.",
        "Run compatibility research and ReleaseProof before WordPress core or plugin upgrades."
      ]
    };
  }
};

const policy = {
  minimumDistinctDomains: 3,
  minimumClaims: 3,
  maximumSourceAgeDays: 365,
  requiredSourceClasses: [
    "official-documentation",
    "release-notes-or-changelog",
    "issue-tracker-or-support-forum"
  ],
  failOnUnresolvedMaterialContradiction: true
};

const result = await new ResearchEngine({
  discovery,
  fetcher,
  extractor,
  synthesizer,
  policy,
  clock: () => now
}).run(request);

console.log(JSON.stringify(result, null, 2));
if (result.artifact.releaseProof.status !== "PASS") process.exitCode = 1;

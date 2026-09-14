import test from "node:test";
import assert from "node:assert/strict";
import { ResearchEngine } from "../src/pipeline.mjs";

const fixed = new Date("2026-09-14T12:00:00.000Z");

function engine(overrides = {}) {
  const pages = [
    { url: "https://docs.example.test/a", sourceClass: "official-documentation" },
    { url: "https://changes.example.test/b", sourceClass: "release-notes-or-changelog" },
    { url: "https://forum.example.test/c", sourceClass: "issue-tracker-or-support-forum" }
  ];
  return new ResearchEngine({
    discovery: { async search() { return pages; } },
    fetcher: {
      async fetch({ url }) {
        const page = pages.find((item) => item.url === url);
        return { ...page, title: url, publishedAt: "2026-09-01T00:00:00.000Z" };
      }
    },
    extractor: {
      async extract({ page }) {
        return { claims: [{
          statement: `Evidence from ${page.url}`,
          quote: `Quoted evidence from ${page.url}`,
          confidence: 0.9,
          publishedAt: page.publishedAt,
          subject: page.url,
          stance: "supports",
          tags: ["time-sensitive"]
        }] };
      }
    },
    synthesizer: {
      async synthesize({ claims }) {
        return {
          recommendation: "Use the evidence-backed option.",
          supportingClaimIds: claims.map((claim) => claim.id),
          resolvedContradictionIds: []
        };
      }
    },
    policy: {
      minimumDistinctDomains: 3,
      minimumClaims: 3,
      maximumSourceAgeDays: 365,
      requiredSourceClasses: [
        "official-documentation",
        "release-notes-or-changelog",
        "issue-tracker-or-support-forum"
      ]
    },
    clock: () => fixed,
    ...overrides
  });
}

test("creates deterministic idempotency keys and passes complete evidence", async () => {
  const request = { question: "Which WordPress integration should we use?" };
  const first = await engine().run(request);
  const second = await engine().run(request);

  assert.equal(first.command.idempotencyKey, second.command.idempotencyKey);
  assert.equal(first.artifact.releaseProof.status, "PASS");
  assert.equal(first.acknowledgements.at(-1).state, "succeeded");
  assert.equal(first.artifact.claims.length, 3);
});

test("fails closed when required evidence classes are missing", async () => {
  const result = await engine({
    policy: {
      minimumDistinctDomains: 3,
      minimumClaims: 3,
      requiredSourceClasses: ["security-advisory"]
    }
  }).run({ question: "Can this be promoted?" });

  assert.equal(result.artifact.releaseProof.status, "FAIL");
  assert.equal(result.acknowledgements.at(-1).state, "failed");
  assert.ok(result.artifact.releaseProof.blockers.some((item) => item.code === "MISSING_SOURCE_CLASS"));
});

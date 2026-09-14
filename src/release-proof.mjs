function daysBetween(left, right) {
  return Math.floor(Math.abs(right.getTime() - left.getTime()) / 86_400_000);
}

export function evaluateReleaseProof(artifact, policy = {}, now = new Date()) {
  const blockers = [];
  const warnings = [];
  const claims = artifact.claims ?? [];
  const sources = artifact.sources ?? [];

  if (claims.length < (policy.minimumClaims ?? 1)) {
    blockers.push({ code: "INSUFFICIENT_CLAIMS", detail: `Expected at least ${policy.minimumClaims ?? 1} claims` });
  }

  const domains = new Set(sources.map((source) => {
    try { return new URL(source.url).hostname; } catch { return null; }
  }).filter(Boolean));
  if (domains.size < (policy.minimumDistinctDomains ?? 1)) {
    blockers.push({ code: "INSUFFICIENT_DOMAIN_DIVERSITY", detail: `Found ${domains.size} distinct domains` });
  }

  for (const requiredClass of policy.requiredSourceClasses ?? []) {
    if (!sources.some((source) => source.sourceClass === requiredClass)) {
      blockers.push({ code: "MISSING_SOURCE_CLASS", detail: requiredClass });
    }
  }

  for (const claim of claims) {
    for (const field of ["statement", "sourceUrl", "quote", "accessedAt"]) {
      if (!claim[field]) blockers.push({ code: "INCOMPLETE_CLAIM", claimId: claim.id, detail: field });
    }
    if (!Number.isFinite(claim.confidence) || claim.confidence < 0 || claim.confidence > 1) {
      blockers.push({ code: "INVALID_CONFIDENCE", claimId: claim.id });
    }
    if (claim.tags?.includes("time-sensitive")) {
      if (!claim.publishedAt) {
        blockers.push({ code: "MISSING_PUBLICATION_DATE", claimId: claim.id });
      } else if (daysBetween(new Date(claim.publishedAt), now) > (policy.maximumSourceAgeDays ?? 365)) {
        blockers.push({ code: "STALE_TIME_SENSITIVE_CLAIM", claimId: claim.id });
      }
    }
  }

  const claimIds = new Set(claims.map((claim) => claim.id));
  for (const id of artifact.synthesis?.supportingClaimIds ?? []) {
    if (!claimIds.has(id)) blockers.push({ code: "UNKNOWN_SUPPORTING_CLAIM", claimId: id });
  }

  const material = (artifact.contradictions ?? []).filter((item) => item.material !== false);
  const resolved = new Set(artifact.synthesis?.resolvedContradictionIds ?? []);
  for (const contradiction of material) {
    if (!resolved.has(contradiction.id)) {
      const finding = { code: "UNRESOLVED_MATERIAL_CONTRADICTION", contradictionId: contradiction.id };
      if (policy.failOnUnresolvedMaterialContradiction === false) warnings.push(finding);
      else blockers.push(finding);
    }
  }

  return {
    status: blockers.length === 0 ? "PASS" : "FAIL",
    evaluatedAt: now.toISOString(),
    blockers,
    warnings
  };
}

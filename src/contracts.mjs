import { createHash, randomUUID } from "node:crypto";

export const ACK_STATES = Object.freeze([
  "accepted",
  "running",
  "succeeded",
  "failed"
]);

function canonical(value) {
  if (Array.isArray(value)) return value.map(canonical);
  if (value && typeof value === "object") {
    return Object.fromEntries(
      Object.entries(value)
        .filter(([, item]) => item !== undefined)
        .sort(([left], [right]) => left.localeCompare(right))
        .map(([key, item]) => [key, canonical(item)])
    );
  }
  return value;
}

export function stableStringify(value) {
  return JSON.stringify(canonical(value));
}

export function normalizeResearchRequest(input) {
  if (!input || typeof input !== "object") {
    throw new TypeError("Research request must be an object");
  }
  const question = String(input.question ?? "").trim();
  if (!question) throw new TypeError("question is required");

  const queries = [...new Set(
    (input.queries?.length ? input.queries : [question])
      .map((value) => String(value).trim())
      .filter(Boolean)
  )];

  return {
    requestVersion: "1.0.0",
    question,
    decisionContext: String(input.decisionContext ?? "").trim(),
    queries,
    constraints: {
      includeDomains: [...new Set(input.constraints?.includeDomains ?? [])].sort(),
      excludeDomains: [...new Set(input.constraints?.excludeDomains ?? [])].sort(),
      maxSourceAgeDays: Number(input.constraints?.maxSourceAgeDays ?? 365)
    },
    requiredSourceClasses: [...new Set(input.requiredSourceClasses ?? [])].sort(),
    metadata: input.metadata ?? {}
  };
}

export function createCommandEnvelope(commandType, payload, options = {}) {
  const normalizedPayload = canonical(payload);
  const idempotencyKey = options.idempotencyKey ?? createHash("sha256")
    .update(stableStringify({ commandType, payload: normalizedPayload }))
    .digest("hex");

  return {
    envelopeVersion: "1.0.0",
    commandId: options.commandId ?? randomUUID(),
    commandType,
    idempotencyKey,
    issuedAt: options.issuedAt ?? new Date().toISOString(),
    correlationId: options.correlationId ?? randomUUID(),
    payload: normalizedPayload
  };
}

export function acknowledge(envelope, state, details = {}) {
  if (!ACK_STATES.includes(state)) throw new TypeError(`Unknown acknowledgement state: ${state}`);
  return {
    acknowledgementVersion: "1.0.0",
    commandId: envelope.commandId,
    idempotencyKey: envelope.idempotencyKey,
    state,
    recordedAt: details.recordedAt ?? new Date().toISOString(),
    artifactId: details.artifactId ?? null,
    error: details.error ?? null
  };
}

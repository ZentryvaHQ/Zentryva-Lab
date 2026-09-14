# ADR-0001: Research Intelligence first vertical slice

Status: Accepted

Date: 2026-09-14

## Decision

Implement Research Intelligence as a shared capability owned by Search & Content Intelligence. The first pilot answers a WordPress plugin or integration decision and returns a structured, cited artifact governed by ReleaseProof.

The Website Factory keeps ZWIR as its canonical representation. WordPress is a delivery adapter that maps validated components to native blocks, custom blocks, and templates. Third-party page builders may be optional adapters but are not the canonical store.

## Pipeline

1. Normalize intake.
2. Discover across official documentation, release notes, security sources, repositories, issue trackers, forums, and independent analysis.
3. Fetch and timestamp source material.
4. Extract atomic claims with direct evidence.
5. Deduplicate claims and group contradictions.
6. Synthesize a recommendation with explicit supporting claim IDs.
7. Fail closed through ReleaseProof.

## Model policy

The AI Router policy selects the strongest available reasoning profile for planning, extraction, contradiction analysis, and synthesis. Fallback is explicit and may not happen silently.

## Consequences

The service is auditable and reusable by Website Factory, Plugin Factory, GPT Maker, NetworkOps, and other managed products. Live adapters, credentials, persistence, queues, and Desktop Bridge acceptance remain separate activation work and cannot be reported as passed until executed evidence exists.

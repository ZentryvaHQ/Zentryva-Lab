# Zentryva Lab

Engineering workspace for Zentryva platform services.

## Research Intelligence Service

This branch contains the first P0 vertical slice for a shared research capability owned by Search & Content Intelligence.

Implemented:

- durable command envelopes with deterministic idempotency keys;
- normalized research requests;
- pluggable discovery, fetch, extraction, and synthesis adapters;
- evidence-level claims with URLs, quotations, timestamps, and confidence;
- deterministic deduplication and contradiction grouping;
- a fail-closed ReleaseProof gate;
- a WordPress plugin/integration decision pilot with mocked adapters;
- an AI Router policy targeting the strongest available reasoning profile.

Not yet activated:

- live search, browser, forum, GitHub issue, or WordPress.org adapters;
- live model-provider credentials;
- scheduled refreshes;
- production persistence and job queues;
- runtime acceptance on the Windows/Desktop Bridge.

## Requirements

Node.js 22 or newer.

## Commands

- npm test
- npm run pilot

The pilot uses deterministic fixtures so its contract and evidence gate can be tested without network access. Live adapters must not be marked production-ready until executed evidence passes ReleaseProof.

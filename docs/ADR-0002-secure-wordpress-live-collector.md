# ADR-0002: Secure WordPress official-source collector

Status: Accepted

Date: 2026-09-14

## Decision

Add a read-only live collector for WordPress.org's official core and plugin APIs before enabling broad web crawling. The adapter uses a strict HTTPS origin allowlist, validates redirects, caps redirects and response sizes, applies timeouts, prohibits embedded URL credentials, bounds query parameters, and returns raw evidence separately from AI-generated claims.

## Why this comes first

Official APIs provide deterministic version and plugin compatibility data with less ambiguity than search snippets or forum posts. They are necessary but not sufficient for deep research. Broad discovery, GitHub issues, support forums, security databases, and independent testing remain additional evidence classes.

## Security boundaries

- GET requests only.
- HTTPS only.
- Exact-origin allowlist.
- Manual redirect validation.
- Response-size and redirect limits.
- Request timeout.
- Input validation and bounded pagination.
- No secrets in URLs.
- Read-only data collection.
- No automatic production changes.

## Promotion rule

Passing adapter tests proves contract and policy behavior only. Production qualification also requires executed live-source evidence, failure-path tests, rate-limit handling, independent verification, and ReleaseProof approval.

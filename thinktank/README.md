# Zentryva Think Tank / Opportunity Radar v1.0.0

Evidence-first strategic research, opportunity detection, challenge, experiment control, and promotion gating for Zentryva.

## What v1.0.0 implements

- Research job, source, passage, atomic claim, evidence-edge, failure-case, recommendation, opportunity, critique, and experiment contracts.
- Deep/standard/quick/forensic research policy profiles with explicit budgets and diminishing-return stopping rules.
- Evidence graph with claim-level citation coverage, entailment-strength, contradiction, source-class, and corroboration gates.
- Opportunity scoring plus independent deterministic Critic Council.
- Reversible experiment state machine; promotion requires measured improvement, ReleaseProof PASS, durable evidence refs, and verified rollback.
- Safe-fetch boundary with HTTP/HTTPS allowlist, credential stripping, port restrictions, DNS-injected SSRF checks, private/loopback/link-local/metadata blocking, and redirect revalidation.
- Prompt-injection markers and explicit untrusted-content wrapping.
- SQLite knowledge store with WAL, SHA-256 payload integrity, append-only hash-chained audit log, backup, restore, and integrity checks.
- Provider-neutral adapter contracts for search, fetch, and model roles.
- Opportunity Radar disposition: EXPERIMENT only when score/evidence/risk/critic gates pass; otherwise RESEARCH.
- Automated ReleaseProof gate runner and regression suite.

## Deliberate boundaries

v1.0.0 does **not** hard-code paid model/search credentials, mutate production systems, or auto-promote research findings into production. External providers are injected behind adapter contracts. This keeps the service reusable by Controller, Router, Website Factory, Plugin Factory, NetworkOps, and future Zentryva products.

## Install and test

```bash
python -m venv .venv
. .venv/bin/activate  # Windows: .venv\\Scripts\\activate
python -m pip install --no-build-isolation -e .
pytest -o addopts= -q
python scripts/security_scan.py
python scripts/run_release_gate.py
zthink demo --db demo.db
```

## Release standard

A release is not PASS because code compiles. `scripts/run_release_gate.py` requires all gates below to pass:

1. schema/compile
2. security
3. evidence
4. opportunity
5. experiment
6. storage
7. backup/restore
8. packaging
9. regression
10. aggregate ReleaseProof

See `docs/ARCHITECTURE.md`, `docs/THREAT_MODEL.md`, `docs/OPERATIONS.md`, and `evidence/RELEASE_GATE_v1.0.0.json`.

# Zentryva AI Marketing Center — authoritative MARKETING_STATUS

Last Activity: 2026-09-25T10:43:46.268872+00:00. Pilot: Salem Botanicals.
Repository: https://github.com/ZentryvaHQ/Zentryva-Lab.git
Branch: mc-r1-salem-sprint.
Tested Marketing source: 5268e808a9cd79aeabf55db35d8db84fcf5bf0bd.
Tested shared source: 9ab3dcd623b3a5b27738bed52b36a5285f2b4cb8,
branch worker/salem-local-control-20260925 in Zentryva-Command-Center-Core.

Release readiness: PASS — SYNTHETIC LOCAL BETA. Commercial/live release: HOLD.
No production publishing, deployment or spend. No background service is running.

| Work | Priority | Status | Evidence | Remaining work |
|---|---|---|---|---|
| MC-002–004 contracts, tenant and identity | P0 | VERIFIED LOCAL | Final 79-test Marketing suite | Preserve contracts |
| MC-005–007 research, competitors, strategy | P0 | VERIFIED LOCAL | Structured synthetic evidence and traceable decisions | Approved real pilot data later |
| MC-008–016 complete Salem shadow loop | P0 | VERIFIED LOCAL BETA | Exact archive runs SHADOW_COMPLETE, zero spend, no publication | MC-017 live validation later |
| ML-001–003 Core and six modules | P0 | VERIFIED LOCAL | Full regression and artifact runtime provenance | Preserve module boundaries |
| ML-004 shared control and recovery | P0 | VERIFIED COOPERATIVE LOCAL | 79 Marketing + 58 shared tests; pause, crash, response-loss and restart fencing | Arbitrary provider preemption/distributed service operation outside local qualification |
| ML-005 security qualification | P0 | VERIFIED SCOPED LOCAL | Adversarial tests, independent review; 2 P2 issues fixed and retested | Separate live/production security qualification |
| MC-017 controlled live pilot | P0 | AWAITING RICHARD — LATER | Local beta ready for inspection | Approved real brand/product facts and baseline, secure authorized accounts, explicit launch approval |
| ML-006 commercialization | P1 | DEFERRED | R1 scope freeze | No SaaS expansion |
| ML-007 expansion | P2 | DEFERRED | R1 scope freeze | Qualified V1 first |

## Current checkpoint

The former running-state/pause/recovery dependency is implemented in an isolated
shared checkout. Worker-scoped status, cooperative control checks and short fenced
sessions support explicit recovery. Owner pauses cannot be overridden by workers.
A real subprocess crash and lost HTTP responses were tested; verified stages are
reused and terminal output tampering is rejected. New runs reset the stall clock;
monotonic expiry and server-process epochs prevent expired-session revival.

Final suites: 79/79 Marketing and 58/58 shared, zero failures or skips. The legacy
reference remains unchanged at 6c50292cf91fb4ea94f08e833e899d555290b714 for regression.
All temporary HTTP listeners used by tests and the launcher are shut down on exit.

Artifact-bound proof: evidence/supervised-beta/ReleaseProof.json (122 files).
Archive: evidence/supervised-beta/salem-local-beta-20260925.zip, 142214 bytes.
SHA256: 42ff8e9b13bcf0018ab577c3698794d88c8953b55a55b83a7edc3677c303644c.
The exact extracted archive completed the no-publish loop. Its package manifest
binds both commits; its runtime source digest matches the tested source checkout.
Run instructions: docs/LOCAL-BETA.md. Entry point: python -m mc.beta.

The prior formal source audit stays scoped to 7d6c60b. Later changes have their own
independent review and tests, not an invented extension of that sealed audit.

## Boundaries and next step

Canonical sole writer: 01a0c8ac-0afe-7572-b3ab-99cda493e643.
Resume Marketing Center P0 work remains archived/reference-only. Marketing is P0;
no other Zentryva project was started during this qualification.

The usable synthetic local beta is complete to the authorized no-publish boundary.
Next pilot step: supply approved actual Salem facts/baseline through a safe intake,
then qualify provider access separately. MC-017 launch remains gated. No invented
real data, platform credentials, commercial readiness or live performance claims.

Technical limits remain explicit: one server process, cooperative stage boundaries,
no arbitrary external provider cancellation, no distributed state service or
crash-atomic state/event transaction. Use the loopback beta launcher; the shared
legacy server executable binds all interfaces and is not the qualified launcher.

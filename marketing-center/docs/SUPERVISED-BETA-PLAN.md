# Local supervised beta plan — 2026-09-25

Resume dcc84cb; shared base 6c50292 (fresh fetch confirms no newer branch work).
Scope: synthetic Salem loop, real loopback HTTP, no live providers/publishing/spend.
Architecture: shared Command Center owns worker-scoped status and short leases.
New cooperative-v1 requests use acquire/pulse/release with opaque per-attempt session
IDs; expired sessions cannot store results or complete. Worker pause is cooperative
at stage boundaries, never claimed as cancellation of arbitrary provider calls.
A pause exits retaining immutable stage checkpoints. Resume requires RUNNING desired
state. Crash takeover waits for lease expiry; deterministic pure stages may replay.
Read-only reconciliation handles lost acknowledgement/completion responses. One-shot
invocations continue to completion or an explicit pause, no duplicate scheduler.
Legacy one-shot protocol remains regression tested separately.

1. Shared protocol: scoped reads, acquire/lease/guard, authorization, stale writer tests.
2. Marketing controlled execution: stage guards, resume, terminal reconciliation, CLI.
3. Real HTTP integration/failure/recovery/security regression and independent review.
4. Commit both source revisions, rerun suites; bind ReleaseProof to bytes/logs and
   update authoritative MARKETING_STATUS. Local beta qualification is not production.

Ruling: proceed under explicit no-routine-prompts authority; no staged approval stops.
Pre-flight: new protocol requires both repositories; pin shared tested commit in
Marketing tests. Old reference remains unmodified for legacy regression.

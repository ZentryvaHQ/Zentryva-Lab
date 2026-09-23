Current authoritative status: [MARKETING_STATUS.md](MARKETING_STATUS.md). The following is the preserved R1 shadow checkpoint.

# MC-R1-SALEM-001 Tracker

Updated 2026-09-22: internal shadow loop working; production R1 pilot is NOT complete.
Evidence: `evidence/13-review-fixes-green.log` (29 tests), preserved shadow run and `docs/EXECUTION-LEDGER.md`.

| ID | Work | Status | Gate |
|---|---|---|---|
| MC-001 | Architecture boundary | VERIFIED | Command Center/Marketing Center split recorded |
| MC-002 | Command Center contract | VERIFIED | evidence/02-contracts-green.log; negative validation checks |
| MC-003 | Tenant core | VERIFIED | Tenant schema; safety policy checks |
| MC-004 | Traceable marketing identity | VERIFIED | evidence/02-contracts-green.log; negative validation checks |
| MC-005 | Research evidence engine | VERIFIED (SHADOW) | Imported records validated; source hashes/freshness |
| MC-006 | Competitor intelligence | VERIFIED (SHADOW) | Structured observations linked to evidence |
| MC-007 | Strategy engine | VERIFIED (SHADOW) | Traceability, abstention, tenant isolation tested |
| MC-008 | Campaign planner | VERIFIED (SHADOW) | Strategy -> audience/channel/hypothesis |
| MC-009 | Content engine | VERIFIED (SHADOW) | Allowlisted copy, CTA, tracking URL, creative brief |
| MC-010 | Brand/compliance gates | VERIFIED (SHADOW) | Mechanical checks; live human review still required |
| MC-011 | Publishing contract | VERIFIED (HANDOFF) | Manual file handoff; no live publishing adapter |
| MC-012 | Delivery verification | VERIFIED (NEGATIVE STATES) | Acceptance does not prove delivery; auth/retry/tracking errors; live rendering UNVERIFIED |
| MC-013 | Analytics normalization | VERIFIED (SHADOW) | Synthetic metrics; identity/count checks |
| MC-014 | Attribution | VERIFIED (SHADOW) | Four classes; no real ROI claimed |
| MC-015 | Learning/optimization | VERIFIED (SHADOW) | Results change next recommendation; experiment and memory |
| MC-016 | Salem shadow run | VERIFIED | Full no-publish CLI loop, persisted evidence and dashboard |
| MC-017 | Salem controlled pilot | BLOCKED_AWAITING_RICHARD | Production approval/access only at launch gate |

## Hard blocker policy
Owner-dependent production access/approval is isolated at MC-017. It does not block MC-001 through MC-016.

Live Command Center integration, actual Salem source/brand/product facts and baseline, public rendering and measured business uplift remain unverified. Mechanical compliance checks are not legal approval. No production changes or spend.

Resume using `docs/RUNBOOK.md`. Minor deferred: receipt importer lacks full campaign/content identity checks, but cannot verify publication and is not connected to a publisher.



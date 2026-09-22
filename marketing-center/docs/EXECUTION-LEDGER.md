# MC-R1-SALEM-001 execution ledger

Base: bc9ec7b7cf36d4400a376be0f0345fb8e4dc0252 (verified remote 2026-09-22).
Authority: Project Pulse conversation 6ab1f757-840c-83ea-a6ca-9df61eacd218; master prompt and accelerated sprint, plus current execution request.
Plan: verify MC-002–004; implement/test MC-005–007; then MC-008–016 full shadow loop; independent review and preserve checkpoint.

Ruling: Use Python and installed JSON Schema validator for the local portable harness; the baseline has no runtime or package conventions. Cost if wrong: adapter/packaging migration.
Ruling: Synthetic research and analytics are explicitly labeled test inputs. No real Salem research, performance, approval, or publication may be inferred from the shadow run. Production integration remains unverified.
Ruling: Preserve logs and checkpoints rather than deleting the execution ledger; user explicitly requires provenance and checkpoints.
Pre-flight: evidence -> strategy -> campaign -> content -> handoff -> delivery -> metrics -> attribution -> learning share tenant, objective, record references and campaign/content identity. The runner must reject cross-tenant input and preserve the reference chain.
Pre-flight: Command Center status is a temporary file adapter, not a scheduler, queue, or permanent evidence service.
MC-002–004: verified with 3 contract tests. Initial tests found empty identity/objective acceptance, absent tenant schema, and missing date-format dependency. Fixed and retested; 01-contracts-red.log -> 02-contracts-green.log. Schema verification does not verify live Command Center integration or Salem business data.
MC-005–007: 8/8 total tests pass (03-intelligence-red.log -> 04-intelligence-green.log). Structured evidence import, deterministic decisions, stale/low-quality abstention, and tenant checks. Ruling: rule-based free shadow decision engine and structured imports establish an executable baseline; autonomous web acquisition and provider-generated creative remain future adapters, not verified integrations.

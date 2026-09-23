# Local shadow recovery and qualification

All six bundled modules now execute through the tenant registry: intelligence, planning, content/review, publishing/delivery, measurement/attribution, optimization. The default and previous intelligence-only configuration shorthand enable the complete fixed shadow pipeline. Explicit full selections must include every stage. There are no arbitrary customer imports or paid providers.

The local development adapter stores completed pure operation results under `<output>/<tenant>/.checkpoints/<run-id>`. Step identities include operation arguments; run identity includes source/schema/module/runtime fingerprints. Each step writes an atomic, flushed JSON checkpoint with a checksum. RUNNING/FAILED/COMPLETE and attempt counts survive process restart. Exception payloads are never stored. Checksums detect accidental corruption, not a malicious local user rewriting both content and hash.

An OS-held writer lock rejects overlapping execution of the same run and is automatically released on process exit. Rerunning the same input with the same `--at` timestamp resumes completed operations. This is not a scheduler; the Command Center adapter or an explicit local rerun initiates another attempt. Each failed/interrupted step has a three-attempt budget. Exhaustion requires diagnosis and a corrected input or implementation; do not delete evidence to disguise failure.

A 60-second deadline is checked before and after stage calls. It is a **soft boundary**, not preemptive cancellation of a stuck Python function. The trusted bundled functions perform no network calls. Provider timeouts, cancellation and automatic retry scheduling remain Command Center integration requirements before live provider use. No independent global supervisor was introduced.

Known credential-shaped fields and credential-bearing URLs are rejected before snapshots/checkpoints are written. This is not a universal secret or personal-data detector; keep shadow inputs synthetic and non-secret. Receipt import now requires matching tenant, campaign and content identities, and never certifies real publication.

The supported trust boundary is a single-user local development checkout. Hostile Python plugins, multi-user filesystem access controls, encryption at rest and production RBAC are not qualified. The original source schemas, safety policies, zero spend and no-production gates remain in force.

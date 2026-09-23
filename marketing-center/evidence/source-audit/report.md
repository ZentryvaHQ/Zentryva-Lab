# Security Review: work

## Scope

Offline source audit of the current single-user local Marketing Center shadow workflow at 7d6c60bc245cd39f9c533bb5957b05e5675ba763.

- Scan mode: scoped_path
- Target kind: git_revision
- Target ID: target_sha256_f36ffc09c3952491edeaa6c9e370dfa50682c7641c279c81ef92a02350101ea8
- Revision: 7d6c60bc245cd39f9c533bb5957b05e5675ba763
- Inventory strategy: scoped_path
- Included paths: marketing-center
- Excluded paths: none
- Runtime or test status: Application code and tests were not executed during this audit.

Limitations and exclusions:
- No production service, provider, multi-user authorization or Command Center transport existed in this revision.
- Prior generated evidence snapshots and historical status documents are non-executable reference artifacts, excluded from vulnerability source coverage.
- Current dependency advisories are not rechecked by this offline source audit.
- Excluded marketing-center/evidence/\*\*: Historical logs and generated non-executable shadow output, not implementation source; current generator code audited.
- Excluded marketing-center/{MARKETING_STATUS.md,TRACKER.md,docs/EXECUTION-LEDGER.md}: Historical project status and execution ledger, no executable behavior. Other supporting architecture/runbook documentation inspected.

### Scan Summary

| Field | Value |
| --- | --- |
| Scan outcome | completed |
| Reportable findings | 0 |
| Severity mix | none |
| Confidence mix | none |
| Coverage | complete |
| Validation mode | static source review with independent baseline and architecture review |

Canonical artifacts: `scan-manifest.json`, `findings.json`, and `coverage.json`. This report is a deterministic projection of those files.

## Threat Model

Marketing Center is a single-user local Python shadow pipeline. CLI input JSON passes through credential-shape rejection, tenant/objective validation, a fixed trusted module catalog, research/strategy/content/review/measurement stages, then local evidence persistence. Its documented invocation is python -m mc --input fixtures/salem-shadow.json --output runs --at \<timestamp\>. No publishing API or remote Command Center transport exists in this pipeline; Command Center integration remains explicitly unverified. Sources: marketing-center/mc/__main__.py:8-20; marketing-center/mc/workflow.py:17-95; marketing-center/mc/catalog.py:28-50; marketing-center/docs/RUNBOOK.md:3-13,25-29; marketing-center/docs/LOCAL-RECOVERY.md:13.

### Assets

- Tenant/objective associations and marketing record provenance: scoped comparisons reject mixed identities; record IDs and run identities derive from canonical JSON SHA-256. Sources: marketing-center/mc/core.py:23-24,43-48,57-64; marketing-center/mc/workflow.py:21-35.
- Input snapshots, normalized records, results, rendered dashboard, optional handoff and Command Center status under resolve(output_root)/\<tenant_id\>/\<run_id\>. A sibling temporary directory is renamed into the final run directory; the manifest inventories and hashes generated files. Sources: marketing-center/mc/workflow.py:36-52,97-116.
- Recovery state under resolve(output_root)/\<tenant_id\>/.checkpoints/\<run_id\>, including writer.lock and step-\<SHA256\>.json. Checkpoints contain completed operation results, attempts and checksums. Sources: marketing-center/mc/workflow.py:53; marketing-center/mc/recovery.py:20-38,44-81.
- Module identity, source/configuration fingerprints and lifecycle state. These are provenance and accidental-isolation controls for trusted Python, not a hostile-plugin sandbox. Sources: marketing-center/mc/modules.py:1-4,65-71,128-142.
- No-secret/no-spend/no-publication guarantees for the authorized local qualification. Source-backed restrictions include empty connectors, paid_media_authorized=false, shadow-only execution, zero synthetic analytics spend and publication records with production_approved=false. Sources: marketing-center/schemas/tenant.schema.json:10-14; marketing-center/mc/workflow.py:18-29,57-58; marketing-center/mc/stages.py:142-150. User context also requires no irreversible actions and no duplicated Command Center infrastructure.

### Trust Boundaries

- Input-provider data enters the operator-invoked CLI/library. check_input recursively rejects named credential fields and HTTP(S) userinfo or credential-shaped query/fragment keys before snapshots or checkpoints. Tenant configuration and objective are supplied together by the caller; comparison is consistency enforcement, not authentication of a tenant principal. Sources: marketing-center/mc/__main__.py:10-16; marketing-center/mc/input_safety.py:1-24; marketing-center/mc/workflow.py:18-27.
- Structured evidence crosses into derived decisions. Research validates tenant labels, required fields, HTTPS reference syntax, provenance labels, timestamps and numeric confidence/relevance. References are parsed and stored, not fetched. Evidence truth and permission labels remain caller assertions. Sources: marketing-center/mc/intelligence.py:1-37,47-63.
- Customer module selection crosses into the fixed catalog. Only the documented intelligence shorthand or complete bundled module selection is accepted; bundled configuration schemas require empty objects. Actual install/replace APIs accept trusted inspectable Python function objects and confer operator-level execution, not tenant sandbox privileges. Sources: marketing-center/mc/catalog.py:28-50; marketing-center/mc/modules.py:29-71,109-137.
- Derived results cross into local filesystem evidence. Operator-selected output_root resolves before tenant/run path composition. Tenant naming is checked by both schema and Registry. Existing runs are read and inventory/content hashes checked; new runs are staged and renamed. Filesystem protection is the host/operator boundary, with no application-owned ACL or signature boundary established. Sources: marketing-center/mc/workflow.py:32-53,97-116; marketing-center/mc/modules.py:18-21; marketing-center/schemas/tenant.schema.json:7; marketing-center/docs/LOCAL-RECOVERY.md:5,13.
- Recovery operations cross a per-run writer coordination boundary. Windows uses msvcrt byte locking; other platforms use flock. Atomic checkpoint replacement, checksums, three attempts and before/after soft-deadline checks limit accidental corruption/concurrent reruns. They do not preempt Python execution or authenticate state against an already authorized filesystem writer. Sources: marketing-center/mc/recovery.py:14-76; marketing-center/docs/LOCAL-RECOVERY.md:5-9.
- Local review output crosses into human-readable artifacts. Dashboard fields are HTML escaped. The Markdown handoff contains supplied content and a shadow-only warning; no publication operation consumes it. Receipt parsing requires tenant/campaign/content identity equality and never promotes publication to VERIFIED. Sources: marketing-center/mc/workflow.py:105-109; marketing-center/mc/stages.py:22-38,142-150.
- Marketing status crosses only into a local JSON adapter file. Contract validation and evidence references exist; no external recipient authorization or transport is implemented. Sources: marketing-center/mc/workflow.py:86-94,101-104; marketing-center/contracts/command-center-interface.schema.json:5-19; marketing-center/docs/RUNBOOK.md:29.

### Attacker Capabilities

- A realistic input-source adversary may influence structured observations, strings, URLs or imported JSON presented to the operator. They do not thereby gain Python import selection, network access, publication authority or OS privileges; impact must be established through an actual input consumer. Sources: marketing-center/mc/catalog.py:28-50; marketing-center/mc/intelligence.py:5-37; marketing-center/mc/workflow.py:17-95.
- An ordinary library caller can invoke exported functions with caller-selected arguments, including tenant identities. No authenticated multi-user service or per-principal tenant authorization layer is present in the supported deployment. Treating such caller-selected identities as an authentication bypass would require a future broker that exposes the library to less-trusted principals. Sources: marketing-center/mc/workflow.py:17-26; marketing-center/mc/modules.py:18-21,128-134; marketing-center/docs/LOCAL-RECOVERY.md:13.
- An actor able to install arbitrary Python handlers or rewrite application/evidence files already possesses trusted local operator/filesystem authority. Checksum recomputation or malicious handlers are not new privilege gains within this model. Sources: marketing-center/mc/modules.py:1-4,59-74; marketing-center/docs/LOCAL-RECOVERY.md:5,13.
- Remote network attackers, hostile co-tenants with separate authenticated sessions, and provider credential theft require deployment surfaces not established by this local source. No such exposure is inferred.

### Security Objectives

- Reject mixed tenant/objective records through relevant stages and keep deterministic run/checkpoint/evidence namespaces tenant-specific. Sources: marketing-center/mc/core.py:43-48; marketing-center/mc/workflow.py:21-36,53; marketing-center/mc/stages.py:128-150.
- Reject supported credential shapes before persistence, sanitize operational error messages, and require synthetic non-secret operator inputs because credential rejection is explicitly not a general secret detector. Sources: marketing-center/mc/input_safety.py:1-24; marketing-center/mc/__main__.py:17-19; marketing-center/mc/modules.py:133-137; marketing-center/mc/recovery.py:74-76.
- Preserve existing evidence on mismatched inventory/content and recover pure operations without duplicate concurrent writers; respect retry budgets and disclose soft deadline limits. Sources: marketing-center/mc/workflow.py:37-53; marketing-center/mc/recovery.py:20-76.
- Permit only the fixed trusted bundled customer execution path; separate lifecycle/provenance checks from unsupported hostile-code isolation. Sources: marketing-center/mc/catalog.py:28-50; marketing-center/mc/modules.py:1-4,29-71.
- Keep all supported workflow results local, zero-cost and unapproved for production; never treat receipt assertions or a local VERIFIED status as live publication verification. Sources: marketing-center/mc/workflow.py:19-20,57-58,86-89; marketing-center/mc/stages.py:22-38,146-149.
- Preserve Command Center ownership of shared scheduling, retries, permissions and evidence services; local recovery/status adapters must remain temporary integration boundaries. Sources: marketing-center/README.md:15-18; marketing-center/mc/recovery.py:1-5; marketing-center/docs/RUNBOOK.md:29. This also reflects the supplied user scope.

### Assumptions

- Review is architecture mapping, not completed vulnerability coverage or runtime qualification. Only offline source was inspected; no code execution, external access, edits or tests were performed.
- Supported deployment is a single-user local checkout with trusted source, interpreter, imported dependencies, PATH-selected git executable and output filesystem. Multi-user ACLs, encryption at rest, RBAC and hostile plugins are explicitly unqualified. Sources: marketing-center/docs/LOCAL-RECOVERY.md:13; marketing-center/mc/core.py:13-21.
- CLI defaults output_root to cwd/runs; direct library callers supply output_root themselves. The application resolves this root but does not establish a separately enforced sandbox around an operator-selected output destination. Sources: marketing-center/mc/__main__.py:10-16; marketing-center/mc/workflow.py:36.
- Known credential-shape rejection does not guarantee that arbitrary free-text or unknown key names contain no secrets. Full input JSON is deliberately persisted; operators must supply non-secret data. Sources: marketing-center/mc/input_safety.py:1-3; marketing-center/mc/workflow.py:101-103; marketing-center/docs/LOCAL-RECOVERY.md:11.
- Checksums detect corruption, not adversarial rewriting by an actor with local write authority. The 60-second deadline is soft. Both limits are accurately disclosed by current recovery documentation. Sources: marketing-center/mc/recovery.py:54-76; marketing-center/docs/LOCAL-RECOVERY.md:5-9.
- Documentation evolution: docs/MODULES.md:11 and docs/V1-CORE-MODULE-DESIGN.md:6,12 describe the earlier intelligence-only/unfinished-recovery checkpoint. docs/MODULES.md:1 explicitly points to LOCAL-RECOVERY.md as superseding those limits; current code and LOCAL-RECOVERY.md:3-9 implement all six bundled modules and recovery. This is retained documentation history, not evidence that the current pipeline remains intelligence-only.
- Source provenance labels are not independently verified: research accepts synthetic, public_observation and authorized_client_data labels, whereas workflow analytics requires synthetic data. The runbook accurately says imported evidence is not independently browsed or verified. Sources: marketing-center/mc/intelligence.py:19-20; marketing-center/mc/workflow.py:28-29; marketing-center/docs/RUNBOOK.md:18.
- Future Command Center authentication, tenant authorization, exact-payload approval binding, provider cancellation, credentials and remote storage controls remain unresolved integration requirements; the current adapter cannot establish them. Sources: marketing-center/docs/RUNBOOK.md:25-29; marketing-center/docs/LOCAL-RECOVERY.md:9,13.

## Findings

### No findings

No reportable findings survived the canonical discovery, validation, and reportability gates.

## Reviewed Surfaces

| Surface | Risk Area | Outcome | Notes |
| --- | --- | --- | --- |
| Local input and tenant paths | not recorded | No issue found | mc/workflow.py:18-36, mc/modules.py:18-21: input credentials checked before persistence, validated tenant ID anchors paths; digests name runs. Local output_root is operator selected. No authenticated remote tenant boundary exists. |
| Module execution and lifecycle | not recorded | No issue found | mc/catalog.py:28-50, mc/modules.py:29-142, mc/recovery.py:78-81: fixed catalog, reference-free schemas, copied inputs, tenant injection, dependency/lifecycle checks including cache reuse. Trusted Python registry is explicitly not hostile-code isolation. |
| Source references and strategy | not recorded | No issue found | mc/intelligence.py:5-63: sources validated and URLs parsed without fetching. Confidence and provenance remain caller assertions, not external fact verification; decisions can HOLD. No network/SSRF sink. |
| Rendering and publishing boundary | not recorded | No issue found | mc/workflow.py:105-109; mc/stages.py:6-38,142-150: HTML escaped output, local Markdown handoff only; tenant/campaign/content receipt checks never verify real publication. No provider or payment sink. |
| Credential rejection and errors | not recorded | No issue found | mc/input_safety.py:1-24; mc/__main__.py:17-19; mc/modules.py:133-137; mc/recovery.py:74-76: normalized credential labels and parsed HTTP(S) credential URLs rejected, exception contents sanitized. Free text is not universally classified as secret-free. |
| Evidence persistence and recovery | not recorded | No issue found | mc/workflow.py:37-53,97-116; mc/recovery.py:20-81: fixed inventory, hashes, atomic staging/checkpoints, OS lock, bounded retry attempts. Trusted local filesystem assumed; checksums not malicious-writer authentication; deadline cooperative. |
| Process invocation and schema consumers | not recorded | No issue found | mc/core.py:13-41: constant git subprocess argument vector without shell, bundled local schemas. No caller-selected executable or remote schema reference; interpreter and PATH trusted. |
| Tests, fixtures, contracts and dependencies | not recorded | No issue found | All 10 mc files, all 10 tests, both schemas, status contract, Salem fixture, tenant example and requirements fully audited by independent baseline. Parent inspected critical consumers. Static source review only; existing 54-test/dependency logs are prior evidence, not tests executed during this scan. |
| Does customer JSON select executable imports or arbitrary modules? | not recorded | No issue found | No. It selects only fixed bundled configurations; all bundled config objects must be empty. Privileged Registry.install accepts trusted Python function objects separately. marketing-center/mc/catalog.py:28-50; marketing-center/mc/modules.py:59-74 |
| Is tenant identity bound to an authenticated principal? | not recorded | No issue found | No authentication boundary is implemented or claimed in this single-user local adapter. Tenant labels are caller-supplied and cross-record consistency is enforced. Future broker identity binding is unresolved. marketing-center/mc/workflow.py:21-27; marketing-center/mc/core.py:43-48; marketing-center/docs/LOCAL-RECOVERY.md:13 |
| Are output and recovery paths independently isolated resources? | not recorded | No issue found | They are separate child paths under the same operator-selected tenant output parent, with the same host authority. Checkpoint lock coordination is separate from filesystem authorization. marketing-center/mc/workflow.py:36,53; marketing-center/mc/recovery.py:20-36 |
| Do checksums and timeout provide adversarial tamper resistance and preemption? | not recorded | No issue found | No; current documentation explicitly limits checksums to corruption detection and calls the deadline soft. Code matches those limitations. marketing-center/mc/recovery.py:54-76; marketing-center/docs/LOCAL-RECOVERY.md:5-9 |
| Are references fetched or status/handoff files delivered remotely? | not recorded | No issue found | No remote consumer is implemented in the inspected pipeline. URLs are parsed/stored; status and handoff are local files. marketing-center/mc/intelligence.py:16-35; marketing-center/mc/workflow.py:101-109; marketing-center/docs/RUNBOOK.md:13,29 |
| Are earlier intelligence-only documents authoritative for current execution? | not recorded | No issue found | No. MODULES.md explicitly marks the earlier limits superseded. Current catalog and LOCAL-RECOVERY describe six bundled modules and durable local checkpoints. The older design remains historical documentation. marketing-center/docs/MODULES.md:1,11; marketing-center/docs/V1-CORE-MODULE-DESIGN.md:6,12; marketing-center/docs/LOCAL-RECOVERY.md:3-9; marketing-center/mc/catalog.py:33-49 |
| Does credential rejection guarantee no sensitive text is persisted? | not recorded | No issue found | No universal detector is claimed. Known field and URL credential shapes are rejected, while accepted full inputs are preserved; synthetic non-secret input remains an operator obligation. marketing-center/mc/input_safety.py:1-24; marketing-center/mc/workflow.py:101-103; marketing-center/docs/LOCAL-RECOVERY.md:11 |
| Independent baseline review | not recorded | No issue found | No additional canonical notes were recorded. |

## Open Questions And Follow Up

- Future Command Center integration requires separate authentication, tenant authorization, pause/recovery and exact-request-binding qualification; absent in this audited revision.
- Multi-user/service deployment, universal sensitive-text classification and malicious-local-writer protection are outside the current supported boundary.

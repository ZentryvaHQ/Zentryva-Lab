# V1 Core and module checkpoint design

Authority: MARKETING-LANE-DIRECTIVE.md and Richard's current execution request.
The existing R1 scope remains frozen. This checkpoint supplies missing P0 module infrastructure, not new marketing capabilities.

Core owns tenant validation, record contracts, orchestration, evidence persistence and module lifecycle. Research/competitor/strategy handlers are a bundled optional intelligence module. Existing marketing workflow is a legacy composition to extract further; it is not yet a fully modular commercial Core.

Use an explicit trusted local Python module catalog, not arbitrary import paths from customer input. Each tenant receives a fresh registry. Manifests declare exact version, Core API version, dependencies and configuration schema. Validate before activation. Disable/remove/replace must reject changes that would break enabled dependants. Calls require an enabled healthy module, inject the registry tenant, and sanitize module exception messages. Config is copied to prevent accidental cross-call mutation. File hashes, manifest and config participate in replay identity. This is isolation against accidental data mixing, not a sandbox for hostile Python plugins.

The shadow workflow uses the bundled module by default; explicit module selection is allowed, but omission/disablement of its required intelligence module fails before evidence creation. No dynamic package installation, external provider, credentials, spending or production adapter is added.

Acceptance: baseline regressions; incompatible API/dependency/config rejection; independent tenant configuration; disable/remove/replace effects; module crash sanitization; workflow integration; configuration/module-version replay separation; manifest provenance. Remaining extraction, durable step recovery, provider timeout/retry policy and full security audit stay open P0.

Execution: establish status and scope; write failing lifecycle/integration tests; implement registry and built-in adapter; run entire suite and dependency checks; preserve local commit, source/file hashes and logs; update authoritative tracker and ReleaseProof. No remote push or production release is required.

Current module/recovery behavior: see LOCAL-RECOVERY.md. This supersedes the original intelligence-only checkpoint limits below.

# Module operator notes — P0 local checkpoint

The default shadow CLI enables bundled `intelligence` version `1.0.0` automatically. To specify it explicitly, use top-level input `"modules": {"intelligence": {}}`. Empty, unknown, null and invalid configuration selections fail closed. No customer input selects Python packages or import paths.

Trusted module developers register a manifest and named functions through `Registry.install`. Manifest fields: module_id, exact version, core_api (1), dependencies (module IDs), config_schema (inline object JSON Schema, no references). Functions receive `(tenant_id, copied_configuration, ...operation_arguments)`. Use `enable`, `call`, `disable`, `replace`, `remove` and `snapshot`. Disable dependants before their dependencies; removal and replacement require disablement. Replacement is disabled until explicitly enabled. A failed operation marks module health FAILED; disable then enable is the explicit local reset. Dependencies must be healthy, including transitively. Configuration and operation arguments are copied per call.

Snapshot records manifest, handler source-file SHA-256, callable identity, enabled state, configuration hash and health. Enabled-module snapshots participate in run identity and manifest replay checks. No secret values belong in this shadow input: the existing evidence system preserves full inputs.

Trust and limits: local Python modules are trusted application code, not sandboxed plugins. No dynamic package installation, hostile-code isolation, provider health probes, dependency version ranges, resource teardown hooks, persistent registry or provider timeout/retry scheduler is claimed. Core runtime fingerprints cover the bundled top-level mc Python sources; external module transitive imports are not a qualified release path. Customer runtime currently supports only the bundled intelligence module. Other marketing stages still live in the legacy workflow composition and require extraction under ML-003. Durable restart/recovery and complete security qualification remain ML-004/005. A record named VERIFIED refers only to tested local scope.

Validation: `python -m unittest discover -s tests -v`; `python -m pip check`. Use the project's existing virtual environment. Logs and exact tested commit are in the checkpoint ReleaseProof. No dependencies were added.

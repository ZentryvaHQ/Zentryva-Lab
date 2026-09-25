# Local Command Center qualification

This document preserves the legacy one-shot protocol qualification. The newer
cooperative local beta is documented in LOCAL-BETA.md and pinned by
contracts/local-command-center.json. Its evidence is in evidence/supervised-beta.
The legacy reference below remains unchanged for regression testing.

This adapter implements the existing worker protocol against an isolated local
Command Center instance. It does not provide scheduling, a supervisor, a live
marketing publisher, or a new persistence service.

Reference repository: https://github.com/ZentryvaHQ/Zentryva-Command-Center-Core

Qualified reference: `worker/command-center-backend-adapter-20260921`, exact commit
`6c50292cf91fb4ea94f08e833e899d555290b714`. This is an unmerged development reference,
not a released or production-qualified Command Center. No changes are made there.

## Request and execution

An operator configures a local project/provider/worker in an isolated instance.
The owner/controller queues action `marketing.shadow.verify`, with `input` equal
to `mc.command_center.request_binding(data, now)`. This binds synthetic input,
tenant, clock and current Marketing Center source bytes. Worker and owner tokens
are separate, held in process memory/environment only. The adapter never uses
the owner token and cannot create or approve its own queued work.

`LocalCommandCenter(base_url, worker_id, token)` accepts only an explicit
`http://127.0.0.1:<port>` origin. The one-shot library entry point is:

```python
shadow_once(client=client, run_id=selected_run_id, project_id=project_id,
            provider_id=provider_id, tenant_id=tenant_id, data=data,
            output_root=output_root, now=now)
```

It selects exactly that pending run, rejects owner-gated jobs and all other
actions, checks bindings, stores receipt and checkpoint evidence, acknowledges,
checks the returned project desired state and assignment, runs the local shadow
pipeline, stores a result manifest summary, and completes the shared lifecycle.
A research/review/analytics hold becomes FAILED for this full-loop qualification,
never COMPLETE. Local failures publish a sanitized failure result. Real marketing
publication and spend remain false/zero throughout.

The operator entry point is `python -m mc.worker`. It requires `--url`,
`--worker-id`, `--run-id`, `--project-id`, `--provider-id`, `--tenant-id`,
`--input`, `--output`, and `--at`. Supply the already-provisioned worker token
through `MC_CC_WORKER_TOKEN` in the local process environment, never as a command
argument. Exit 0 means SHADOW_COMPLETE; exit 1 is an incomplete shadow result;
exit 2 means adapter failure and requires state reconciliation. This entry point
does not queue work or launch a background polling loop.

## Recovery boundary

The adapter never blindly retries HTTP mutations. A lost acknowledgement or
completion response can leave a remote run RUNNING or COMPLETE. Preserve local
evidence and reconcile through the shared control plane before another attempt.
The existing local operation journal still supports explicit deterministic replay.
This adapter does not automatically resume an acknowledged remote run.

The inspected server's worker pending endpoint exposes queued/approved runs only.
It has no worker-scoped running-run/status, cancellation or control-event read
interface. A project pause already present in the acknowledgement response blocks
local execution. A pause arriving during execution cannot be observed through
this protocol. Therefore continuous service use, shared-supervisor pause/restart,
and preemptive provider deadlines remain UNVERIFIED, a shared technical dependency,
not an owner-data request and not a reason to label local qualification production-ready.

## Repeat qualification

Use a clean reference checkout at the exact commit above and the dedicated
Marketing `.venv` with `marketing-center/requirements.txt` installed. Global
Python environments relying on per-user packages are not the qualification
runtime: fixture subprocesses intentionally do not inherit user-package paths.
From the Marketing repository root, set `MC_CC_SOURCE` to that checkout and run
`.venv/Scripts/python.exe -m unittest discover -s marketing-center/tests -v`.
Integration tests verify the reference HEAD and tracked-file cleanliness before loading its handler,
start a real HTTP listener on an ephemeral loopback port, generate disposable
test tokens, use temporary state/evidence, and shut it down afterwards.
Without `MC_CC_SOURCE`, these integration tests are explicitly skipped.

Set `MC_CC_EVIDENCE` to a new empty destination path when a durable success
roundtrip is needed. The test preserves generated synthetic state, events,
content-addressed shared evidence, local Marketing artifacts and revision proof.
Existing destinations are rejected. No test token is copied into evidence.

The scoped Codex Security report in `evidence/source-audit/report.md` covers the
pre-adapter commit `7d6c60bc245cd39f9c533bb5957b05e5675ba763`. The adapter is later
code, qualified separately by its tests and independent review; it is not silently
included in that sealed audit.

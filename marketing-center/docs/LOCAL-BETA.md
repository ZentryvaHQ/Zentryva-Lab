# Salem local beta

This beta completes the Salem synthetic loop through research, competitors,
strategy, campaign, reviewed copy, no-publish handoff, synthetic measurement,
attribution, learning and the next experiment. It exercises a real authenticated
local Command Center. It cannot publish, spend money or prove real Salem results.

## Run the beta

Use Python with requirements.txt installed (the existing repository .venv is the
qualified runtime). From marketing-center, run:

    python -m mc.beta --command-center PATH_TO_QUALIFIED_COMMAND_CENTER --output NEW_OUTPUT_DIRECTORY

The launcher validates the pinned shared source before loading it, creates a fresh
isolated state directory, binds an ephemeral 127.0.0.1 listener, uses disposable
in-memory owner/worker tokens, queues only the synthetic fixture, runs the worker,
and closes the listener. It prints the saved dashboard path. An existing output
directory is rejected rather than overwritten. Fixture dates remain their original
synthetic observation dates, not today's measured business performance.

Open dashboard.html in the resulting marketing/salem-botanicals/run-* directory.
handoff.md contains the generated copy and tracking URL, explicitly NOT APPROVED
FOR PUBLICATION. beta-summary.json records runtime and pinned shared source.

## Controlled worker operation

For a separately provisioned, isolated loopback instance, the existing worker
command supports `--supervised`. Queue protocol=cooperative-v1 and the exact
request_binding. Keep MC_CC_WORKER_TOKEN in the process environment. No owner token
is given to the worker. Exit codes: 0 complete, 1 content/evidence hold, 2 failure
requiring diagnosis/reconciliation, 3 suspended by shared control.

The worker executes continuously within that invocation until completion or a
control boundary. No service, scheduler, background watcher or production worker
is installed. Pause is observed before/after bundled stages and before completion;
it does not preempt a stage already in progress. A stage exceeding the 30-second
lease cannot commit remote completion; its pure local checkpoint may be reused.

After a pause, issue owner RESUME_REQUESTED and invoke the same worker request.
After a client crash or lost acquisition response, wait for the 30-second lease
to expire, then invoke the same request with the same input/output/source. After
a shared server restart, old session epochs are invalidated immediately. Terminal
success is reconciled by matching shared result hashes to local immutable files;
failed terminal runs require diagnosis and a new controller request.

## Qualified boundary

Single server process and trusted local modules only. Cross-worker status reads,
owner-control attempts, stale leases/generations, changed output, cross-tenant
bindings, secret-bearing input and live-mode requests are rejected by scoped tests.
Actual process death, response loss, control outage, pause/resume, clock rollback
and restart fencing are tested. This is not a full production security certification.

Remaining technical limits: no arbitrary provider cancellation, distributed
multi-process state store or crash-atomic state/event journal; no automatic service
installation. The shared legacy server.py executable binds all interfaces; use
the loopback beta launcher, not that executable, for this qualification.

MC-017 remains AWAITING RICHARD — LATER: approved real brand/product facts and
baseline, secure authorized accounts, explicit live launch approval. Local beta
qualification must not be described as commercial or live-publishing release.

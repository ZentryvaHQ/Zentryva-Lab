# Independent adapter review

Reviewer: review_unified_p0, 2026-09-23. Read-only review against real Command
Center reference 6c50292cf91fb4ea94f08e833e899d555290b714. All 9 focused tests ran
and passed. No critical or important defect found in the one-shot synthetic
loopback scope.

Minor evidence gap: the qualification checked reference HEAD but not tracked
working-tree changes or the actual imported module path. Fixed by rejecting
tracked modifications, verifying server.__file__, and recording reference Python
file SHA-256 values in the durable roundtrip proof.

Reviewed controls: exact request binding, worker authentication, allowlisted
shadow action, local execution rejection, failure reporting, shared evidence
references, and no repeated work after a lost completion reply.

Limits: no mid-operation pause, remote recovery, automatic HTTP retry, or
production supervision. Lost replies require shared-state reconciliation;
the final heartbeat can fail after the remote run already completed.

Follow-up reviewed mc/worker.py: no token argument/output, sanitized operational
errors, completion/incomplete/failure exit mapping checked. Reviewer found a
global-Python fixture portability issue: clearing APPDATA prevents discovery of
user-installed jsonschema. Resolution: qualification explicitly requires the
dedicated .venv with installed requirements; ambient per-user packages remain
excluded. Parent executed the subprocess roundtrip using that pinned environment.

The early `roundtrip` evidence has git_commit=null because the initial test
fixture cleared PATH. Its source digest and known checkpoint a12f18d are retained
as historical evidence. Windows socket initialization additionally required
SystemRoot. The final fixture preserves only OS runtime variables and disposable
test tokens. `final-roundtrip` supersedes the early run, includes exact Git
provenance, and asserts that provenance against the current checkout.

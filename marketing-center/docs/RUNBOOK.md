# Run the Salem shadow loop

Requires Python 3.11+ and the free JSON Schema package. From `marketing-center`:

```powershell
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python -m mc --input fixtures/salem-shadow.json --output runs --at 2026-09-22T12:00:00Z
```

Open `dashboard.html` inside the output directory printed by the command. The same directory contains the review copy, handoff, normalized records, input snapshot, Command Center status and integrity manifest. A repeated identical input/time returns the preserved result after checking integrity. Change the input to create a new run; never edit an existing evidence directory.

All sample research, competitors, brand wording and analytics are **synthetic**, not verified Salem facts. The reserved example.org URL deliberately prevents confusing the handoff with a real campaign. This is an executable internal shadow milestone, not a completed production pilot. There are no network clients, credentials, paid provider calls, schedulers, background jobs or public posting paths.

## Inputs and limits

- `tenant`: validated safety configuration, objectives and identity. Production configuration is intentionally unavailable in this runner.
- `sources`: structured observations including source URI, observation date, applicability, relevance and confidence. The engine imports evidence; it does not claim to have browsed or independently verified it. Freshness cutoff: 30 days; relevance/confidence floor: 0.5; configurable policy is deferred.
- `brand`: explicitly synthetic shadow profile and allowlisted copy. The initial content adapter assembles the approved text, CTA, creative brief and tracking link; it is not an LLM provider. Its mechanical phrase checks are not legal/compliance approval.
- `analytics`: synthetic funnel snapshot with provenance. Missing analytics yields `WAITING_ANALYTICS`; supply the data in a new run to recover. Counts represent unique visits/leads in one window, not cumulative provider counters.
- `baseline`: comparable synthetic window. Under 30 visits or unmatched windows produces HOLD. This floor is not a statistical significance threshold.

Attribution keeps direct, influenced, correlated and unknown separate. A matching campaign key and explicit conversion references are required for directly attributed revenue; zero spend leaves ROAS undefined. Synthetic results never establish actual Salem ROI. Learning proposes experiments or reductions, not paid scaling.

## MC-017 — AWAITING RICHARD (later)

Production remains gated on the approved Salem business/product/brand facts, baseline/client data, chosen campaign, publishing access and explicit production approval. Do not put credentials in these input files. Without this gate, the system can continue shadow runs and tests but cannot publish or claim measured business uplift.

Command Center owns scheduling, retries, health and evidence services. `command-center-status.json` is a temporary development adapter; no live delivery to Command Center has been verified. Receipt parsing can detect acceptance, expired auth, retry requirements and tracking failures; it deliberately cannot certify real-world rendering.

# Independent review and resolution

Reviewed bc9ec7b7cf36d4400a376be0f0345fb8e4dc0252..ac03f95fd44bbf42fbc47edd3c5566a50a077195 with a read-only reviewer. Initial 21 tests passed; review found five important issues. All were reproduced and fixed:

1. Claim checks skipped CTA: now scan emitted copy, CTA, creative brief, audience and tracking text.
2. Metric/baseline identities were rebound: declared identities must match; non-synthetic metrics require explicit campaign binding; metric references the campaign. Synthetic fixtures may bind to the generated campaign.
3. Impossible conversions could support attributed revenue: reject conversions above unique visits and reference counts above conversions. References are imported assertions, not independent payment verification.
4. Replay omitted implementation identity: source/schema fingerprint and runtime versions now participate in run identity; manifest preserves git commit and source fingerprint.
5. Manifest could omit altered handoff: require expected file set and run identity. Hashes detect corruption, not an attacker rewriting the entire bundle.

Portability fix: copied evidence returns the current output path without rewriting preserved files.

Minor deferred: receipt importer can assign failure/retry without full campaign/content identity validation. Runner supplies no receipts and no receipt can become verified publication; tighten before connecting a live adapter.

Scope rulings: real research, legal approval, live publishing/rendering, actual ROI and live Command Center integration remain unverified. The reviewer did not judge those external integrations. Intentional shadow scope; production R1 cannot be declared complete.

Regression evidence: logs 09, 10, 12 (red) -> 13-review-fixes-green.log: 29 tests passing.

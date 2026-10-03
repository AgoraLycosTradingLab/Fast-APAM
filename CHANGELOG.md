# Changes

## Unreleased — customer setup preparation

- Added offline `check-setup` for a ticker CSV and explicit model date.
- Added a Windows VS Code quick-start, example request list and staged customer-release brief.
- Kept setup validity separate from issuer eligibility, peer coverage and score readiness.
- Customer ticker-to-results automation remains under development.

## Unreleased — private SEC identification

- Prompt with hidden entry only when an uncached SEC download requires identification.
- Keep entered identification in memory for the command; no credential file is created.
- Support environment configuration for automation and refuse visible-input fallbacks.
- Existing local scoring needs no API keys; calculation methodology is unchanged.

## 0.2.0 — software consolidation

- Consolidated the dated research engine behind an explicit model-date configuration.
- Replaced loose permanent intermediate outputs with a compressed SQLite artifact store and optional audit ZIP.
- Added immutable imports, source/code fingerprints, deterministic run reuse and protected output publication.
- Added incremental immutable SEC-document retrieval with resumable failures.
- Preserved scoring weights, fallback treatment, availability rules, source lineage and provisional policy.
- Kept original July/September archives unchanged; no production approval or GitHub publication.

# Calculation dependencies

The calculation model is unchanged. The refactor changes orchestration, storage and reporting only.

1. **Prepared snapshot import:** roster, filing index, canonical selected facts, standalone quarters, TTM/YoY observations and controls, Wave1 compatibility outputs, specifications, research policy, and recorded input exceptions. Imports verify dates, membership, source checksums where supplied, and eligibility cutoffs. Configuration counts come from the imported roster and wave controls.
2. **Factor inputs:** reads observations and control audits; reconstructs source references and factor floors.
3. **Normalization:** reads factor inputs, required coverage tables, and lineage. Standard peer coverage must pass before percentile calculation. Absolute changes are not mixed with rates.
4. **Factor aggregation:** consumes eligible metric scores and company gates. July's fixed eligible-company count is not a rule.
5. **Persistence and arithmetic review:** consumes factor scores, diagnostics, and source manifests. The existing research conventions and reviewed FCF-margin correction remain unchanged.
6. **Research results:** checks source-parent evidence, applies the recorded provisional confidence/status policy, and preserves company holds and sector exclusions.

Some files called audits are essential control tables. They are never skipped. Their existence in temporary processing does not require users to manage loose CSVs.

## Storage boundary

SQLite holds content-addressed, compressed artifacts and immutable snapshot/run metadata. This first refactor deliberately preserves the tested CSV interchange schemas inside the engine. It is not yet a typed financial-observation warehouse, and it does not claim a faster first calculation without benchmark evidence. Avoid a simultaneous rewrite of storage semantics and financial methodology.

Identical snapshots share identical blob content. Runs are keyed by input and code fingerprints. Unchanged runs can reuse checksum-verified outputs; changed code recalculates. Publication is staged and promoted only after calculation and requested reference validation pass. Raw SEC files remain separately retained in the source archive or document cache.

## Historical compatibility

Two existing snapshot dates are reference fixtures, not hard-coded supported dates. Six tables per date cover final results, factor scores, primary input decisions, status decisions, parent evidence and observation lineage. The 22 earlier integration tests tied to local fixture folders are replaced by these actual two-date regression comparisons; 107 portable calculation tests remain. New orchestration tests cover immutability, checksum failures, date isolation, output preservation and incremental retrieval.

The current importer requires the governed two-wave prepared schema. Importing another sector or radically different data schema requires an explicit adapter and methodology review. Original specifications may retain their dated research status; cleanup does not change approval status.

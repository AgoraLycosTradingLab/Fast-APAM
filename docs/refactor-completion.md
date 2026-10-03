# Fast APAM software cleanup — completed

The refactor preserves the existing July 31 and September 25 research results. It does not redesign approved financial calculations or change production approval status.

## Delivered

- One installable Python package and one date-driven CLI.
- Immutable prepared snapshots in a compressed, content-addressed SQLite store.
- Exactly three routine files per run: results, exceptions, and run metadata.
- Optional detailed audit ZIP, including evidence bytes named by stage checksum manifests.
- Incremental SEC-document retrieval with cached content validation and resumable failures.
- Date/cohort configuration derived from imported snapshots instead of copied dated code.
- Repository documentation, dependency map, synthetic tests, Git ignores, and a Windows/Linux CI workflow.

## Verification

125 portable unit tests pass. The former 22 local-fixture integration tests have been replaced for this migration by exact comparisons of six substantial tables for each of the two archived dates. All 12 table comparisons pass with no differences. They include final results, factor scores, status audits, detailed factor inputs, parent evidence and observation lineage.

The installable wheel's CLI was exercised on both dates. Optional audit exports were checked against their dependency checksum manifests. Detailed machine-readable results are in `refactor-validation.json`.

## Efficiency

See `benchmark.json` for measured timing and storage, including the old six-stage pipeline. Initial calculation remains in the same general range; the major speed benefit is reusing an identical input/code snapshot. The compressed store saves disk space and removes the need to manage intermediate CSVs manually.

The raw historical SEC documents, earlier revisions, and original project folders remain unchanged. The local scoring database is not a replacement for that full source archive.

## Operating boundary

This release runs prepared, validated snapshots. Its incremental downloader does not automatically approve new accounting contexts, restatements, fiscal calendars, or peer classifications. Those decisions still follow the existing data-construction process before import. The engine retains its tested CSV interchange schemas internally; database storage does not yet provide a normalized, queryable financial-observation warehouse.

The original two-wave IT pilot remains the supported schema. Other sectors need their own governed adapters and validation. Model weights, fallback treatment, filing buffers and provisional scoring/status conventions are unchanged.

The consolidated source is published at https://github.com/AgoraLycosTradingLab/Fast-APAM. No packaged release is established by the original refactor. The software subsequently adopted the MIT License; third-party data rights remain separate. Local databases, raw data, caches, results, archives and credentials are excluded from normal Git history.

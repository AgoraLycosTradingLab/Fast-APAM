# Customer preparation milestone

Implemented October 3, 2026. This is the first financial-data acquisition stage for a fresh source checkout, not a finished customer scoring release.

On Windows, open `Fast APAM.cmd`, select option 2, and supply the model date, ticker CSV path, and a new preparation folder. Your CSV needs one column named `ticker`. If your file is under `examples`, enter `examples/universe.csv`. The SEC identification prompt is hidden and does not save the entered organization/contact identifier. Paid-provider keys are not used.

After package installation, the equivalent command is:

```text
python -m fast_apam prepare-data --date 2026-09-25 --universe universe.csv --output data/preparation-2026-09-25
```

The date is a historical example. Future model dates are rejected. The default filing history begins January 1 three years before the model year. `--history-start YYYY-MM-DD` overrides this; dates before 2023 are outside the existing pilot calendar support. A shorter range does not waive financial-history requirements. Review extraordinary exchange closures before extending historical calendar coverage.

| File | Meaning |
|---|---|
| `issuer_candidates.csv` | Exact current SEC symbol-to-CIK matches; not dated identity approval |
| `filing_index.csv` | US periodic filing metadata, derived availability dates, amendments and cutoff exclusions |
| `candidate_facts.csv` | Standard-tag candidates with accession, unit, period and source lineage; contexts remain unverified |
| `preparation_exceptions.csv` | Unresolved symbols, invalid metadata, retrieval problems and remaining review requirements |
| `preparation.json` | Counts, status, source manifest, input checksum and remaining gates |
| `raw/` | Original SEC JSON responses addressed by SHA-256 |

The source manifest records each URL, hash and retrieval timestamp. Current ticker matches are discovery hints even when the requested date is historical; the command never promotes them to point-in-time universe evidence. Different share-class spellings are not guessed. Nonpositive financial values remain unchanged for later governed fallback handling. Acceleration and scores are not calculated here.

Requests are sequential and throttled. Acquired evidence is preserved if one issuer fails. `INCOMPLETE` returns exit code 1. `CANDIDATES_ACQUIRED_NOT_SCORE_READY` returns 0 for acquisition only; both statuses have `ready_to_score: false`. Nonempty output folders are rejected. Retry into a new folder; automatic retry/resume remains future work. Invalid or future fact periods and unresolved symbols remain explicit exceptions even when transport succeeds.

No original development data, local snapshot or scoring configuration is needed. Tests use synthetic SEC responses for older filing pages, cutoff protection, lineage, nonpositive values, malformed metadata, unresolved symbols, source restrictions and redacted failures. Live acquisition still needs internet and the customer's SEC contact identifier; offline tests do not establish live provider availability.

Remaining work before customer scoring:

1. Verify dated issuer identities, eligibility and sector/peer evidence. FAPAM-004 permits a personal input file operationally but retains point-in-time S&P 500 eligibility for v1 and dated membership for historical tests.
2. Automate inline-context verification and approved special-issuer mappings.
3. Connect standalone-quarter, FCF and TTM/YoY construction to the snapshot input contract.
4. Validate peer coverage, then connect normalization, scoring and result export.

The preserved scoring engine still runs validated prepared snapshots. Do not pass this preparation folder to `run --source`: it does not yet meet that contract.

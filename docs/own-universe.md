# Use your own stock list

Create a UTF-8 CSV named `universe.csv` with one column:

```csv
ticker
MSFT
AAPL
NVDA
```

Save it at the repository root, where this filename is ignored by Git, or outside the repository. Do not put credentials in the file. Use one symbol per row; surrounding spaces and lowercase letters are normalized. Duplicate symbols, extra columns, invalid symbols and empty lists are rejected with a row-specific error where applicable. Share-class spellings are not guessed or silently merged.

## Windows menu

Open `Fast APAM.cmd`. Choose:

1. **Check my ticker file** to validate the list without downloading anything.
2. **Download SEC financial candidates** to acquire evidence for the requested stocks. This still does not produce scores.
3. **Run my stock list against a prepared scoring snapshot** to export scores and exceptions for your list from an existing validated snapshot.

Enter a date or leave the date blank for `latest`. At the CSV prompt, press Enter to browse for your file, or paste its path. If Python's file-dialog component is unavailable, the launcher accepts a typed path. Cancelling file selection cancels the operation; it never substitutes the example list.

For option 3, leave the snapshot-folder prompt blank to use an already imported snapshot in this copy's local database. A fresh GitHub download does not include that database. To import a validated snapshot, provide its prepared-input folder. Supply a new output folder in either case.

## Command-line equivalent

```text
python -m fast_apam run --date 2026-09-25 --universe universe.csv --output outputs/my-stocks-september
```

The example requires the September 25 snapshot. Use `--date latest` only when inputs for the effective latest session have been prepared and imported. The model never relabels an older snapshot to satisfy a missing date. `--source PATH` can import validated inputs matching the effective date.

## Results and comparison peers

`results.csv` contains one row for each requested stock, in your file's order. Covered stocks retain their original scores, status, dates, source lineage and hold reasons. A stock absent from the prepared cohort gets an unscored row with `NOT_IN_PREPARED_COHORT`, blank score and source fields, and an explicit missing-input reason. It is also included in `exceptions.csv`. This is a data-coverage outcome, not a finding that the stock is ineligible or a poor investment.

The model calculates and validates the entire prepared comparison cohort before selecting your rows. Adding or removing stocks from your request therefore does not change a covered stock's score or waive peer-coverage requirements. No requested ticker is silently dropped. A request containing only unavailable stocks still produces an exception report with zero scores, not fabricated results.

`run.json` records the normalized request, exact input-file SHA-256, requested/matched/scored/unscored counts and normalization-cohort size under `universe_selection`. The unchanged full-cohort calculation statistics are retained under `cohort_summary`. The top-level score count describes the customer's output. The calculation `run_id` identifies the full-cohort run and can be shared by multiple stock-list exports; output hashes and the input-list checksum identify the particular export. `export-audit` continues to export full-cohort evidence, so retain the customer output folder alongside it.

Running without `--universe` retains the existing full-cohort export. Prepared-snapshot verification still compares the entire cohort against frozen references before selecting customer results.

## Current scope

This adds stock-list selection to actual prepared-snapshot scoring, beyond the existing acquisition-only support. It does not yet construct validated scoring inputs automatically for arbitrary new stocks or sectors. The validated pipeline remains the IT operating-company research pilot. The remaining acquisition-to-scoring work includes dated identity and peer evidence, inline context verification, approved issuer mappings, financial-period construction and cohort coverage validation.

# Reading results

Each successful published run writes `results.csv`, `exceptions.csv`, and `run.json`. The calculation always performs required controls; optional audit export changes the packaging, not whether checks run.

## Company results

| Field | Meaning |
|---|---|
| `ticker`, `company_name`, `cik` | Recorded security and issuer identity |
| `model_date` | Information cutoff used by the snapshot |
| `as_of_period_end`, `fiscal_quarter` | Financial period being evaluated |
| `signal_model_available_date`, `data_age_days` | Signal availability and age |
| `PROVISIONAL_FAST_SCORE` | Relative research score on a 0–100 scale, or blank |
| `PROVISIONAL_FAST_STATUS` | Business-trend interpretation |
| `PROVISIONAL_DATA_CONFIDENCE` | Separate research measure of input reliability/completeness |
| `PROVISIONAL_DATA_STATUS` | Partial, held, excluded, or other recorded data condition |
| `score_published` | Whether a score was actually released |
| `gate_reason`, `underlying_candidate_hold_reason` | Reasons for holds or partial coverage |
| `history_view`, `filing_vintage_status` | Restatement/availability treatment |
| `production_approved`, `historical_as_filed_backtest_verified`, `investability_status_calculated` | Explicit limits on what the run establishes |

Use the published score field. `reviewed_candidate_score_reference` is an audit reference and must not be promoted to a published score when `score_published` is NO.

## Trends

- **ACCELERATING:** research rules identify strengthening performance.
- **IMPROVING:** research rules identify improvement.
- **STABLE:** the recorded policy's stability rule is satisfied.
- **DECELERATING:** performance is slowing under the trend rules.
- **DETERIORATING:** the policy identifies weakening operating direction.
- **MIXED:** conflicting evidence or no more specific directional rule matches.
- **UNSCORED:** the run did not release a score.

These are summaries, not replacements for the exact recorded thresholds and status reasons. High relative scores can coexist with deceleration. Confidence is not a stock-return forecast, and missing scores are not zero. Partial data status can occur on a scored company because optional inputs are unavailable.

## Exceptions and run details

`exceptions.csv` includes each unpublished company with its recorded reasons. It is not a list of investment rejections. Incomplete history, peer classification and unresolved source conflicts can all prevent publication.

`run.json` identifies inputs/code, run completion, cohort/coverage information and any requested reference comparisons. A COMPLETE run can contain unscored companies. It does not grant production approval.

For full evidence, obtain `run_id` from `run.json` and run:

```text
python -m fast_apam export-audit --run-id RUN_ID --output archives/run-audit.zip
```

The archive includes prepared inputs, intermediate calculations and source/code evidence. Review its contents before sharing; local audit exports are not part of the public source distribution.

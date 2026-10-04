# Requested date and effective model date

Customer commands `run`, `prepare-data`, and `check-setup` accept either `YYYY-MM-DD` or `latest`. The Windows launcher defaults to `latest` when the date prompt is left blank.

The effective model date is the most recent completed NYSE cash-equity session on or before the requested day. Weekends and full-day exchange holidays roll backward. A request for today before the scheduled close also rolls backward. Early closing sessions count as completed at 1 p.m. Eastern; regular sessions at 4 p.m. Eastern. The application uses `America/New_York`, including daylight saving time, independently of the computer's local timezone. Explicit future dates are rejected.

For example, `2026-09-27` (Sunday) resolves to `2026-09-25`. The observed Independence Day holiday and its weekend, July 3–5, 2026, resolve to July 2.

Preview the date without a database, credentials or downloads:

```text
python -m fast_apam resolve-date --date latest
python -m fast_apam resolve-date --date 2026-09-27
```

Use the same option for preparation or a prepared scoring run:

```text
python -m fast_apam prepare-data --date latest --universe universe.csv --output data/new-preparation
python -m fast_apam run --date 2026-09-27 --output outputs/september-weekend
```

The second example requires an already imported September 25 snapshot. Date fallback does not search for older available snapshots: if the effective day's snapshot is missing, the command fails rather than relabeling stale data. `--source` must contain validated inputs for the effective date. Date handling does not complete the unfinished automatic ticker-to-score workflow.

`date_resolution` records the original request, effective date, skipped days and reasons, close timestamp, resolution timestamp and calendar version. It appears in setup JSON, `preparation.json`, and exported `run.json`. Preparation rows use the effective date. It is output metadata rather than a change to the immutable financial snapshot or cached calculation; identical effective-date inputs retain identical financial results. Low-level `import-snapshot`, `verify`, and `fetch-new-filings` retain their exact dated-evidence contracts and do not rewrite dates.

## Calendar maintenance

The bundled resolver supports 2023–2028. It reuses the existing regular-holiday rules, adds known special closure January 9, 2025, and records scheduled early closes explicitly. It rejects dates outside its supported range, including a fallback that would cross the lower boundary. The calendar is offline and does not discover newly announced emergency closures or intraday interruptions. Maintainers must update and test it when the exchange changes its schedule. This resolver does not alter the preserved financial engine's filing-availability calendar or processing buffer.

Sources checked October 4, 2026:

- [NYSE holidays and trading hours, 2026–2028](https://www.nyse.com/trade/hours-calendars)
- [NYSE announced calendar, 2025–2027](https://ir.theice.com/press/news-details/2024/NYSE-Group-Announces-2025-2026-and-2027-Holiday-and-Early-Closings-Calendar/default.aspx)
- [NYSE 2023 calendar](https://www.nyse.com/publicdocs/ICE_NYSE_2023_Yearly_Trading_Calendar.pdf)
- [NYSE 2024 calendar](https://www.nyse.com/publicdocs/ICE_NYSE_2024_Yearly_Trading_Calendar.pdf)
- [NYSE special closure for January 9, 2025](https://ir.theice.com/press/news-details/2024/The-New-York-Stock-Exchange-Will-Close-Markets-on-January-9-to-Honor-the-Passing-of-Former-President-Jimmy-Carter-on-National-Day-of-Mourning/default.aspx)

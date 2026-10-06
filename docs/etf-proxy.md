# Dated ETF holdings proxy

The GitHub edition can use public iShares Core S&P 500 ETF (IVV) holdings as a practical membership and sector **proxy**. The [official iShares fund page](https://www.ishares.com/us/products/239726/ISHARES-CORE-SP-500-ETF) provides the [holdings CSV](https://www.ishares.com/us/products/239726/ishares-core-s-p-500-etf/latest-holdings.csv). Holdings are not the official S&P 500 constituent record; sponsor sector labels are not licensed historical GICS classifications. The original model's reviewed cohort and scoring method are unchanged. This proxy supplies candidates for the portable acquisition pipeline, not automatic score approval.

Choose option 5 in `Fast APAM.cmd`, or run:

```powershell
python -m fast_apam resolve-cohort --date latest --universe examples/universe.csv --output data/etf-proxy-latest
```

The stock list remains a one-column CSV named `ticker`. It selects requested stocks for audit, while all unambiguous equity holdings form the peer-candidate cohort. The command writes `etf_proxy_cohort.csv`, `etf_proxy_audit.csv`, and `etf_proxy_manifest.json` in a new or empty output folder. The manifest records the effective model date, ETF holdings as-of date, age, original file path, SHA-256, sector counts, and requested-stock coverage. The downloaded source is retained under ignored `data/etf-holdings/`; it is not committed to GitHub.

For a historical date, pass a dated source you obtained from the sponsor, or use a previously archived local download:

```powershell
python -m fast_apam resolve-cohort --date 2026-09-17 --universe examples/universe.csv --holdings-file path/to/dated-IVV.csv --output data/etf-proxy-2026-09-17
```

The parser requires the IVV fund name, a single `Fund Holdings as of` date and a recognizable holdings table. An as-of date after the effective market date is rejected to prevent look-ahead. A file older than 14 calendar days is rejected; this includes the original September 17 holdings file when used for September 25 (eight days old). For a historical request, the program selects the newest matching local archive dated on or before the model date; it does not relabel the current sponsor file as historical evidence. Unknown sectors, non-equity rows, malformed symbols and duplicate ticker symbols remain in the audit and are excluded from the peer candidates. Different share-class ticker spellings are not guessed. A ticker absent from the dated proxy is audited and does not become an eligible peer merely because the user requested it.

The output has `ready_to_score: false`. SEC issuer identity, sector-specific factor mappings, comparable financial history, special-issuer treatment, normalization coverage, and the approved scoring gates still need review. The portable pipeline currently has validated scoring only for prepared Information Technology pilot snapshots. No ETF-proxy command calculates scores, ranks, or investability statuses.

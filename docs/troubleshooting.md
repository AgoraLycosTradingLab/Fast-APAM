# Troubleshooting

| Problem | Check or action |
|---|---|
| `py` is not found | Locate/install Python 3.11+, reopen the terminal, or use `python -m venv .venv` if that is your installed command |
| `No module named fast_apam` | Install from the folder containing `pyproject.toml`; use the same virtual environment for installation and execution |
| PowerShell blocks environment activation | Activation is unnecessary; use `.\.venv\Scripts\python.exe` directly |
| Setup says `ready_to_score: false` | Expected: the setup command validates ticker-file format only |
| Ticker CSV rejected | Keep exactly one `ticker` column, remove duplicates and extra columns, and fix the indicated row |
| Snapshot not found | Source downloads exclude the local database; import validated prepared inputs first |
| Required prepared input missing | Consult the input contract; a ticker list or raw filing directory is not a prepared snapshot |
| Date mismatch or look-ahead error | Correct the actual dated inputs/availability; do not bypass checks or relabel old data |
| Snapshot cannot be overwritten | The import is immutable; preserve it and investigate differing inputs rather than replacing evidence |
| No frozen references for `--verify` | Use the matching validated reference set, or omit reference verification for a genuinely new validated snapshot |
| Output folder already contains files | Choose a new or empty folder; existing results are preserved |
| Hidden SEC entry unavailable | Run in an interactive terminal or supply `APAM_SEC_USER_AGENT` through the process environment |
| SEC retrieval incomplete | Inspect failure counts, network access and SEC access guidance; rerun to retrieve missing documents using the cache |
| A company is unscored | Read `exceptions.csv` and detailed audits; do not substitute zero or a withheld candidate score |

The current downloader does not automatically retry with backoff within a command. Customer ticker-to-results preparation is still under development.

For ordinary bug reports, provide the command name, Python/OS versions, error text and a minimal synthetic reproducer. Remove contact identifiers, credentials, customer data and local personal paths. See [SECURITY.md](../SECURITY.md) for vulnerability reporting.

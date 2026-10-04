# Configuration and commands

Use your virtual environment's Python for every command. `python -m fast_apam` and the installed `fast-apam` command expose the same interface. The model date is explicit, never silently inferred from the computer clock.

## Ticker input

`check-setup --date YYYY-MM-DD --universe PATH` accepts UTF-8 CSV with exactly one column named `ticker`. The example is [examples/universe.csv](../examples/universe.csv). Symbols are trimmed and uppercased; duplicates are rejected. Letters, digits, dots and hyphens are accepted up to 15 characters under the command's syntax rules. Different share-class spellings are not automatically combined.

This validates format only. It makes no network calls, creates no database and requests no credentials. It does not approve membership, resolve issuer identity, or pass the list to scoring.

## Prepared snapshot inputs

The current importer uses the preserved two-wave IT pilot schema. [snapshots.py](../src/fast_apam/snapshots.py) defines the exact filenames and validation. A source directory needs:

- The dated extraction roster and reviewed SEC filing index.
- Wave1 and Wave2 TTM/YoY observations, control audits, canonical selected facts and standalone quarters.
- Wave1 compatibility factor-input and coverage outputs.
- The eight governing documents and the dated research policy JSON.
- Recorded input exceptions and cohort review/evidence where applicable.
- Frozen reference tables when reference verification is requested.

This is a prepared-data contract, not a folder of arbitrary downloaded filings. The importer preserves the existing historical governance path where newer review files are absent; it does not fabricate approval of new universes. Source observations and availability must match the model date.

## Storage and execution

The default store is `data/fast_apam.sqlite`, relative to the working directory. To select a different store, put `--store PATH` **before** the subcommand. Snapshots are immutable: changed inputs cannot silently overwrite an imported date.

| Command | Purpose |
|---|---|
| `check-setup --date D --universe FILE` | Offline input syntax validation |
| `prepare-data --date D --universe FILE --output DIR [--history-start D]` | Acquire SEC candidates; never publish scores |
| `import-snapshot --date D --source DIR` | Import prepared inputs without publishing results |
| `run --date D --output DIR [--source DIR] [--verify] [--force]` | Calculate or reuse and publish three files |
| `verify --date D` | Compare calculated tables against imported references |
| `list` | Show imported dates and fingerprints |
| `fetch-new-filings --date D --index FILE` | Cache missing eligible documents from a reviewed index |
| `export-audit --run-id ID --output FILE.zip` | Export detailed evidence for a successful run |

Replace D, FILE, DIR and ID with actual values. `--verify` needs frozen reference outputs. `--force` recalculates even when cached and checks determinism for the same input/code combination. Output directories must be new or empty. Audit ZIPs cannot overwrite an existing file.

## Credentials

Only implemented SEC downloads need `APAM_SEC_USER_AGENT`, an organization/contact identifier rather than a paid API key. Interactive entry is hidden, command-scoped, and not saved by the application. Unattended jobs must supply it through their environment. The application does not load `.env` automatically.

No customer JSON configuration file, vendor-key argument, automatic “today” run, or ticker-to-scoring command has been implemented. See [data sources](data-sources.md).

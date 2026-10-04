# Try Fast APAM in VS Code on Windows

This source distribution needs Python 3.11 or newer. The Microsoft Python extension in VS Code is optional for running terminal commands. It does not require an installer or administrator access. Git is optional when downloading a ZIP.

## Windows launcher

Double-click `Fast APAM.cmd` in the repository. It uses its own directory, creates or reuses `.venv`, and installs the package if needed. Select option 1 to check your ticker file, option 2 to acquire SEC candidates, or option 3 to score an already prepared snapshot. Supply an explicit date. If your CSV is under `examples`, enter `examples/universe.csv` at the prompt.

Option 2 produces audited candidate data, not scores. See [the preparation guide](customer-preparation.md) for remaining work. To repair installation, run `& '.\Fast APAM.cmd' --setup` from PowerShell.

## Open and install

Open the extracted project folder with File > Open Folder. Select the folder containing `pyproject.toml`, `README.md`, and `src`. Open Terminal > New Terminal and use PowerShell.

Run each command from that folder:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

These commands install dependencies into a project-specific environment. Activation and changes to PowerShell execution policy are unnecessary. If `py` is unavailable but Python 3.11+ is installed as `python`, use `python -m venv .venv` for the first command.

In VS Code, use Python: Select Interpreter and select `.venv\Scripts\python.exe`. Keep using the explicit commands above if automatic interpreter discovery does not find it.

## Check your ticker file

Copy `examples/universe.csv` to `universe.csv` at the project root. Replace the example tickers with the companies you want to research. Keep the single `ticker` column. The root `universe.csv` is ignored by Git so a personal list is not included in a normal publication.

```powershell
.\.venv\Scripts\python.exe -m fast_apam check-setup --date 2026-09-25 --universe universe.csv
```

Use your intended model date explicitly. The date above is the historical validation example, not today's date.

Expected output includes `setup_status: INPUT_FORMAT_VALID` and the number of tickers. `ready_to_score: false` is intentional: this command checks file format only. It does not verify ticker identities, sector membership, financial data, or peer coverage. It makes no network requests, asks for no credentials, and creates no database. Different share-class spellings are not automatically combined; the future issuer resolver must check them.

The three example tickers demonstrate the input format. They do not constitute a valid normalization cohort. The customer ticker list will select requested companies, while a separately validated dated peer cohort supplies normalization observations.

## Run an existing validated snapshot

If this particular copy already contains an imported September snapshot in its local database, rerun it into a new output folder:

```powershell
.\.venv\Scripts\python.exe -m fast_apam run --date 2026-09-25 --output outputs/my-september-test --verify
```

Choose a new or empty output folder each time. The command uses the imported snapshot, not `universe.csv`.

Someone downloading only the public source will not receive your ignored local database or historical data. They can run the setup check and portable tests, but scoring currently requires a validated prepared snapshot imported using the README instructions. A fully automatic ticker-to-results workflow is still under development.

## Credentials

Local tests, input checks, and prepared-snapshot scoring need no API keys. SEC retrieval needs an organization/contact identifier, entered privately in the terminal when needed or supplied as `APAM_SEC_USER_AGENT` through the environment. It is sent to SEC as a request header and is not saved by the application. Never place credentials in ticker files, source code, or Git. There is currently no paid-vendor adapter or vendor-key setup.

## Common setup problems

- Python command missing: install or locate Python 3.11+ and reopen the terminal.
- Package not found: confirm you installed from the project root and are using `.venv\Scripts\python.exe`.
- Snapshot missing: a source-only download does not include local prepared data. Do not change an old snapshot's date to manufacture a new one.
- Duplicate or invalid ticker row: correct the indicated row, then rerun `check-setup`.

See `customer-release-build.md` for the remaining implementation stages.

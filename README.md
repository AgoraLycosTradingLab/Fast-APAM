# Fast APAM

**Quarterly and trailing-twelve-month business-trend research in Python.**

Fast APAM measures recent operating strength, acceleration, and deterioration. It is a separate companion to Core APAM, which measures durable annual business quality.

**Development status: provisional research pilot.** The validated implementation covers an Information Technology operating-company cohort and runs prepared, validated snapshots. Automatic preparation and scoring from customer tickers are still under development. This is not a valuation model or a production-approved investment system.

[Quick start](#quick-start) · [Model logic](docs/model-logic.md) · [Data sources](docs/data-sources.md) · [Results guide](docs/results-guide.md)

## Current capabilities

| Capability | Status |
|---|---|
| Run a prepared snapshot for an explicit model date | Available |
| Reuse unchanged calculations with checksum-verified caching | Available |
| Export results, exceptions, and run details | Available |
| Export detailed evidence and audits as a ZIP | Available |
| Retrieve uncached SEC documents from a reviewed filing index | Available |
| Check a customer ticker CSV offline | Available; format validation only |
| Turn arbitrary tickers into a complete scoring run | Under development |
| Paid-provider API integration | Not implemented |
| Additional sector modules or historical as-filed backtest validation | Not established by this pilot |

Local checks, tests, and prepared-snapshot scoring need no credentials. SEC downloads use an organization/contact identifier through hidden terminal entry or an environment variable. No paid API key is currently required.

## Requirements

- Python **3.11 or newer**.
- A terminal or Python IDE such as VS Code. Git is optional with a ZIP download.
- **lxml** and **tzdata**, installed by the command below. [pyproject.toml](pyproject.toml) is the authoritative dependency list.
- Internet access for installing packages and retrieving new filings.
- For scoring: validated financial inputs, dated membership/classification evidence, and adequate peer coverage. A ticker list alone is insufficient.

See [software and data requirements](docs/requirements.md).

## Quick start

On [the repository page](https://github.com/AgoraLycosTradingLab/Fast-APAM), choose **Code > Download ZIP** and extract it, or clone it:

```text
git clone https://github.com/AgoraLycosTradingLab/Fast-APAM.git
```

Open the folder containing `pyproject.toml` in VS Code.

In **Windows PowerShell**, run these commands one at a time:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe -m fast_apam check-setup --date 2026-09-25 --universe examples/universe.csv
```

Expected output includes `INPUT_FORMAT_VALID`, three requested tickers, and `ready_to_score: false`. This validates file format only; it does not establish issuer eligibility or download financial data. The example date is historical, not a dynamic “today” setting.

Copy `examples/universe.csv` to a root-level `universe.csv` and edit that copy for your own setup check. The personal root file is ignored by Git. Never put credentials in it.

On macOS/Linux, create the environment with `python3 -m venv .venv` and use `.venv/bin/python` instead of the Windows executable. See the [VS Code walkthrough](docs/vscode-quickstart.md).

## Run a prepared snapshot

A source-only download does **not** include the developer's local database or historical financial datasets. Scoring currently requires the [prepared input contract](docs/configuration.md#prepared-snapshot-inputs).

With your environment's Python selected:

```text
python -m fast_apam run --date 2026-09-25 --source "PATH_TO_VALIDATED_PREPARED_INPUTS" --output outputs/september-test --verify
```

The source path is a placeholder. `--verify` requires frozen reference outputs supplied with the snapshot. For a validated new snapshot without references, omit it; source and scoring gates still apply. The customer ticker file is not yet an input to `run`.

After import, rerun the snapshot without `--source`. Output folders must be new or empty. Select dates explicitly; never relabel old data to create a new snapshot.

## Outputs

| File | Contents |
|---|---|
| `results.csv` | Scores, business trends, confidence, data status, dates, and source-related fields |
| `exceptions.csv` | Unscored companies and recorded reasons |
| `run.json` | Completion metadata, fingerprints, coverage, and requested reference checks |

**Illustrative presentation only. These fictional values are not model calculations.**

| Fictional company | Provisional score | Business trend | Data status |
|---|---:|---|---|
| Example A | 82.0 | Accelerating | Partial |
| Example B | 77.0 | Decelerating | Partial |
| Example C | — | Unscored | Insufficient history |

A high relative score can coexist with deceleration. Unscored does not mean zero. Confidence is separate from score and is not a probability of investment success. See the [results guide](docs/results-guide.md).

## Model approach

1. Establish dated issuer identity, periods, and filing availability.
2. Construct validated standalone quarters and TTM windows.
3. Measure comparable-quarter YoY and TTM YoY changes.
4. Validate metric and peer coverage before normalization and scoring.
5. Apply the recorded research policy and retain lineage and exceptions.

Raw sequential QoQ changes have **zero primary-signal weight**. Acceleration contributes to score and status; it is not an automatic exclusion gate. Percentage growth is not calculated from zero or negative comparison bases. Approved absolute-change fallbacks remain separately identified.

Read the [model guide](docs/model-logic.md) and [governing specifications](docs/methodology/). The guide does not replace those specifications.

## Documentation

| Guide | Contents |
|---|---|
| [VS Code quick-start](docs/vscode-quickstart.md) | Install, check inputs, and test a local snapshot |
| [Requirements](docs/requirements.md) | Python, packages, environments, and financial inputs |
| [Data sources and APIs](docs/data-sources.md) | SEC access, credentials, and integration limits |
| [Configuration](docs/configuration.md) | Dates, ticker files, prepared inputs, storage, and commands |
| [Model logic](docs/model-logic.md) | Signals, factors, fallback handling, and safeguards |
| [Results guide](docs/results-guide.md) | Scores, statuses, exceptions, and audits |
| [Troubleshooting](docs/troubleshooting.md) | Installation, data, and run problems |
| [Security policy](SECURITY.md) | Credential handling and reporting status |
| [Customer release plan](docs/customer-release-build.md) | Remaining implementation stages |
| [Changelog](CHANGELOG.md) | Development changes |

## Validation

The customer-setup milestone passed **140 portable tests**. Local reference validation matched six tables for each of July 31 and September 25, 2026: **12 exact comparisons**, including results and source lineage. Those local fixtures are not bundled in a source download. These checks demonstrate regression consistency, not investment performance or production approval.

```text
python -m unittest discover -s tests
```

A [Windows/Linux CI workflow](.github/workflows/tests.yml) is included. Its presence is not a claim that a hosted GitHub run has passed. See the [validation record](docs/customer-setup-validation.json).

## Repository layout

```text
src/fast_apam/       Python package, commands, and calculation engine
tests/              Portable tests and synthetic controls
examples/           Example ticker input
docs/               User guides, validation, and methodology
.github/workflows/  Automated test configuration
pyproject.toml      Package metadata and dependencies
```

Local databases, downloads, results, audit exports, credentials, and virtual environments are excluded from normal Git tracking. Historical `MSFT_IT_...` names remain at the prepared-input compatibility boundary to preserve evidence references.

## License and release status

The software and associated project documentation are licensed under the [MIT License](LICENSE), copyright 2026 Douglas Salone. Third-party packages, financial datasets, filings, and licensed classifications retain their own applicable terms; this license does not grant rights to third-party material. See [SECURITY.md](SECURITY.md) for private-reporting setup status and the [publication checklist](docs/publication-checklist.md) for remaining repository settings.

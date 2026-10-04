# Customer Python release: implementation brief

Prepared October 3, 2026. This brief defines software delivery work; it does not approve new financial methodology, scoring universes, production status, or redistribution rights.

## Intended customer experience

Download the source ZIP or clone the repository, open it in a Python IDE, install dependencies in a local virtual environment, supply a ticker CSV and explicit model date, enter any required provider credentials privately, and run locally. Results should include scores, business-trend classifications, exceptions, and an optional audit export. No application installer, hosted service, or GUI is required for the first release.

## Reuse and present limitations

Reuse `src/fast_apam/engine` for the governed calculations, `snapshots.py` for existing prepared imports, `storage.py` for immutable compressed evidence and cached runs, `runner.py` for orchestration and exact reference comparisons, and `acquisition.py` plus `credentials.py` for incremental SEC-document retrieval and private identification. Preserve the July and September reference snapshots and all governing documents under `docs/methodology`.

The current source package does not build a complete scoring snapshot from arbitrary tickers. The importer still expects Wave1/Wave2 inputs and compatibility outputs. Existing SEC retrieval starts with a reviewed filing index. Historical prepared inputs and the local database are ignored by Git and are not a public sample dataset. The existing distribution wheel is the earlier consolidation build; install the current source to test new setup features until a new release artifact is built.

## Governing constraints and unresolved scope

- The Data Contract specifies a point-in-time S&P 500 universe. Customer ticker entry is a request list, not permission to score arbitrary securities or replace the approved peer cohort.
- The validated implementation is the IT operating-company research pilot. Other sectors, banks, insurers, REITs, foreign reporting regimes, and new universe methodologies need governed adapters and validation before score publication.
- Dated issuer identity, membership, and sector classification need evidence. Current ticker or sector labels cannot be projected backward.
- The dated peer-decision document retains its historical `AWAITING APPROVAL` status and limited pilot proposal. Preserve it with the later decision records and run policy. This brief cannot promote the pilot exception to production approval.
- The approved peer hierarchy and per-metric coverage gates remain authoritative. Do not lower coverage floors to accommodate a small customer list.
- Quarter-YoY and TTM-YoY signals, zero raw sequential-QoQ primary weight, fallback separation, FCF construction, filing availability, restatement checks, and missing-data rules remain unchanged.

SEC is the initial software data source because it is already implemented and the governing accounting truth layer. Paid-provider integration remains an optional later convenience/cross-check layer until a specific provider and field mapping are selected. API keys alone do not supply historical membership or classification rights/evidence.

## Delivery milestones and acceptance checks

| Stage | Deliverable | Acceptance |
|---|---|---|
| 1. Customer setup | IDE quick-start, example ticker file, offline `check-setup` | Works without private snapshots or credentials; bad input fails clearly; no scoring claim |
| 2. Dated universe resolution | Resolve requested securities to issuer identities; validate membership, routing and dated peer evidence | Unknown, ambiguous, unsupported and out-of-universe securities receive explicit exceptions; watchlist changes do not silently change normalization |
| 3. Automatic data preparation | Build eligible filing index, retrieve missing evidence, select canonical facts, construct quarters/TTM/YoY and controls | Reuse existing methods; block unresolved source conflicts; produce reviewed input contract without manual dated code copies |
| 4. Customer run orchestration | Connect prepared inputs to existing scoring and export requested-company results | Preserve peer cohort and lineage; coverage gates precede normalization; failed/incomplete runs cannot appear successful |
| 5. Distribution validation | Clean-machine source install, reproducible test fixtures, release archive and documented support | No personal data or credentials; exact historical regression checks; portable tests pass; MIT license included and third-party data rights reviewed before publication |

Keep stages small enough to review. Stage 1 is implemented as a preparation milestone. Stages 2–5 remain open. Do not describe the new setup command as the completed customer product.

## Credential and distribution rules

Use hidden terminal entry or environment configuration. Do not include credentials in arguments, CSVs, logs, errors, audit bundles, Git history or sample files. The current command keeps entered SEC identification in memory; it does not persist credentials. If persistent storage becomes necessary, use a supported OS credential store in a separately tested change.

Source releases should contain code, tests, governing documentation, and synthetic/example inputs. Exclude the local database, downloaded filings, customer lists, results, archives, virtual environments, and private configuration. Git ignore rules alone are not a release audit. Inspect the actual archive and tracked history before publication. The original preparation stage did not authorize publication. The owner subsequently authorized creation and population of https://github.com/AgoraLycosTradingLab/Fast-APAM.

## Next implementation stage

The October 3 acquisition milestone added the Windows launcher and `prepare-data`: current SEC issuer discovery, recent/archived filing metadata, cutoff-filtered financial candidates and source evidence. The October 4 continuation adds latest-eligible-vintage filing targets and a separate `verify-contexts` command that downloads those targets and audits inline XBRL facts and contexts. See [customer preparation](customer-preparation.md). These additions do not close stages 2–5. Next, complete dated issuer and peer evidence, reconcile inline contexts to canonical Company Facts, construct quarters and TTM/YoY, and connect the preserved scoring engine. FAPAM-004 permits personal files operationally while retaining dated eligibility requirements.

# Software and data requirements

| Requirement | Current declaration |
|---|---|
| Python | 3.11 or newer |
| lxml | 4.9 or newer; XML/HTML processing |
| tzdata | 2024.1 or newer; time-zone database |
| Build backend | setuptools 68 or newer |
| Tests | Standard-library unittest |
| IDE | Optional; Windows VS Code walkthrough provided |
| Git | Optional when downloading a ZIP |

[pyproject.toml](../pyproject.toml) is authoritative. `python -m pip install -e .` installs declared dependencies. A second manually maintained package list is unnecessary. Version lower bounds are not a locked dependency environment; release dependency locking and vulnerability review remain distribution work.

The workflow defines Windows and Ubuntu tests on Python 3.11/3.12. Local validation was performed on Windows. Workflow configuration does not prove hosted CI or macOS validation.

No Docker, Node.js, Excel, external database server, administrator access, or paid API subscription is required for the implemented commands. SQLite comes with Python. Internet access is needed to install uncached dependencies and acquire new filings. Disk needs depend on retained evidence and history; no general minimum memory/disk benchmark is claimed.

Scoring requires dated identity, membership, routing and peer evidence, comparable quarters and TTM periods, filing availability, canonical facts, controls, lineage, and the recorded run policy. A source-only download contains tests and example tickers, not the developer's financial database. See [configuration](configuration.md).

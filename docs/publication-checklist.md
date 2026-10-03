# Publication checklist

The source repository is [AgoraLycosTradingLab/Fast-APAM](https://github.com/AgoraLycosTradingLab/Fast-APAM). This checklist records completed setup and remaining release work.

## Owner decisions before public release

- Completed: the software uses the [MIT License](../LICENSE), attributed to Douglas Salone, with license metadata in pyproject.toml.
- Confirm ownership and redistribution rights for source, methodology documents, and any proposed data fixtures.
- Completed: GitHub Private Vulnerability Reporting was enabled and verified in repository settings on October 3, 2026. Maintainers should keep security-alert subscriptions current.
- Repository: AgoraLycosTradingLab/Fast-APAM. Choose a release version before publishing packaged releases. Do not label the project production-ready or advertise automatic customer-universe scoring.

## Review the actual distribution

- Include code, portable tests, documentation, workflow, package metadata, placeholder environment example, and example ticker input.
- Exclude databases, raw filings, customer universes, results, audits, virtual environments, build directories and credentials.
- Inspect tracked files and Git history; ignore patterns alone do not prove that secrets were never committed.
- Run portable tests from a clean environment and the documented setup example.
- Run the two local historical regressions without publishing their private/local fixtures.
- Build a fresh source/wheel artifact only after selecting release metadata; the old 0.2.0 local wheel predates newer source features.
- Review dependencies and decide how to lock release versions. Run hosted CI after the repository is created.
- Inspect internal Markdown links and the rendered README. Avoid badges or download links to repositories/releases that do not exist.

## Suggested repository metadata

Description: Quarterly and TTM operating-company trend research in Python, with validated snapshots and auditable outputs.

Suggested topics: python, financial-analysis, sec-edgar, fundamental-analysis, research.

Initial release description should say: development research pilot; prepared-snapshot scoring available; custom-universe preparation under development.

The source repository is public. No packaged release is claimed by this checklist.

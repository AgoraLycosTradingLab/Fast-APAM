# Security

## Current support status

This is a development research project. There is no established security response-time commitment or production support policy.

## Reporting vulnerabilities

Do not post credentials, customer data, or exploitable vulnerability details in a public issue.

**GitHub Private Vulnerability Reporting is enabled** for [AgoraLycosTradingLab/Fast-APAM](https://github.com/AgoraLycosTradingLab/Fast-APAM). Activation was verified in repository settings on October 3, 2026. Use the repository's [Security Advisories page](https://github.com/AgoraLycosTradingLab/Fast-APAM/security/advisories) to report privately. The [custom report form](.github/VULNERABILITY_REPORT.yml) requests only the information needed for investigation.

Use **Security > Advisories > Report a vulnerability** on the GitHub repository. Reports should include the affected version, a summary, impact, and reproduction steps using synthetic inputs. Never include real credentials or customer financial data. If the private-report button is unavailable, request a private contact without disclosing vulnerability details publicly.

### Repository administrator setup

1. Open the public repository's **Settings > Advanced Security** and enable **Private vulnerability reporting**.
2. Confirm **Report a vulnerability** appears under **Security > Advisories**. Merely committing this policy/form does not enable reporting.
3. Subscribe to repository security-alert notifications and confirm the intended maintainers will receive them.
4. Keep the reporting link and maintainer subscriptions current. Do not submit a dummy security report to test notifications.

A SECURITY.md file or report form alone does not activate reporting. This repository's setting was enabled separately. No separate disclosure mailbox is provided.

See [GitHub's private reporting configuration](https://docs.github.com/en/code-security/how-tos/report-and-fix-vulnerabilities/configure-vulnerability-reporting/configure-for-a-repository).

## Credentials and local data

- The current customer CLI needs no paid-provider API keys.
- SEC identification is supplied by hidden terminal entry or `APAM_SEC_USER_AGENT`.
- Entered identification stays in memory for the command and is sent to SEC as a request header. The credential helper does not save it to a file or database.
- Hidden entry refuses a visible-input fallback. Unattended runs need environment configuration.
- `.env.example` contains placeholders only; `.env` is not automatically loaded.
- Local databases and audit exports can contain financial evidence and customer-specific data. They are not encrypted credential stores.
- Git ignore rules do not remove files already tracked or protect arbitrary files outside their patterns.

Use a project-specific Python environment. Inspect downloaded source and dependencies before execution. No administrator privileges are needed by the documented workflow. Prepared inputs and run settings should come from trusted sources; auditability does not make the application a sandbox for hostile files.

Do not include real secrets in source, command arguments, test fixtures, logs, screenshots, issue reports, or audit bundles. If a secret is exposed, remove it from public material and revoke/rotate it with its provider.

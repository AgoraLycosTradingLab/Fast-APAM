# Data sources and APIs

| Source | Purpose | Implementation | Current boundary |
|---|---|---|---|
| SEC EDGAR filing archive | Original documents and inline XBRL evidence | `fetch-new-filings`; `acquisition.py` | Requires an already reviewed dated filing index |
| SEC submissions JSON | Filing history and accession metadata | `engine/sec_filing_index.py` | Preserved library component; not a complete customer pipeline |
| SEC Company Facts JSON | Reported XBRL facts | `engine/sec_companyfacts_acquisition.py` | Canonical selection and context validation still required |
| Prepared snapshot files | Reviewed roster, periods, observations, controls and policy | `import-snapshot` or `run --source` | Current supported scoring input |
| Dated membership/classification evidence | Universe and peer eligibility | Imported evidence and governing records | Not supplied automatically by entering an API key |

The public SEC data APIs do not require API keys. See [SEC API documentation](https://www.sec.gov/search-filings/edgar-application-programming-interfaces). The archive downloader accepts HTTPS URLs under `www.sec.gov/Archives/edgar/data/` from its reviewed index.

## Identification and access

The application uses `APAM_SEC_USER_AGENT` for an organization/contact identifier. If absent when a new document is needed, an interactive terminal requests hidden entry. It is kept for that command and sent to SEC in a request header. Cached-only retrieval needs no prompt. Unattended execution must receive the variable through its environment.

`.env.example` is a placeholder reference; `.env` is not automatically loaded. Never place identification or future API keys in source code, input CSVs, or command arguments.

Follow [SEC developer access guidance](https://www.sec.gov/about/developer-resources). The archive downloader runs sequentially with a delay and caches successful downloads. It is not a cross-process rate limiter. Failed retrievals can be retried by rerunning the command. Downloading a document does not approve it for scoring.

## Not integrated

FMP is named as a possible structured convenience layer in the Data Contract, but the customer CLI has no FMP adapter. No paid-provider keys are requested. Prices, forecasts, broker execution and valuation APIs are not required for the implemented workflow.

Historical membership and classification may require separate access and redistribution arrangements. Current metadata cannot establish historical identity or classification. Vendor values cannot silently replace conflicting SEC facts. See the [Data Contract](methodology/Data_Contract.md).

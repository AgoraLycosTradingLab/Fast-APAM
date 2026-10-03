# Fast APAM Data Contract

**Project:** Fast APAM Model  
**Version:** 0.1  
**Status:** Approved design baseline; implementation pending  
**Governing documents:** `Fast_APAM_Project_Charter_v0.1.md`, `Decision_Register.md`  
**Last updated:** 2026-09-19

## 1. Purpose

This contract defines the data that Fast APAM may ingest, how every observation is identified, when it becomes available, how source conflicts and restatements are handled, and what lineage is required before quarterly or trailing-twelve-month metrics can be calculated.

Fast APAM preserves the Core APAM economic logic while measuring recent change through comparable-quarter year-over-year and TTM comparisons. This contract covers data semantics only; it does not define factor weights or production code.

## 2. Approved governing rules

1. Initial universe: point-in-time S&P 500.
2. Accounting truth layer: SEC filings.
3. Structured convenience layer: FMP or an equivalent vendor.
4. Primary availability rule: SEC acceptance timestamp plus one full trading day.
5. Quarterly comparison: issuer fiscal quarter versus the same prior-year issuer fiscal quarter.
6. TTM: latest four validated standalone fiscal quarters.
7. Q2 and Q3 cumulative flows may be reconstructed into standalone quarters.
8. Q4 flows may be derived from annual totals minus nine-month YTD totals.
9. Both as-filed and latest-restated histories must be preserved.
10. Initial production-grade model uses filed fundamentals only.
11. Period construction must be validated before composite scoring begins.

## 3. Data-layer boundaries

| Layer | Purpose | Permitted sources | May drive v1 scores? |
| --- | --- | --- | --- |
| Universe | Point-in-time eligibility and identity | Historical S&P membership, SEC, approved reference data | Yes |
| Raw filing | Preserve original facts and filing context | SEC submissions, companyfacts, inline XBRL, filed statements | Yes |
| Standardized fact | Map raw facts to canonical concepts | SEC-derived mappings; vendor cross-check | Yes |
| Constructed period | Standalone quarters and TTM windows | Validated standardized facts | Yes |
| Sector metric | Economically appropriate calculated measures | Constructed periods | Yes |
| Preliminary information | Earlier but unaudited/unfiled updates | Earnings releases, supplements | No—deferred |
| Forward information | Expectations | Estimates, guidance, transcripts | No—deferred |
| AI evidence | Attribution research | Filings, transcripts, disclosures | Separate layer only |

## 4. Source hierarchy and conflict policy

### 4.1 Precedence

1. SEC-filed financial statements and filing facts.
2. Company-filed reconciliations and supplemental schedules incorporated into a filing.
3. Structured vendor fields.
4. Manual review for unresolved material differences.

### 4.2 Conflict rules

- A vendor value cannot silently replace a conflicting filed value.
- Conflicts must retain both raw values, sources, retrieval timestamps, and the selected canonical result.
- The resolution must state whether the difference is caused by taxonomy mapping, units, currency, dimensions, duration, restatement, non-GAAP treatment, discontinued operations, or vendor transformation.
- Unresolved material conflicts produce `REVIEW_REQUIRED` and cannot receive a production score for the affected factor.
- Materiality tolerances will be finalized during test-fixture validation and recorded in the Decision Register.

## 5. Canonical entities

### 5.1 Issuer

| Field | Type | Required | Definition |
| --- | --- | --- | --- |
| `issuer_id` | string | Yes | Stable internal issuer identifier. |
| `cik` | string | Yes | Ten-digit SEC Central Index Key, preserving leading zeros. |
| `legal_name` | string | Yes | Legal registrant name applicable to the record date. |
| `lei` | string/null | No | Legal Entity Identifier when available. |
| `domicile_country` | string | Yes | Issuer domicile at the applicable date. |
| `reporting_currency` | string | Yes | Currency used in the filing. |
| `fiscal_year_end` | month-day | Yes | Fiscal-year-end applicable to the period. |

### 5.2 Security identity

| Field | Type | Required | Definition |
| --- | --- | --- | --- |
| `security_id` | string | Yes | Stable internal security identifier. |
| `ticker` | string | Yes | Ticker valid on `effective_from`. |
| `exchange` | string | Yes | Listing exchange valid on the date. |
| `share_class` | string/null | Conditional | Share class where multiple listed classes exist. |
| `effective_from` | date | Yes | First date the identity record is valid. |
| `effective_to` | date/null | Yes | Last valid date; null for current record. |

Ticker is not a permanent issuer key. Historical ticker changes must not create a new issuer unless the legal/economic entity changes.

### 5.3 Universe membership

| Field | Type | Required | Definition |
| --- | --- | --- | --- |
| `universe_name` | string | Yes | Initially `SP500`. |
| `security_id` | string | Yes | Eligible security. |
| `membership_start` | date | Yes | First effective membership date. |
| `membership_end` | date/null | Yes | Final effective membership date. |
| `membership_source` | string | Yes | Provenance for the membership interval. |
| `knowledge_timestamp` | datetime | Yes | When the membership event became knowable. |

Historical model runs must use membership known on the evaluation date. A current personal universe file is not sufficient for historical eligibility unless it contains valid membership intervals.

### 5.4 Sector classification

| Field | Type | Required | Definition |
| --- | --- | --- | --- |
| `issuer_id` | string | Yes | Issuer receiving the classification. |
| `classification_system` | string | Yes | Initially GICS or an explicitly documented substitute. |
| `sector` | string | Yes | Sector valid on the effective date. |
| `industry_group` | string/null | No | Industry group. |
| `industry` | string/null | No | Industry. |
| `sub_industry` | string/null | No | Sub-industry. |
| `effective_from` | date | Yes | First valid date. |
| `effective_to` | date/null | Yes | Last valid date. |
| `classification_source` | string | Yes | Source provenance. |

The sector module must be selected using the classification available on the model date.

## 6. Filing entity

Every filing record must contain:

| Field | Type | Required | Definition |
| --- | --- | --- | --- |
| `accession_number` | string | Yes | Exact SEC accession identifier. |
| `cik` | string | Yes | Filing registrant CIK. |
| `form_type` | string | Yes | Such as 10-Q, 10-K, 10-Q/A, or 10-K/A. |
| `filed_date` | date | Yes | SEC filing date. |
| `accepted_timestamp` | datetime | Yes | SEC acceptance time in the source timezone. |
| `accepted_timestamp_utc` | datetime | Yes | Normalized UTC timestamp. |
| `report_period` | date | Yes | Filing period-of-report date. |
| `fiscal_year` | integer/string | Yes | Issuer fiscal year label. |
| `fiscal_period` | enum | Yes | FY, Q1, Q2, Q3, or transition/stub label. |
| `amends_accession` | string/null | No | Prior accession amended by this filing. |
| `is_amendment` | boolean | Yes | Whether the filing is an amendment. |
| `source_url_or_locator` | string | Yes | Reproducible source locator. |
| `retrieved_timestamp_utc` | datetime | Yes | When the data was retrieved. |
| `model_available_date` | date | Yes | First model date permitted by the availability rule. |

### Availability rule

`model_available_date` is the first eligible trading day after one full trading day has elapsed following SEC acceptance. The implementation must use an exchange trading calendar, not simple calendar-day addition.

Same-day and two-trading-day alternatives are retained only for sensitivity tests.

## 7. Raw fact contract

Every source fact must remain immutable and retain:

| Field | Type | Required | Definition |
| --- | --- | --- | --- |
| `raw_fact_id` | string | Yes | Stable identifier for the exact source fact. |
| `accession_number` | string | Yes | Filing containing the fact. |
| `taxonomy` | string | Yes | Taxonomy namespace/version. |
| `concept` | string | Yes | Exact reported XBRL concept. |
| `label` | string/null | No | Filing label. |
| `value` | decimal | Yes | Unscaled numeric value. |
| `unit` | string | Yes | Exact XBRL unit. |
| `decimals` | string/integer/null | No | Reported precision. |
| `scale` | integer/null | No | Reported presentation scale if applicable. |
| `period_type` | enum | Yes | `DURATION` or `INSTANT`. |
| `period_start` | date/null | Conditional | Required for duration facts. |
| `period_end` | date | Yes | End date or instant date. |
| `duration_days` | integer/null | Conditional | Inclusive/exclusive convention must be documented consistently. |
| `dimensions` | structured object | Yes | All explicit XBRL dimensions; empty only for consolidated default facts. |
| `statement_role` | string/null | No | Statement/presentation role. |
| `fiscal_year` | string/integer/null | No | Source fiscal-year tag. |
| `fiscal_period` | string/null | No | Source fiscal-period tag. |
| `frame` | string/null | No | SEC frame when provided; never used alone to establish period identity. |
| `source_type` | enum | Yes | SEC XBRL, filed table, vendor, or manual-reviewed source. |
| `retrieved_timestamp_utc` | datetime | Yes | Retrieval time. |

Raw facts are append-only. Corrections create new records or new filing vintages; they do not overwrite the source record.

## 8. Canonical financial concepts

Each standardized observation maps one or more raw concepts to a controlled canonical concept.

### 8.1 Universal operating-company concepts

| Canonical concept | Period type | Required priority | Notes |
| --- | --- | --- | --- |
| `revenue` | Duration | Critical | Sector-appropriate top-line output; mapping must exclude financing components when inappropriate. |
| `operating_income` | Duration | Critical | Primary operating-profit concept. |
| `ebit` | Duration | Important | Standardized definition documented separately; do not assume identical to operating income. |
| `cash_from_operations` | Duration | Critical | Continuing consolidated operations where possible. |
| `capital_expenditures` | Duration | Critical for FCF | Classification policy must be consistent. |
| `free_cash_flow` | Duration | Derived | CFO minus approved capex definition. |
| `total_assets` | Instant | Important | Used with appropriate averaging rules. |
| `current_assets` | Instant | Conditional | Used in invested-capital construction. |
| `current_liabilities` | Instant | Conditional | Used in invested-capital construction. |
| `cash_and_equivalents` | Instant | Conditional | Invested-capital adjustment. |
| `total_debt` | Instant | Conditional | Capital and leverage context. |
| `income_tax_expense` | Duration | Conditional | NOPAT/effective-tax calculations. |
| `pretax_income` | Duration | Conditional | Tax-rate diagnostics. |
| `employee_count` | Instant/as-of disclosure | Important | Usually annual; must include disclosure date and quality class. |

### 8.2 Financials concepts

Financials use sub-industry contracts. At minimum, preserve the following families rather than forcing generic operating-company definitions:

- Banks: net interest income, noninterest income, noninterest expense, provision for credit losses, loans, deposits, average earning assets where filed, capital ratios, and asset-quality fields.
- Insurers: premiums, underwriting result inputs, claims/losses, expenses, investment income, reserve-development and catastrophe fields where available.
- Asset managers/brokers: net revenue, compensation expense, non-compensation expense, operating income, AUM/client assets, and flow/activity fields where available.

### 8.3 Equity REIT concepts

- Rental and total revenue.
- Property operating expenses and NOI inputs.
- FFO and reconciliation components.
- Normalized FFO/AFFO inputs when filed and definitionally traceable.
- Recurring capital expenditures.
- Occupancy, same-store revenue/NOI, and leasing metrics where filed.
- Debt, interest expense, shares/units, and property/area measures.

Generic net income and generic FCF will not be primary REIT productivity signals.

## 9. Standardized fact contract

| Field | Type | Required | Definition |
| --- | --- | --- | --- |
| `standardized_fact_id` | string | Yes | Stable identifier. |
| `issuer_id` | string | Yes | Canonical issuer. |
| `canonical_concept` | string | Yes | Controlled concept name. |
| `value` | decimal | Yes | Standardized value. |
| `currency` | string/null | Conditional | Required for monetary facts. |
| `period_type` | enum | Yes | `DURATION`, `INSTANT`, or approved as-of disclosure type. |
| `period_start` | date/null | Conditional | Duration start. |
| `period_end` | date | Yes | Duration end or instant date. |
| `duration_days` | integer/null | Conditional | Duration length. |
| `fiscal_year` | string/integer | Yes | Canonical fiscal-year identity. |
| `fiscal_quarter` | enum | Yes | Q1, Q2, Q3, Q4, FY, STUB, or TRANSITION. |
| `period_basis` | enum | Yes | `STANDALONE`, `YTD`, `ANNUAL`, `INSTANT`, or `AS_OF`. |
| `value_origin` | enum | Yes | `DIRECT`, `MAPPED`, `DERIVED`, or `MANUAL_REVIEWED`. |
| `accession_number` | string | Yes | Filing vintage. |
| `accepted_timestamp_utc` | datetime | Yes | Point-in-time availability basis. |
| `model_available_date` | date | Yes | First eligible model date. |
| `mapping_rule_id` | string | Yes | Versioned taxonomy-to-canonical rule. |
| `consolidation_scope` | string | Yes | Consolidated, segment, parent-only, or other scope. |
| `continuing_operations_flag` | boolean/null | No | Continuing-operation treatment. |
| `quality_status` | enum | Yes | Data-quality disposition. |

## 10. Canonical fiscal-period identity

Every constructed period must have:

- `issuer_id`
- `fiscal_year`
- `fiscal_quarter`
- `period_start`
- `period_end`
- `duration_days`
- `period_basis`
- `calendar_year_end`
- `calendar_quarter_end`
- `fiscal_calendar_version`
- `is_52_53_week_year`
- `extra_week_flag`
- `transition_period_flag`
- `comparable_period_id`

Issuer fiscal identity controls comparisons. Calendar fields are descriptive and may support reporting, but they do not replace fiscal-quarter matching.

## 11. Standalone-quarter construction contract

### 11.1 Flow facts

- Q1 = validated direct three-month fact.
- Q2 = validated direct Q2 fact when unambiguous; otherwise six-month YTD minus Q1.
- Q3 = validated direct Q3 fact when unambiguous; otherwise nine-month YTD minus six-month YTD.
- Q4 = annual FY minus nine-month YTD.

### 11.2 Compatibility requirements

Parent facts used in subtraction must match on:

- Issuer and fiscal year.
- Canonical concept.
- Currency and unit.
- Consolidation scope.
- Dimensions.
- Continuing/discontinued-operation basis.
- Restatement/vintage basis.
- Compatible fiscal calendar.

### 11.3 Prohibited operations

- Do not subtract instant balance-sheet facts.
- Do not subtract ratios, margins, or per-share values.
- Do not combine reported and restated parents without explicit version alignment.
- Do not force a derived quarter when a fiscal transition or taxonomy mismatch prevents reconciliation.

### 11.4 Direct-versus-derived precedence

A direct standalone value is preferred only when its duration and context clearly represent the intended quarter. Otherwise the system may prefer the cumulative reconstruction and must flag the difference for review when material.

## 12. TTM construction contract

For duration facts:

`TTM(t) = Q(t) + Q(t-1) + Q(t-2) + Q(t-3)`

Requirements:

- Four validated consecutive standalone fiscal quarters.
- Compatible concept definitions, currency, scope, and continuing-operation basis.
- No unresolved stub or transition period.
- Each quarter must have been available by the evaluation date.

For instant denominators used in TTM ratios, use a separately approved averaging rule. Instantaneous values are never summed.

TTM comparison is primarily the latest TTM versus the TTM ending four issuer fiscal quarters earlier.

## 13. Restatement and vintage contract

Each observation must support:

| Field | Definition |
| --- | --- |
| `vintage_id` | Unique data vintage. |
| `vintage_available_timestamp` | When the vintage became knowable. |
| `supersedes_vintage_id` | Earlier vintage replaced for current diagnostics. |
| `as_filed_value` | Value used at the historical evaluation date. |
| `latest_restated_value` | Latest known comparable value. |
| `restatement_difference` | Absolute difference. |
| `restatement_difference_pct` | Relative difference when meaningful. |
| `restatement_material_flag` | Whether the change exceeds the approved tolerance. |

Backtests must query `AS_FILED` as of the evaluation date. Current research may use `LATEST_RESTATED`, but the view must be labeled.

## 14. Employee-count contract

Employee observations require:

- Count.
- As-of date.
- Filing/accession or exact disclosure source.
- Full-time, full-time-equivalent, total workforce, or other definition.
- Inclusion of contractors where stated.
- Geographic or segment scope where applicable.
- Acquisition/divestiture context when disclosed.
- `employee_signal_class`: `OBSERVED_EMPLOYEE`, `CARRIED_EMPLOYEE`, or `NO_EMPLOYEE_SIGNAL`.
- `employee_data_age_days` on the model date.

A carried annual count must never be presented as a fresh quarterly measurement. Weight decay and maximum carry age remain a separate research decision.

## 15. Missing-data semantics

Missing is never zero. Every absent value must have a reason code.

| Code | Meaning |
| --- | --- |
| `NOT_FILED` | Issuer did not report the concept. |
| `NOT_APPLICABLE` | Concept is economically inapplicable to the sector/module. |
| `NOT_YET_AVAILABLE` | Filing existed for the period but was unavailable on the model date. |
| `INSUFFICIENT_HISTORY` | Required comparison periods do not exist. |
| `CONCEPT_UNMAPPED` | Source fact exists but lacks an approved canonical mapping. |
| `PERIOD_INCOMPARABLE` | Fiscal-calendar, duration, or scope mismatch prevents comparison. |
| `CONFLICT_UNRESOLVED` | Material source conflict remains unresolved. |
| `DERIVATION_FAILED` | Required parent facts are missing or incompatible. |
| `STALE` | Observation exceeds the approved age threshold. |
| `QUALITY_REJECTED` | Value failed a validation rule. |

## 16. Data-quality and lineage fields

Every scoreable observation must expose:

- Direct or derived origin.
- Raw source fact IDs.
- Filing accession number(s).
- Canonical mapping rule and version.
- Transformation rule and version.
- Parent observation IDs for derived values.
- Reconciliation difference and tolerance result.
- Model-availability date.
- Data age on evaluation date.
- Restatement vintage.
- Quality flags and review notes.
- Manual reviewer and date, if applicable.

If lineage cannot reproduce the value, the observation is not production-scoreable.

## 17. Quality statuses

| Status | Meaning | Score eligibility |
| --- | --- | --- |
| `PASS` | Complete and validated. | Eligible |
| `PARTIAL` | Some noncritical fields missing; minimum module coverage satisfied. | Conditionally eligible |
| `STALE` | Observation exceeds freshness threshold. | Module-dependent |
| `REVIEW_REQUIRED` | Material ambiguity or conflict. | Affected factor ineligible |
| `INSUFFICIENT_HISTORY` | Comparison window unavailable. | Ineligible for affected comparison |
| `SECTOR_MODULE_UNAVAILABLE` | Required methodology does not exist. | Ineligible |
| `PERIOD_INCOMPARABLE` | Period cannot be validly matched. | Ineligible |

Poor economic performance is not a data-quality failure. Valid negative results remain scoreable.

## 18. Required validation checks

### Identity and eligibility

- CIK format and historical ticker mapping.
- No duplicate active security identity.
- Point-in-time universe and sector validity.

### Filing and timing

- Unique accession identifiers.
- Acceptance time precedes model availability.
- No observation used before availability.
- Amendment links are valid.

### Fact integrity

- Units and currencies are valid.
- Duration/instant classification is correct.
- Dimensions and consolidation scope are preserved.
- Duplicate facts are resolved deterministically.

### Period construction

- Q1 + Q2 standalone equals six-month YTD within tolerance.
- Q1 + Q2 + Q3 standalone equals nine-month YTD within tolerance.
- Q1 + Q2 + Q3 + Q4 equals annual FY within tolerance.
- Four-quarter TTM windows contain consecutive fiscal quarters.
- Transition and extra-week cases are flagged.

### Point-in-time integrity

- Historical run reproduces only facts available by that date.
- Later restatements do not leak backward.
- Derived Q4 is unavailable before the annual filing.

## 19. Minimum implementation interfaces

The future system must be able to request data by:

- Issuer and evaluation date.
- Universe and evaluation date.
- Canonical concept and filing vintage.
- Fiscal year and fiscal quarter.
- `AS_FILED` or `LATEST_RESTATED` view.
- Direct-only or direct-plus-derived origin.
- Sector module and quality status.

The interface must return values together with availability, lineage, and quality metadata—not numbers alone.

## 20. Acceptance criteria for Data Contract v0.1

This contract is ready to support the next specification when:

1. Required entity, filing, fact, period, vintage, and lineage fields are accepted.
2. Source hierarchy and one-trading-day availability rule are accepted.
3. Missing-data codes and quality statuses are accepted.
4. Canonical concept lists are accepted as starting sets, with sector-specific expansion allowed through versioned amendments.
5. No composite scoring or implementation code is introduced before period-construction test cases exist.

## 21. Next document

Create `Period_Construction_Rules.md`. It should convert this contract into exact decision tables and worked examples for direct quarters, cumulative 10-Q reconstruction, Q4 derivation, TTM construction, restatements, 52/53-week years, and fiscal transition periods.

## 22. Revision history

| Version | Date | Change | Author |
| --- | --- | --- | --- |
| 0.1 | 2026-09-19 | Created initial Fast APAM data contract following approval of the foundational decisions. | Agora Lycos / Douglas Salone |


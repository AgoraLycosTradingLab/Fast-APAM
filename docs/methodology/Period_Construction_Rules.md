# Fast APAM Period Construction Rules

**Project:** Fast APAM Model  
**Version:** 0.1  
**Status:** Proposed accounting specification; implementation pending  
**Governing documents:** `Fast_APAM_Project_Charter_v0.1.md`, `Decision_Register.md`, `Data_Contract.md`  
**Last updated:** 2026-09-19

## 1. Purpose

This document defines how Fast APAM converts filed financial facts into comparable standalone fiscal quarters and trailing-twelve-month periods.

The objective is to ensure that every quarterly or TTM metric:

- uses only information available on the historical model date;
- respects the issuer's fiscal calendar;
- distinguishes direct reported values from reconstructed values;
- preserves filing and transformation lineage;
- handles amendments and restatements without look-ahead;
- fails visibly when periods cannot be compared; and
- supports year-over-year quarterly and TTM analysis without relying on raw sequential quarter-over-quarter change as a primary signal.

This document specifies accounting-period construction. It does not define FastScore weights or sector-specific scoring thresholds.

## 2. Governing principles

1. **Fiscal identity controls.** Compare an issuer's fiscal quarter with the same issuer's prior-year fiscal quarter.
2. **Availability controls history.** A period value may enter the model only after its filing becomes eligible under the approved availability rule.
3. **Direct does not automatically mean correct.** A direct quarterly fact must have the correct duration, scope, unit, dimensions, and fiscal identity.
4. **Derived values require complete lineage.** Every subtraction or sum must identify its parent facts and transformation rule.
5. **Instant facts are not flows.** Balance-sheet instants are neither subtracted nor summed to create quarters or TTM values.
6. **Ratios are recomputed.** Margins, returns, and per-share measures are calculated from compatible underlying observations rather than added or subtracted.
7. **Missing is not zero.** Failed construction produces an explicit reason code.
8. **Reported values remain primary.** Duration normalization for extra-week periods is a diagnostic, not a silent replacement.
9. **As-filed and restated histories remain separate.** Later knowledge cannot rewrite earlier model states.
10. **Uncertainty reduces eligibility or confidence.** The system does not force a value to maximize coverage.

## 3. Definitions

| Term | Definition |
| --- | --- |
| Standalone quarter | Flow attributable only to one fiscal quarter. |
| YTD flow | Cumulative flow from the fiscal-year start through the reporting date. |
| Annual flow | Flow covering the full issuer fiscal year. |
| Instant fact | Balance measured on a single date. |
| Direct value | Value explicitly reported for the intended period and context. |
| Derived value | Value constructed from two or more compatible parent observations. |
| TTM | Sum of four consecutive validated standalone fiscal quarters for a flow concept. |
| Vintage | Filing-specific version of a fact as it became available. |
| As-filed view | Facts available on a specified historical model date. |
| Latest-restated view | Most recent known comparable facts used for current diagnostics. |
| Comparable quarter | Same issuer fiscal-quarter identity in the prior fiscal year. |
| Stub period | Short or long period caused by a fiscal-calendar transition or transaction. |
| Extra-week period | Quarter or year containing an additional reporting week under a 52/53-week calendar. |

## 4. Required input fields

No period may be constructed unless the following are available or explicitly classified as not applicable:

- Issuer ID and CIK.
- Accession number and form type.
- SEC acceptance timestamp and model-available date.
- Canonical concept and original taxonomy concept.
- Value, unit, currency, and precision metadata.
- Period type: duration or instant.
- Period start and period end for duration facts.
- Period end for instant facts.
- Fiscal year and fiscal-period identity.
- Consolidation scope and all XBRL dimensions.
- Restatement/vintage identifier.
- Continuing-operations basis where relevant.
- Source and mapping-rule version.

If fiscal identity must be inferred, the inference rule and confidence flag must be stored.

## 5. Period classification

### 5.1 Duration bands

Duration bands are diagnostic starting points, not sufficient evidence by themselves.

| Candidate period | Typical duration | Classification requirement |
| --- | ---: | --- |
| Standalone quarter | Approximately 12–14 weeks | Must align with issuer fiscal-quarter boundaries. |
| Six-month YTD | Approximately 25–28 weeks | Must begin at fiscal-year start and end at Q2. |
| Nine-month YTD | Approximately 38–41 weeks | Must begin at fiscal-year start and end at Q3. |
| Full fiscal year | Approximately 51–53 weeks | Must cover the issuer fiscal year. |
| Stub/transition | Outside expected structure | Must be explicitly labeled and separately handled. |

Exact day thresholds are not finalized until test-company validation. Period start/end dates and fiscal-calendar boundaries take precedence over approximate duration.

### 5.2 Period identity decision order

1. Establish issuer fiscal-year calendar applicable to the filing.
2. Use period start/end dates to determine fiscal boundaries.
3. Use filing fiscal-year and fiscal-period tags as supporting evidence.
4. Use statement presentation and XBRL context.
5. Use SEC frame only as secondary evidence.
6. If evidence conflicts materially, assign `REVIEW_REQUIRED` rather than guessing.

## 6. Compatibility tests

Two observations may be combined only when every critical compatibility test passes.

| Test | Required result | Failure disposition |
| --- | --- | --- |
| Issuer | Same canonical issuer | Reject |
| Fiscal year | Same issuer fiscal year for subtraction | Reject |
| Canonical concept | Same approved concept definition | Reject or manual mapping review |
| Period type | Both duration for flow subtraction/summing | Reject |
| Currency/unit | Identical or validly converted | Reject until normalized |
| Consolidation scope | Same scope | Reject |
| Dimensions | Same dimensional context | Reject unless approved aggregation exists |
| Continuing operations | Compatible basis | Reject or review |
| Fiscal calendar | Same calendar version | Reject or transition handling |
| Vintage basis | Same as-filed/restated basis | Align vintages or reject |
| Accounting presentation | No unresolved taxonomy/scope change | Review |

Noncritical presentation-label differences do not cause failure when the canonical mapping and underlying context are identical.

## 7. Source selection and duplicate resolution

### 7.1 Candidate ranking

For an intended canonical period, rank candidate facts by:

1. Correct issuer, accession, concept, period dates, unit, dimensions, and consolidated scope.
2. Explicit direct standalone fact with the intended duration.
3. Compatible cumulative fact suitable for deterministic reconstruction.
4. Approved filed-table extraction when XBRL is absent or demonstrably incorrect.
5. Structured vendor observation only as a cross-check or temporary review aid.

### 7.2 Duplicate-fact rules

- Identical duplicate contexts collapse to one logical fact while retaining all source references.
- When values differ within the same accession and context, prefer the primary financial-statement fact over a note/segment fact unless the mapping explicitly requires the latter.
- Dimensionless consolidated facts take precedence for consolidated metrics; segment facts must not be accidentally aggregated when eliminations are unknown.
- A more precise `decimals` attribute does not automatically override a better statement context.
- Material unresolved duplicates receive `CONFLICT_UNRESOLVED`.

## 8. Standalone-quarter construction

### 8.1 Q1

For flow concept `X`:

`Q1_X = Direct_Three_Month_Q1_X`

Q1 ordinarily requires no subtraction because the first-quarter YTD period is also the standalone first quarter.

If multiple Q1 facts exist, use the candidate-ranking rules. If Q1 duration reflects a transition period rather than a normal quarter, classify it as `STUB` or `TRANSITION`.

### 8.2 Q2

Preferred order:

1. Use a validated direct standalone Q2 fact when clearly filed.
2. Otherwise derive:

`Q2_X = Six_Month_YTD_X - Q1_YTD_X`

The Q1 parent must cover the same fiscal-year start and use the same definition as the six-month parent.

### 8.3 Q3

Preferred order:

1. Use a validated direct standalone Q3 fact when clearly filed.
2. Otherwise derive:

`Q3_X = Nine_Month_YTD_X - Six_Month_YTD_X`

Both parents must belong to the same fiscal year and compatible vintage basis.

### 8.4 Q4

Q4 is normally derived because issuers report a full-year 10-K rather than a standalone Q4 filing:

`Q4_X = Annual_FY_X - Nine_Month_YTD_X`

Q4 becomes available only when the annual filing is model-eligible. Fiscal year-end or earnings-release dates do not make the filed Q4 derivation available in v1.

### 8.5 Direct-versus-derived validation

When both a direct standalone value and a cumulative-derived value exist:

1. Construct both independently.
2. Calculate absolute and relative difference.
3. If within approved tolerance, select the direct value and record the derived reconciliation.
4. If outside tolerance, do not automatically select either. Investigate duration, dimensions, restatement, discontinued operations, taxonomy, rounding, or presentation changes.
5. Until resolved, assign `REVIEW_REQUIRED` to the concept-period.

## 9. Worked example: cumulative 10-Q reconstruction

Assume Company A reports revenue in USD millions:

| Filing | Reported period | Reported revenue |
| --- | --- | ---: |
| Q1 10-Q | Three months YTD | 100 |
| Q2 10-Q | Six months YTD | 230 |
| Q3 10-Q | Nine months YTD | 375 |
| 10-K | Full fiscal year | 530 |

Constructed standalone quarters:

| Quarter | Formula | Result | Origin |
| --- | --- | ---: | --- |
| Q1 | 100 | 100 | Direct |
| Q2 | 230 − 100 | 130 | Derived |
| Q3 | 375 − 230 | 145 | Derived |
| Q4 | 530 − 375 | 155 | Derived |

Reconciliation:

`100 + 130 + 145 + 155 = 530`

All three derived quarters retain parent fact IDs, accessions, filing availability dates, transformation rule version, and reconciliation result.

## 10. Worked example: direct Q2 conflicts with reconstruction

Assume a Q2 filing contains:

- Direct three-month Q2 revenue: 132.
- Six-month YTD revenue: 230.
- Q1 revenue from the compatible Q1 filing: 100.

Derived Q2 is `230 − 100 = 130`, which differs from direct Q2 by 2.

Required response:

1. Do not average 130 and 132.
2. Check whether the direct fact is segment-specific, recast, rounded, in another unit, or uses a different continuing-operations basis.
3. Check whether the Q1 comparable was restated within the Q2 filing.
4. If the Q2 filing provides a recast six-month composition of Q1 = 98 and Q2 = 132, use the internally consistent same-vintage facts.
5. Preserve the original Q1 as-filed value of 100 for model dates before the Q2 filing.

This example illustrates why vintage alignment is required before subtraction.

## 11. Q4 derivation rules

### 11.1 Required conditions

Q4 derivation is allowed only when:

- Annual and nine-month facts belong to the same issuer and fiscal year.
- Both use compatible canonical concepts and accounting scope.
- Currency, units, dimensions, and consolidation scope match.
- The nine-month value is aligned to the annual filing's restatement basis when constructing a latest-restated Q4.
- No fiscal-year transition prevents a normal fourth-quarter interpretation.

### 11.2 As-filed Q4 views

Two valid analytical views may exist after the 10-K is filed:

- **Contemporaneous-component Q4:** annual value from the 10-K minus the nine-month value known from the Q3 10-Q, when definitions remain compatible.
- **Same-vintage restated Q4:** annual value minus a recast nine-month comparative presented in or supported by the annual filing.

The production view must be explicitly labeled. Backtesting must never make the recast value available before the annual filing.

### 11.3 Negative derived Q4

A negative derived value is not automatically invalid. It may be economically real for cash flow, provisions, losses, reversals, or working-capital movements.

Flag for review when:

- the sign is implausible for the concept;
- magnitude is inconsistent with disclosures;
- annual and nine-month definitions differ; or
- the result exceeds an approved anomaly threshold.

## 12. TTM construction

### 12.1 Flow concepts

For four consecutive validated standalone quarters:

`TTM_X(t) = Q_X(t) + Q_X(t-1) + Q_X(t-2) + Q_X(t-3)`

### 12.2 TTM prerequisites

- Exactly four consecutive issuer fiscal quarters.
- No duplicated or skipped fiscal-quarter identity.
- Compatible canonical concept and accounting scope.
- Compatible currency; conversions, if later permitted, must use an approved rule.
- Every quarter available by the evaluation date.
- No unresolved transition period.

### 12.3 TTM update identity

As a cross-check:

`TTM_X(t) = TTM_X(t-1) + Q_X(t) - Q_X(t-4)`

The direct four-quarter sum and roll-forward identity should agree within numeric tolerance.

### 12.4 TTM YoY comparison

Primary TTM change:

`TTM_YoY_Growth_X(t) = TTM_X(t) / TTM_X(t-4) - 1`

When the denominator is zero, negative, or economically unsuitable for a growth rate, use an approved alternative such as absolute change, margin change, or sector-specific status. Do not manufacture a percentage growth rate.

## 13. Worked example: TTM construction and update

Assume validated standalone revenue:

| Fiscal quarter | Revenue |
| --- | ---: |
| FY2025 Q2 | 90 |
| FY2025 Q3 | 95 |
| FY2025 Q4 | 100 |
| FY2026 Q1 | 105 |
| FY2026 Q2 | 112 |

At FY2026 Q1:

`TTM = 90 + 95 + 100 + 105 = 390`

At FY2026 Q2:

`TTM = 95 + 100 + 105 + 112 = 412`

Roll-forward check:

`390 + 112 − 90 = 412`

The sequential TTM increase is a diagnostic. The primary growth comparison uses the TTM ending FY2026 Q2 against the TTM ending FY2025 Q2.

## 14. Instant facts and TTM ratios

Instant balance-sheet facts are not summed. A TTM ratio must specify its denominator rule.

Examples:

- TTM operating margin = TTM operating income ÷ TTM revenue.
- TTM FCF margin = TTM FCF ÷ TTM revenue.
- TTM return on average assets = TTM numerator ÷ approved average of compatible beginning/end or quarterly asset balances.
- TTM ROIC = TTM NOPAT ÷ approved average invested capital.

The averaging convention for each ratio belongs in the metric specification. If required instant observations are unavailable or incompatible, the ratio is missing rather than calculated from an arbitrary ending balance without disclosure.

## 15. Ratios, margins, EPS, and per-share data

### 15.1 Recompute rather than subtract

- Do not derive Q2 operating margin by subtracting Q1 margin from six-month margin.
- Do not derive Q4 EPS by subtracting nine-month EPS from annual EPS when share counts or rounding differ.
- Do not sum quarterly ROIC values to create TTM ROIC.

Use underlying compatible numerators and denominators.

### 15.2 Per-share measures

Per-share measures may be reported for diagnostics, but primary Fast APAM accounting construction should use aggregate earnings/cash-flow values plus appropriately constructed share data when per-share analysis is required.

## 16. Free-cash-flow construction

For each validated standalone quarter:

`FCF_Q = CFO_Q - Capex_Q`

Then:

`FCF_TTM = Σ FCF_Q over four consecutive quarters`

Equivalent cross-check:

`FCF_TTM = CFO_TTM - Capex_TTM`

Capital-expenditure mappings must be consistent across quarters. If an issuer changes presentation or combines purchases with disposals, the affected periods require mapping review.

Negative FCF is valid data and must not be converted to missing. Percentage growth across zero or negative bases requires special metric treatment.

## 17. Restatements, amendments, and comparative recasts

### 17.1 Storage rule

Never overwrite a prior filing vintage. Link the later observation through `supersedes_vintage_id` or equivalent lineage.

### 17.2 Availability rule

- Original filing facts become available under the original filing timestamp.
- Amended facts become available under the amendment timestamp.
- Comparatives recast in a later filing become available only when that later filing becomes eligible.

### 17.3 Construction by view

| View | Permitted parents |
| --- | --- |
| `AS_FILED` | Facts available as of the historical evaluation date. |
| `LATEST_RESTATED` | Latest compatible facts known at the current evaluation date. |

Do not combine an old cumulative parent with a later restated parent unless the construction is explicitly labeled and tested for compatibility.

### 17.4 Worked restatement example

Timeline:

- May 5: Q1 revenue filed as 100.
- August 5: Q2 filing recasts Q1 revenue to 98 and reports six-month revenue of 230.
- August 6: Q2 filing becomes model-eligible under the one-trading-day rule.

Before August 6:

- Q1 as-filed = 100.
- Q2 unavailable.

On or after August 6:

- Latest-restated Q1 = 98.
- Q2 standalone on the Q2 vintage = `230 − 98 = 132`.
- Original Q1 = 100 remains preserved in historical storage.

The model must not revise May or June backtest states to 98.

## 18. Filing-date and look-ahead rules

### 18.1 Eligibility

A filing is eligible on the first approved trading date after one full trading day has elapsed following SEC acceptance.

### 18.2 Evaluation-date logic

For evaluation date `D`:

1. Select only filings with `model_available_date <= D`.
2. Select point-in-time universe membership effective on `D`.
3. Select sector classification known/effective on `D`.
4. Construct periods only from eligible parent facts.
5. Store the exact vintage set used in the model snapshot.

### 18.3 Prohibitions

- Do not use period end as availability.
- Do not backfill later restatements.
- Do not use vendor “latest” history without filing vintages.
- Do not make derived Q4 available before the 10-K.
- Do not use an earnings release in v1 to accelerate a filed-data score.

## 19. Fiscal-calendar alignment

### 19.1 Company comparisons

Quarterly YoY comparisons match:

- FY2026 Q1 with FY2025 Q1.
- FY2026 Q2 with FY2025 Q2.
- FY2026 Q3 with FY2025 Q3.
- FY2026 Q4 with FY2025 Q4.

Calendar month or calendar-quarter labels do not override fiscal identity.

### 19.2 Cross-sectional model dates

On a shared model date, different companies may have different latest fiscal quarters. Cross-sectional outputs must disclose:

- latest fiscal period;
- period end;
- filing/model-available date; and
- data age.

Staleness should affect DataConfidence and may affect score eligibility after thresholds are approved.

### 19.3 Comparable-quarter failure

If a fiscal-year-end change means FY2026 Q1 does not represent a comparable duration or season to FY2025 Q1, assign `PERIOD_INCOMPARABLE` until a defensible comparison window is available.

## 20. 52/53-week fiscal years

### 20.1 Primary rule

Use reported fiscal values and flag the extra week. Do not silently divide or rescale the official value.

### 20.2 Comparison treatment

- Same-quarter YoY remains primary when fiscal identities align.
- Add `extra_week_current`, `extra_week_comparable`, and `duration_difference_days` fields.
- Calculate a duration-normalized diagnostic only where economically sensible.
- Reduce confidence or flag manual review when the extra week materially changes interpretation.

### 20.3 Diagnostic normalization

For a flow suitable for simple time normalization:

`Daily_Rate = Reported_Flow / Duration_Days`

`Normalized_Flow = Daily_Rate × Reference_Duration_Days`

This is diagnostic only. It is not appropriate for every concept because sales and cash flows are not uniformly distributed through time.

### 20.4 Worked example

Current Q4 revenue is 140 over 14 weeks; prior Q4 revenue is 126 over 13 weeks.

- Reported YoY growth = `140 / 126 − 1 = 11.1%`.
- Weekly-rate diagnostic: current 10.0 versus prior 9.69, approximately 3.2% growth.

Fast APAM retains 11.1% as the reported comparison, displays the extra-week diagnostic, and prevents the apparent acceleration from being interpreted without the flag.

## 21. Fiscal-year changes and transition periods

### 21.1 Identification

Flag a transition when:

- fiscal-year-end changes;
- a filing covers an unusual short or long period;
- quarterly boundaries no longer map to prior-year fiscal quarters; or
- merger/reorganization accounting creates a new reporting entity or predecessor/successor basis.

### 21.2 Treatment

- Do not force the transition period into Q1–Q4.
- Label it `STUB` or `TRANSITION` with exact dates and duration.
- Do not use it in a standard four-quarter TTM until an approved bridge exists.
- Resume standard comparisons only when four consecutive comparable quarters are available or a manually approved mapping is documented.

### 21.3 Optional bridge

Pro forma or recast comparatives may support a future manual bridge only when filed, definitionally compatible, point-in-time available, and separately labeled. They do not overwrite reported history.

## 22. Acquisitions, divestitures, and discontinued operations

Period construction and economic interpretation are separate.

- Valid reported quarters should still be constructed when accounting scope is consistent.
- Material acquisitions/divestitures receive confounder flags.
- Restated discontinued-operation comparatives use their actual availability vintage.
- If numerator scope changes but prior periods are not recast, YoY comparison may be `PERIOD_INCOMPARABLE` or confidence-reduced.
- Do not “organically adjust” reported values without an approved, fully sourced methodology.

## 23. Foreign currency and reporting-currency changes

- Construct quarters in the filing's reported currency.
- Do not subtract cumulative parents expressed in different currencies without an approved conversion.
- A reporting-currency change requires a comparable recast or a transition flag.
- Cross-sectional score normalization should normally operate on ratios and growth measures after valid company-level construction, not on mixed raw currencies.

Constant-currency growth is a separate disclosure-derived metric and must not replace reported growth silently.

## 24. Sector-specific period considerations

### 24.1 Operating companies

Revenue, operating income/EBIT, CFO, capex, and FCF generally follow standard flow construction. Employee counts are as-of disclosures and are not quarter flows.

### 24.2 Banks and other Financials

- Net interest income, noninterest income/expense, provisions, premiums, claims, and compensation expenses are flows and may be reconstructed when filing presentations are compatible.
- Loans, deposits, assets, capital, reserves, AUM, and client assets are instant/as-of values; do not sum them.
- Average-balance fields may already represent quarterly or YTD averages. Do not subtract average balances to create standalone averages.
- Ratios such as efficiency, net interest margin, combined ratio, and capital ratios must be recomputed or used as period-specific reported diagnostics, not subtracted.

### 24.3 Equity REITs

- Revenue, property expenses, NOI inputs, FFO reconciliation flows, and recurring capex may be reconstructed when definitions match.
- Occupancy is an instant/as-of metric.
- Same-store pools can change; YoY comparisons require pool-definition flags.
- Company-defined normalized FFO/AFFO must retain definition and reconciliation lineage; do not combine quarters with materially inconsistent definitions.

## 25. Missing and failure outcomes

| Failure | Required code | Result |
| --- | --- | --- |
| Parent fact absent | `DERIVATION_FAILED` | No derived quarter |
| Parent filing not yet available | `NOT_YET_AVAILABLE` | No value on model date |
| Same concept not mapped consistently | `CONCEPT_UNMAPPED` | Mapping review |
| Period/duration mismatch | `PERIOD_INCOMPARABLE` | No comparison |
| Unit/currency mismatch | `QUALITY_REJECTED` or review | No construction |
| Dimension/scope mismatch | `CONFLICT_UNRESOLVED` | Manual review |
| Insufficient four-quarter history | `INSUFFICIENT_HISTORY` | No TTM |
| Fiscal transition | `PERIOD_INCOMPARABLE` | Transition handling |
| Material direct/derived disagreement | `REVIEW_REQUIRED` | Factor ineligible pending resolution |

No failure outcome may be converted to zero.

## 26. Construction output schema

Every constructed period must include:

| Field | Definition |
| --- | --- |
| `constructed_observation_id` | Stable unique identifier. |
| `issuer_id` | Canonical issuer. |
| `canonical_concept` | Controlled metric concept. |
| `fiscal_year` | Issuer fiscal year. |
| `fiscal_quarter` | Q1–Q4 or transition label. |
| `period_start` / `period_end` | Exact dates. |
| `duration_days` | Period duration. |
| `period_basis` | Standalone, TTM, annual, instant, or as-of. |
| `value` | Constructed or selected value. |
| `unit` / `currency` | Standardized unit. |
| `value_origin` | Direct, derived, mapped, or manual-reviewed. |
| `transformation_rule_id` | Versioned construction rule. |
| `parent_observation_ids` | Complete parent list. |
| `parent_accession_numbers` | Complete filing list. |
| `view_type` | As-filed or latest-restated. |
| `model_available_date` | First eligible date for the finished observation. |
| `reconciliation_difference` | Difference from alternative construction when available. |
| `quality_status` | PASS, PARTIAL, REVIEW_REQUIRED, etc. |
| `quality_flags` | Extra week, stale, transition, restated, acquisition, and other flags. |

For a derived observation, `model_available_date` is the latest availability date among all required parents.

## 27. Deterministic construction decision table

| Intended output | Required inputs | Construction | Valid result | Invalid result |
| --- | --- | --- | --- | --- |
| Q1 flow | Valid Q1 duration fact | Select direct | `PASS` | Missing/review code |
| Q2 flow | Direct Q2 or compatible 6M and Q1 | Direct; otherwise 6M − Q1 | `PASS`/`DERIVED` | `DERIVATION_FAILED` or review |
| Q3 flow | Direct Q3 or compatible 9M and 6M | Direct; otherwise 9M − 6M | `PASS`/`DERIVED` | `DERIVATION_FAILED` or review |
| Q4 flow | Compatible FY and 9M | FY − 9M | `PASS`/`DERIVED` | `PERIOD_INCOMPARABLE` or review |
| TTM flow | Four consecutive standalone quarters | Sum four quarters | `PASS` | `INSUFFICIENT_HISTORY` |
| TTM margin | Compatible TTM numerator/denominator | Recompute ratio | `PASS` | Missing/invalid denominator |
| Instant comparison | Compatible period-end instants | Compare levels/changes | `PASS` | Incomparable dates/scope |

## 28. Test-fixture requirements

Before implementation, create hand-verified fixtures covering at least:

1. Clean direct quarterly facts.
2. Cumulative-only Q2 and Q3 reconstruction.
3. Q4 annual-minus-nine-month derivation.
4. Direct-versus-derived conflict.
5. Q1 comparative recast inside a later filing.
6. 10-Q/A or 10-K/A amendment.
7. Later restatement that must not leak backward.
8. 52/53-week year.
9. Fiscal-year-end transition and stub period.
10. Acquisition/divestiture or discontinued-operation scope change.
11. Bank average-balance versus instant-balance handling.
12. Equity REIT same-store and FFO-definition change.
13. Missing capex or employee data.
14. Negative CFO/FCF and zero/negative comparison base.

Each fixture must contain source accessions, exact parent facts, expected result, model-available date, expected status/flags, and reviewer sign-off.

## 29. Acceptance tests

The period engine is acceptable only when:

- Q1 + Q2 reconciles to six-month YTD within approved tolerance.
- Q1 + Q2 + Q3 reconciles to nine-month YTD.
- Q1 + Q2 + Q3 + Q4 reconciles to annual FY.
- Four-quarter direct sum equals the TTM roll-forward identity.
- No instant, ratio, margin, or per-share fact is improperly subtracted or summed.
- Every derived observation reproduces from stored parents.
- Historical evaluation dates contain no later filings or restatements.
- Fiscal transitions and incompatible periods fail visibly.
- Direct/derived disagreements route deterministically to review.
- The same inputs and rule version always produce the same output.

Exact numeric tolerances remain `RESEARCH_REQUIRED` until the test-company set is audited.

## 30. Decisions still required

| Decision | Recommended approach | Status |
| --- | --- | --- |
| Numeric reconciliation tolerance | Set absolute and relative tolerances by concept/unit after fixture review. | Research required |
| Maximum acceptable quarter duration variance | Calibrate using issuer fiscal calendars. | Research required |
| Data-staleness limit | Measure distribution before setting scoreability cutoff. | Research required |
| Same-vintage versus contemporaneous Q4 production view | Prefer same-vintage for current diagnostics and strict as-filed for backtests. | Proposed |
| Direct-versus-derived precedence threshold | Direct preferred only after reconciliation. | Proposed |
| Transition-period bridge policy | Exclude by default; allow manual approved bridge later. | Proposed |
| Currency-conversion policy | Keep company construction in reported currency in v1. | Proposed |

## 31. Recommended next step

Create `Test_Company_Register.md` and select the first hand-audited fixture set before any period-engine code is written.

The test set should prioritize difficult accounting cases rather than only clean technology issuers. Once expected standalone-quarter and TTM values are independently calculated and approved, implementation can begin against those fixtures.

## 32. Revision history

| Version | Date | Change | Author |
| --- | --- | --- | --- |
| 0.1 | 2026-09-19 | Created the initial deterministic period-construction specification and worked examples. | Agora Lycos / Douglas Salone |


# Fast APAM Scoring and Status Specification

**Version:** 0.1  
**Status:** Proposed research specification; requires calibration and approval before implementation  
**Companion model:** Core APAM Model  

## 1. Purpose

Fast APAM is a separate quarterly and trailing-twelve-month companion to Core APAM. Its purpose is to detect recent operating acceleration, improvement, deceleration, or deterioration before those changes are fully visible in annual Core APAM results.

Fast APAM does not replace or rewrite Core APAM. Core APAM remains the measure of durable, multi-year business quality. Fast APAM measures recent direction and confirmation using information that was publicly available as of each model date.

The governing design conclusion is:

> Fast APAM should detect recent acceleration or deterioration using year-over-year standalone-quarter and trailing-twelve-month comparisons. Raw sequential quarter-over-quarter changes are diagnostic only and are not primary scoring signals because seasonality can make them misleading.

Acceleration generally contributes to the score and status assessment. It is not an automatic elimination gate.

## 2. Scope

This specification defines:

- score architecture and factor weights;
- metric eligibility and transformation rules;
- sector-specific scoring modules;
- missing-data and partial-scoring treatment;
- `FastScore`, `FastStatus`, `DataConfidence`, and `DataStatus`;
- hard gates and review flags;
- interaction with Core APAM;
- point-in-time and audit requirements;
- calibration and validation requirements; and
- the recommended development sequence.

This specification does not:

- implement code;
- finalize empirical cutoffs before calibration;
- create a single blended Core/Fast score;
- authorize automated investment decisions;
- treat raw sequential quarter-over-quarter movements as primary evidence; or
- force operating-company metrics onto Financials or REITs.

## 3. Governing Principles

1. **Core measures durability; Fast measures recent direction.** The two models remain separately visible.
2. **Comparable periods come first.** Standalone-quarter YoY and TTM YoY comparisons are primary.
3. **Acceleration is graded evidence.** It contributes to the result but normally does not determine eligibility.
4. **Data quality is separate from economic performance.** A poor operating result can have high data confidence; a strong-looking result can have low data confidence.
5. **Missing is not zero.** Missing metrics are excluded, flagged, and handled through controlled reweighting or an unscored outcome.
6. **Sector economics control metric selection.** Operating companies, Financials, and REITs require different modules.
7. **Point-in-time integrity is mandatory.** No value may be used before its filing or public availability date.
8. **Every score must be reproducible.** Source facts, period construction, transformations, weights, flags, and status logic must be retained.
9. **Accounting identities are gates; economic weakness is not.** Failed period construction may stop scoring. Deteriorating economics should be measured, not hidden.

## 4. Required Output Objects

Every evaluated issuer/model-date combination produces four separate outputs:

| Output | Range or values | Meaning |
|---|---|---|
| `FastScore` | 0–100 or null | Strength of recent operating and sector-relevant evidence |
| `FastStatus` | Controlled vocabulary | Directional interpretation of recent evidence |
| `DataConfidence` | 0–100 | Reliability, completeness, comparability, and timeliness of the inputs |
| `DataStatus` | Controlled vocabulary | Whether the observation is usable, partial, stale, or blocked |

The model must not silently multiply `FastScore` by `DataConfidence`. Both remain separately visible. A confidence-adjusted value may be studied during validation, but it is not an approved production output.

### 4.1 FastStatus values

- `ACCELERATING`
- `IMPROVING`
- `STABLE`
- `DECELERATING`
- `DETERIORATING`
- `MIXED`
- `UNSCORED`

### 4.2 DataStatus values

- `PASS`
- `PARTIAL`
- `STALE`
- `REVIEW_REQUIRED`
- `INSUFFICIENT_HISTORY`
- `SECTOR_MODULE_UNAVAILABLE`
- `PERIOD_INCOMPARABLE`

## 5. Evaluation Unit and Time Basis

The evaluation unit is one issuer, one fiscal reporting date, one model date, and one applicable sector module.

The model date controls what the model was allowed to know. The fiscal period end identifies the economic period, but it is never treated as the public availability date.

For each result, retain:

- issuer and security identifiers;
- sector and submodule;
- fiscal year and fiscal quarter;
- period start and end dates;
- filing form, accession number, and filing date;
- model date and extraction timestamp;
- source taxonomy/concept and units;
- reported or derived status;
- restatement view;
- score specification version; and
- all applicable quality and review flags.

## 6. Eligibility and Hard Gates

Hard gates are limited to conditions that prevent a defensible point-in-time comparison. They are not used to eliminate companies merely because their recent performance is weak.

### 6.1 Permitted hard gates

A result must be `UNSCORED` when any critical condition below remains unresolved:

- the required filing was not publicly available by the model date;
- a standalone quarter or TTM period fails the required accounting identity checks;
- periods are materially incomparable because of a fiscal-calendar transition, stub period, or unresolved extra-week issue;
- units, dimensions, or consolidation scopes are invalid or irreconcilable;
- the sector module is unavailable;
- history is critically insufficient for the required comparison; or
- conflicting source facts cannot be resolved without judgment not supported by the documented rules.

### 6.2 Conditions that are not automatic gates

The following normally affect score, status, or confidence rather than eligibility:

- negative growth;
- falling margins;
- weak free cash flow;
- a negative acceleration signal;
- disagreement among operating, cash-flow, and productivity measures;
- high capital spending;
- an unfavorable but valid one-time item;
- a carried employee value; or
- a derived Q2, Q3, or Q4 that passes reconstruction tests.

## 7. Period Construction Dependency

Scoring begins only after the Period Construction Rules have produced valid comparable observations.

### 7.1 Standalone-quarter construction

- Q1 generally uses the reported three-month value.
- Q2 equals reported six-month cumulative value minus Q1.
- Q3 equals reported nine-month cumulative value minus reported six-month cumulative value.
- Q4 equals the annual total minus the nine-month cumulative value.
- TTM equals the sum of four valid standalone quarters.

Ratios and margins are recomputed from their components. Instant balance-sheet values are not summed or subtracted as if they were duration facts.

### 7.2 Comparison hierarchy

Primary comparisons are:

1. latest standalone fiscal quarter versus the comparable fiscal quarter one year earlier;
2. current TTM versus the immediately preceding comparable TTM one year earlier; and
3. change in those YoY rates through time, used as acceleration evidence.

Raw Q2-versus-Q1 or Q4-versus-Q3 changes may be displayed as diagnostics but receive zero primary weight.

### 7.3 Fiscal-calendar safeguards

Comparable periods must align by issuer fiscal quarter, not calendar quarter label alone. A 52/53-week year, changed year-end, acquisition stub, or transition report must be flagged. When the extra week materially affects a comparison and cannot be normalized consistently, the affected metric is excluded or the period is marked `PERIOD_INCOMPARABLE`.

## 8. Scoring Pipeline

The approved conceptual pipeline is:

1. establish filing and point-in-time eligibility;
2. construct valid standalone quarters and TTM periods;
3. select the applicable sector module;
4. calculate primary YoY and TTM measures;
5. calculate acceleration, persistence, and breadth measures;
6. identify base effects, one-time items, and comparability risks;
7. directionally align and normalize metric signals;
8. aggregate metrics into factor groups;
9. apply controlled missing-data rules;
10. calculate `FastScore` and `DataConfidence` separately;
11. assign `FastStatus` and `DataStatus` using their respective rules; and
12. retain a complete audit record.

No scoring stage may reach backward from a later restatement or filing if that information was unavailable on the model date.

## 9. Signal Definitions

### 9.1 Standalone-quarter YoY signal

For a valid duration metric with a suitable base:

`Quarter_YoY = Current_Standalone_Quarter / Prior_Year_Comparable_Quarter - 1`

For margins, yields, occupancy, leverage ratios, and similar rate measures, use percentage-point or basis-point change rather than percentage growth unless a sector rule explicitly states otherwise.

### 9.2 TTM YoY signal

For a valid duration metric with a suitable base:

`TTM_YoY = Current_TTM / Prior_Year_TTM - 1`

TTM evidence is the principal stabilizer because it reduces seasonal noise and dependence on one quarter.

### 9.3 Acceleration signal

Acceleration is the change in a comparable YoY rate, not raw sequential growth:

`Quarter_Acceleration = Current_Quarter_YoY - Previous_Fiscal_Quarter_YoY`

`TTM_Acceleration = Current_TTM_YoY - Previous_Fiscal_Quarter_TTM_YoY`

For margins and other level metrics, acceleration is the change in the YoY level improvement. For example, if operating margin improved 100 basis points YoY in the current quarter after improving 30 basis points YoY in the preceding quarter, the margin-acceleration signal is positive 70 basis points.

### 9.4 Persistence

Persistence measures whether directionally aligned evidence has remained positive, neutral, or negative across recent comparable observations. The initial design should use up to four quarterly YoY observations when available, while preventing older observations from overwhelming the latest quarter and TTM.

### 9.5 Breadth

Breadth is the share of eligible, independent metric families that support the same direction. Multiple accounting expressions of the same economic fact must not be counted as independent confirmation.

### 9.6 Base-effect protection

Percentage growth is unsuitable when the comparison base is near zero, changes sign, or is economically distorted. In those cases, the module must use one or more of:

- absolute level change;
- margin or spread change;
- a scaled change using a stable denominator;
- sector-relative ranks based on an appropriate alternate metric; or
- exclusion with a `BASE_EFFECT` flag.

The transformation used must be stored in the audit output.

## 10. Directional Alignment and Normalization

Every metric must be converted so that a higher normalized value consistently represents stronger recent evidence.

Examples:

- revenue growth: higher is generally better;
- margin change: expansion is generally better;
- leverage growth: lower may be better, subject to sector context;
- credit-loss deterioration: lower is better;
- occupancy change: higher is better; and
- interest-burden growth: lower is better.

### 10.1 Recommended research normalization

The initial research implementation should compare each valid signal with an appropriate sector or industry peer group and convert it to a bounded 0–100 score. Extreme observations should be winsorized or robustly clipped before ranking.

Peer construction, winsorization limits, minimum peer counts, and fallback behavior require empirical calibration. Until approved, they must be labeled `PROVISIONAL` in fixtures and validation output.

### 10.2 Own-history context

An issuer's own recent history may be used as secondary context, especially for acceleration and persistence. It must not replace cross-sectional sector comparability or permit an economically weak company to receive a high score solely because it became less weak.

### 10.3 No artificial precision

Source precision and materiality must be respected. Small differences caused by rounding or quarter reconstruction should not create false status changes. Tolerance bands will be set during calibration and recorded by metric family.

## 11. Factor Architecture and Initial Weights

The charter's initial research architecture is retained:

| Factor group | Initial weight | Role |
|---|---:|---|
| TTM productivity and operating improvement | 35% | Stable recent operating evidence |
| Latest comparable-quarter YoY improvement | 25% | Most recent comparable-quarter evidence |
| Margin and capital or sector-quality confirmation | 20% | Confirms quality of growth and sector economics |
| Acceleration and persistence | 15% | Measures strengthening, slowing, and durability of recent direction |
| Breadth and consistency | 5% | Rewards independent confirmation and penalizes conflict |
| **Total** | **100%** | |

These are research weights, not final production weights. Any change requires a dated Decision Register entry, validation evidence, and a specification version update.

### 11.1 Weighting constraints

- Acceleration remains a minority contributor and is not an automatic gate.
- TTM carries more weight than the latest standalone quarter.
- Raw sequential QoQ change has zero primary weight.
- No single metric should dominate a factor merely because related metrics are missing.
- Economically overlapping metrics must be grouped to prevent double counting.
- Sector modules may change the metrics inside a factor group but should preserve the factor group's economic purpose.

### 11.2 Composite calculation

For each factor group:

`FactorScore = weighted mean of eligible, normalized metric signals`

Subject to the missing-data rules, the proposed composite is:

`FastScore = 0.35(TTM) + 0.25(Quarter) + 0.20(Quality) + 0.15(Acceleration) + 0.05(Breadth)`

The calculation must retain pre-rescaling weights, post-rescaling weights, coverage, and excluded metrics.

## 12. Operating Company Module

This module applies to non-financial, non-REIT operating companies when ordinary revenue, operating income, cash flow, and capital deployment concepts are economically meaningful.

### 12.1 Candidate metric families

| Factor | Candidate evidence |
|---|---|
| TTM operating improvement | Revenue, operating income or EBIT, CFO, FCF, revenue/employee when valid |
| Latest-quarter improvement | Revenue, operating income or EBIT, gross/operating profit, sector-relevant volume or unit measures |
| Quality confirmation | Gross margin, operating margin, FCF margin, capital efficiency, working-capital quality |
| Acceleration and persistence | Changes in quarter YoY and TTM YoY rates; recent directional run |
| Breadth | Agreement across growth, profitability, cash generation, and productivity families |

### 12.2 Free cash flow

FCF should generally be derived from CFO less capital expenditures under a documented definition. Capex intensity can make FCF diverge from accounting profit. That divergence is substantive evidence, not a data error.

If cash flow is highly seasonal, TTM receives priority. A single reconstructed quarter should not dominate the result.

### 12.3 Employee productivity

Employee-based metrics are scored only when the denominator is economically meaningful and sufficiently current. Acceptable classifications are:

- `OBSERVED_EMPLOYEE`: disclosed for the relevant period or a defensible nearby measurement date;
- `CARRIED_EMPLOYEE`: carried from a prior observation under an approved age limit, with confidence penalty; and
- `NO_EMPLOYEE_SIGNAL`: not scored when no defensible denominator exists.

Revenue growth minus employee growth may be used as a productivity confirmation signal. It must not be fabricated from an indefinite carry-forward.

## 13. Financials Modules

Financials require separate submodules. Generic revenue, EBIT, FCF, and industrial-company ROIC definitions must not be applied mechanically.

### 13.1 Banks

Candidate evidence includes:

- net interest income and net interest margin;
- fee-income trends;
- efficiency ratio and operating leverage;
- loan and deposit growth, with funding quality;
- credit-loss provisions, net charge-offs, and nonperforming assets;
- capital ratios and tangible book value per share; and
- return on tangible common equity or another approved return measure.

Positive growth that depends on weakening funding, credit, or capital quality should receive limited confirmation and may result in `MIXED`.

### 13.2 Insurers

Candidate evidence includes:

- premium growth;
- underwriting result;
- combined ratio or loss/expense ratios;
- reserve development;
- investment income;
- capital adequacy;
- book value or adjusted book value growth; and
- approved return measures.

Catastrophe losses, reserve releases, and accounting transitions require explicit flags. Comparisons must use consistent definitions.

### 13.3 Asset managers and brokers

Candidate evidence includes:

- assets under management or client assets;
- net flows;
- fee revenue and fee rate;
- compensation and operating efficiency;
- pre-tax or operating margin;
- transaction or market sensitivity;
- capital and liquidity; and
- approved return measures.

Market appreciation and organic flows should be separated when disclosed. Growth caused only by market levels should not be treated as equivalent to organic operating acceleration.

### 13.4 Financials development constraint

No Financials company may receive a production `FastScore` until its specific submodule, mappings, directionality, and validation fixtures are approved. Otherwise use `SECTOR_MODULE_UNAVAILABLE`.

## 14. REIT Module

Equity REITs require property-economics measures rather than industrial-company net income or generic FCF.

### 14.1 Candidate metric families

- same-store NOI growth;
- FFO and AFFO growth per share and in aggregate where appropriate;
- occupancy and leasing spreads;
- rent collections when material;
- G&A efficiency;
- recurring capital expenditures;
- interest burden and fixed-charge coverage;
- leverage and debt maturity risk; and
- property-sector-specific operating measures.

### 14.2 REIT safeguards

- Changes in FFO/AFFO definitions must be reconciled.
- Acquisition-driven growth must be distinguished from same-store improvement where possible.
- Nonrecurring gains and property-sale effects must not masquerade as operating acceleration.
- Share issuance and per-share dilution require explicit treatment.
- Mortgage REITs are excluded from the equity REIT module unless a separate approved module is created.

## 15. Missing Data and Controlled Reweighting

Missing values are never replaced with zero.

### 15.1 Metric-level handling

For every missing metric, store a reason such as:

- `NOT_YET_AVAILABLE`
- `CONCEPT_UNMAPPED`
- `DERIVATION_FAILED`
- `PERIOD_INCOMPARABLE`
- `QUALITY_REJECTED`
- `CONFLICT_UNRESOLVED`

### 15.2 Minimum scoreability

A score requires all of the following:

- a valid TTM anchor;
- at least one valid latest-quarter comparison;
- evidence from at least two independent economic families;
- an approved sector module; and
- no unresolved critical gate.

The exact minimum weighted coverage percentage is `RESEARCH_REQUIRED`. Until calibrated, fixtures must display both total original-weight coverage and factor coverage rather than silently declaring sparse observations complete.

### 15.3 Reweighting rule

Weights may be rescaled only within the same factor group and only among economically substitutable metrics. Missing an entire factor group must not cause unrelated groups to absorb all its weight.

For initial research fixtures:

- retain the original factor weight as the primary reference;
- report the unfilled weight explicitly;
- limit any within-group metric's weight expansion to a documented cap; and
- assign `PARTIAL` when scoreability is met but meaningful evidence is missing.

The numerical expansion cap and minimum coverage threshold require calibration before production.

## 16. DataConfidence

`DataConfidence` measures reliability, not performance. It begins from a fully supported observation and applies documented penalties or component scores for:

- source authority;
- filing-date eligibility;
- direct versus reconstructed values;
- accounting-identity validation;
- period comparability;
- concept and unit consistency;
- restatement state;
- timeliness or staleness;
- employee denominator age;
- metric and factor coverage; and
- unresolved review flags.

### 16.1 Confidence principles

- A correctly derived Q2, Q3, or Q4 is valid, but its derivation status remains visible.
- A carried employee count reduces confidence in employee-based signals, not unrelated metrics.
- Vendor-only data should receive lower confidence than filing-supported data unless independently validated.
- A restated value may improve the latest-known view but cannot be inserted into an earlier as-of run.
- Confidence penalties must be attributable; no opaque discretionary haircut is permitted.

### 16.2 Confidence bands

Numerical confidence bands should not be finalized until fixture review establishes realistic distributions. The eventual bands should distinguish at least:

- high-confidence, filing-supported results;
- usable results with limited reconstruction or missing evidence;
- results requiring analyst review; and
- results too weak for scoring.

## 17. DataStatus Assignment and Precedence

`DataStatus` is assigned independently of `FastStatus`. When multiple conditions apply, use the most restrictive applicable status under the following precedence:

1. `SECTOR_MODULE_UNAVAILABLE`
2. `PERIOD_INCOMPARABLE`
3. `INSUFFICIENT_HISTORY`
4. `REVIEW_REQUIRED`
5. `STALE`
6. `PARTIAL`
7. `PASS`

This ordering is a proposed operational rule and must be tested against fixtures. The underlying flags remain visible even when only one headline status is displayed.

### 17.1 Status definitions

| DataStatus | Definition |
|---|---|
| `PASS` | Required comparisons are available, valid, timely, and sufficiently complete |
| `PARTIAL` | Minimum scoreability is met, but noncritical metrics or factor evidence are missing |
| `STALE` | Data remain usable under an approved age rule but are not current enough for full confidence |
| `REVIEW_REQUIRED` | A noncritical ambiguity or unusual event requires analyst review |
| `INSUFFICIENT_HISTORY` | Required YoY, TTM, or acceleration history cannot be constructed |
| `SECTOR_MODULE_UNAVAILABLE` | No approved methodology exists for the issuer's business type |
| `PERIOD_INCOMPARABLE` | Fiscal periods cannot be compared defensibly under current rules |

Only `PASS`, and conditionally `PARTIAL` or `STALE`, may carry a non-null `FastScore`. Other statuses normally produce `FastStatus = UNSCORED`.

## 18. FastStatus Decision Framework

`FastStatus` is not a mechanical translation of `FastScore` bands. It combines:

- level of recent TTM and quarter YoY evidence;
- direction of acceleration;
- persistence;
- breadth and conflict;
- sector-quality confirmation; and
- sufficient data confidence.

This prevents a still-strong company whose growth rate is slowing from being mislabeled as economically weak, and prevents a weak company from being labeled strong merely because its rate became less negative.

### 18.1 Directional states

| FastStatus | Required interpretation |
|---|---|
| `ACCELERATING` | Recent evidence is positive and broadly strengthening; acceleration is confirmed across sufficient independent signals |
| `IMPROVING` | Recent evidence is positive or becoming meaningfully better, but acceleration confirmation is not broad or persistent enough for `ACCELERATING` |
| `STABLE` | Comparable evidence is broadly unchanged or balanced within calibrated neutral ranges |
| `DECELERATING` | The business may still show positive growth or acceptable levels, but comparable growth, margins, or sector-quality evidence is losing momentum |
| `DETERIORATING` | Recent levels and direction are materially negative across sufficient independent evidence |
| `MIXED` | Materially conflicting signals prevent one coherent directional conclusion |
| `UNSCORED` | Data or methodology do not support a valid conclusion |

### 18.2 Guardrails

- `ACCELERATING` requires positive level evidence plus positive acceleration; acceleration alone is insufficient.
- `DETERIORATING` requires more than one isolated weak metric unless that metric is an approved sector-critical measure.
- `DECELERATING` may coexist with an above-median `FastScore` when performance remains strong but momentum is slowing.
- `IMPROVING` may coexist with a below-median `FastScore` when the company is recovering from weak levels but has not yet reached strong absolute evidence.
- `MIXED` is appropriate when profit, cash flow, margin, credit, or sector-quality signals materially disagree.
- Low confidence cannot be converted into a directional economic judgment; it leads to `UNSCORED` or a review state.

### 18.3 Status thresholds

Exact score, acceleration, breadth, and persistence thresholds are `RESEARCH_REQUIRED`. They must be calibrated on historical, sector-balanced samples and locked before out-of-sample validation. Fixture work may use clearly labeled provisional thresholds but may not present them as approved production logic.

## 19. Mixed Evidence and Confounders

The model must preserve economically meaningful disagreement rather than averaging it away.

Potential confounders include:

- acquisitions or divestitures;
- major restructuring;
- accounting-standard changes;
- currency effects;
- unusual tax effects;
- commodity or market-price effects;
- catastrophe losses;
- reserve releases or charges;
- working-capital timing;
- unusually high capital expenditures;
- fiscal extra weeks;
- share issuance or repurchases; and
- management-defined metric changes.

Each confounder receives an attributable flag. It may affect a specific metric, factor, confidence score, or status. It should not trigger a blanket override without documented justification.

## 20. Restatements and Filing-Date Safeguards

The system must preserve two distinct views:

- **as-filed view:** what was publicly known on the historical model date; and
- **latest-restated view:** the most current reported presentation.

Historical backtests use only the as-filed view appropriate to each model date. Later amendments, recasts, and restatements must not leak backward.

When a restatement changes a previously scored period:

- preserve the original result and its source lineage;
- calculate the revised latest-restated result separately;
- identify the affected metrics and factors;
- record whether the change alters `FastScore`, `FastStatus`, or confidence; and
- never overwrite the point-in-time audit record.

## 21. Interaction with Core APAM

Core APAM remains the durable-quality anchor. Fast APAM is a separate recent-direction overlay.

| Core APAM condition | Fast APAM condition | Interpretation |
|---|---|---|
| Strong | `ACCELERATING` or `IMPROVING` | Durable quality with recent confirmation |
| Strong | `DECELERATING` or `DETERIORATING` | Quality remains, but recent thesis risk has increased |
| Weak or mixed | `ACCELERATING` or `IMPROVING` | Possible early inflection; requires confirmation rather than automatic promotion |
| Weak | `DECELERATING` or `DETERIORATING` | Low-priority or worsening profile |
| Any | `MIXED` | Conflicting recent evidence; inspect factors and flags |
| Any | `UNSCORED` | No Fast conclusion; Core result remains independently valid |

### 21.1 Prohibited interactions

- Fast APAM must not retroactively change Core APAM history.
- A high FastScore must not erase weak durable quality.
- A low FastScore must not automatically eliminate an otherwise qualified company.
- `UNSCORED` must not be treated as deterioration.
- Initial release must not collapse Core and Fast into one opaque number.

If a combined display is studied later, Core must remain the anchor and Fast may only act as a bounded overlay approved through the Decision Register.

## 22. Required Audit Output

Every result must retain enough information to reproduce the final outputs.

### 22.1 Headline fields

- issuer/security identifier;
- model date;
- fiscal quarter and period end;
- sector module and version;
- `FastScore`;
- `FastStatus`;
- `DataConfidence`;
- `DataStatus`;
- Core APAM reference, if displayed; and
- specification version.

### 22.2 Factor fields

For each factor group:

- factor score;
- original weight;
- applied weight;
- coverage percentage;
- contributing metrics;
- excluded metrics and reason codes; and
- factor-level flags.

### 22.3 Metric fields

For each metric:

- reported facts and source identifiers;
- standalone-quarter derivation;
- TTM construction;
- current and prior comparable values;
- YoY and acceleration calculations;
- transformation and directionality;
- normalized score;
- metric weight;
- source/derivation quality; and
- all flags.

### 22.4 Review fields

- analyst or process identifier;
- extraction timestamp;
- review disposition;
- override, if any;
- override reason and approving party; and
- unresolved differences.

Overrides must never replace the original calculated result in the audit trail.

## 23. Validation Plan

Validation occurs in stages.

### 23.1 Stage 1: Arithmetic and reconstruction

- confirm Q2, Q3, Q4, and TTM identities;
- test rounding tolerances and sign conventions;
- verify margins are recomputed rather than subtracted as cumulative ratios;
- test 52/53-week years and transition periods; and
- confirm restatement and filing-date isolation.

### 23.2 Stage 2: Metric and sector logic

- test directionality for every metric;
- verify base-effect handling;
- confirm overlapping metrics are not double counted;
- test sector-submodule selection; and
- ensure operating-company logic is not applied to Financials or REITs.

### 23.3 Stage 3: Score and status behavior

- test missing-data paths and reweighting caps;
- test that acceleration contributes without acting as a gate;
- confirm strong-but-slowing cases can be `DECELERATING` without an artificially collapsed score;
- confirm weak-but-recovering cases can be `IMPROVING` without being mistaken for durable quality;
- test `MIXED` cases; and
- verify `DataConfidence` remains independent of economic direction.

### 23.4 Stage 4: Historical calibration

Use a sector-balanced sample across expansions, recessions, rate cycles, commodity cycles, and company-specific disruptions. Calibrate:

- peer-group definitions;
- outlier handling;
- factor and metric weights;
- score and status thresholds;
- neutral and materiality bands;
- persistence windows;
- minimum coverage;
- confidence penalties; and
- staleness limits.

Thresholds must be locked before out-of-sample evaluation.

### 23.5 Stage 5: Out-of-sample and stability testing

- evaluate predictive and descriptive usefulness without tuning on the test set;
- measure status transition rates and false reversals;
- examine sector bias and market-cap bias;
- test sensitivity to one filing, one metric, and minor revisions;
- compare as-filed with latest-restated outcomes; and
- document failure modes.

### 23.6 Stage 6: Independent review

Independent review is a validation gate after the specification, fixtures, and review packet are stable. It is not a substitute for finishing the scoring design. The reviewer should receive controlled source materials, lock their extraction before comparison, and return a difference log and disposition.

## 24. Initial Fixture Expectations

The first operating-company fixtures should confirm that the framework preserves different kinds of evidence:

- **Microsoft:** strong revenue, operating-income, and operating-cash-flow evidence alongside weaker FCF caused by substantially higher capital spending should create visible mixed factor evidence rather than rejection or concealment.
- **Broadridge:** strong annual confirmation with seasonal cash flow should demonstrate why TTM and comparable-quarter YoY evidence outrank raw sequential QoQ movement.
- **Walmart:** modest revenue and operating-income improvement with stronger cash generation should remain a multifactor result pending working-capital and fiscal-calendar review.

These examples are validation expectations, not preassigned scores or statuses. Fixtures must be derived from source filings under the point-in-time rules.

## 25. Decisions Required Before Production

The following remain open research decisions:

- final factor and within-factor weights;
- sector/industry peer definitions;
- winsorization or robust-clipping rules;
- minimum peer-group size and fallback hierarchy;
- minimum weighted coverage;
- within-factor reweighting caps;
- metric materiality and neutral bands;
- acceleration and persistence thresholds;
- `FastStatus` decision thresholds;
- `DataConfidence` formula and bands;
- employee-data age limits;
- stale-data limits;
- one-time-item adjustment policy; and
- treatment of multi-segment companies spanning modules.

Each approved decision must be added to the Decision Register with rationale, evidence, effective version, and superseded rule if applicable.

## 26. Recommended Development Sequence

1. Approve this scoring and status architecture.
2. Create the metric dictionary with directionality, units, duration/instant type, sector applicability, and base-effect rules.
3. Define the Operating Company metric-to-factor mapping.
4. Build calculation fixtures for Microsoft, Broadridge, and Walmart without assigning production thresholds.
5. Define provisional normalization, coverage, and confidence parameters for research testing.
6. Run fixture-level score and status sensitivity tests.
7. Draft and approve Bank, Insurer, Asset Manager/Broker, and Equity REIT modules separately.
8. Expand the test-company register to cover sector and edge-case diversity.
9. Calibrate on historical in-sample data and lock thresholds.
10. Validate out of sample, including point-in-time and restatement tests.
11. Complete independent review of locked fixtures and calculation logic.
12. Approve implementation requirements and only then begin production code.

## 27. Acceptance Criteria for This Specification

This specification is ready to serve as the implementation design baseline when:

- the four output objects are approved;
- the hard-gate list is approved;
- the five-factor architecture is accepted for research;
- the FastStatus decision framework is accepted;
- missing-data and confidence principles are approved;
- the sector-module boundaries are approved;
- all open calibration decisions have named owners or planned tests; and
- the Decision Register records the approval and effective version.

Approval of this document authorizes fixture and calibration work. It does not by itself authorize production implementation.

## 28. Revision History

| Version | Date | Change | Status |
|---|---|---|---|
| 0.1 | 2026-09-19 | Initial scoring and status specification | Proposed |

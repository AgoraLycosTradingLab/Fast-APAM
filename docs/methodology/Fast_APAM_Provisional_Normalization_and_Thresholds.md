# Fast APAM Provisional Normalization and Thresholds

**Version:** 0.1  
**Status:** Proposed for research fixtures and sensitivity testing only  
**Initial module:** Operating Companies  
**Production status:** Not approved for live scoring or investment use  
**Governing documents:** `Fast_APAM_Scoring_and_Status_Specification.md`, `Fast_APAM_Metric_Dictionary.md`, `Operating_Company_Metric_to_Factor_Mapping.md`, and `Period_Construction_Rules.md`

## 1. Purpose

This document defines provisional normalization, coverage, score-band, directional-status, data-confidence, and data-status rules for Fast APAM research fixtures.

Its purpose is to permit controlled numerical testing without representing unvalidated parameters as final production logic.

The central distinction is:

- `FastScore` measures relative recent strength versus appropriate peers on a 0–100 scale.
- `FastStatus` describes the company's absolute recent direction and momentum.

This separation is necessary because a percentile rank always has a median even when an entire sector is deteriorating. A high relative score does not automatically mean the business is accelerating, and a low relative score does not automatically mean it is deteriorating.

## 2. Governing Constraints

1. Standalone-quarter YoY and TTM YoY comparisons remain primary.
2. Raw sequential QoQ changes receive zero primary weight.
3. Acceleration is a 15% factor contribution and a status input, not an elimination gate.
4. Missing is not zero.
5. Data confidence remains separate from economic score.
6. Core APAM and Fast APAM remain separate outputs.
7. All peer observations must be point-in-time eligible on the shared model date.
8. Financials and REITs require their own normalization studies; this v0.1 specification initially applies to Operating Companies.

## 3. Research Output Labels

Until validation and Decision Register approval, numerical outputs generated under this document must use these labels:

- `PROVISIONAL_FAST_SCORE`
- `PROVISIONAL_FACTOR_SCORE`
- `PROVISIONAL_FAST_STATUS`
- `PROVISIONAL_DATA_CONFIDENCE`
- `PROVISIONAL_DATA_STATUS`

No provisional result may be relabeled as production merely because its arithmetic is correct.

## 4. Evaluation Date and Peer Snapshot

Every normalization run is tied to one shared model date `D`.

For each company on `D`:

1. Use only filings with `model_available_date <= D`.
2. Use the latest eligible issuer fiscal quarter.
3. Use the point-in-time universe and sector classification effective on `D`.
4. Retain the latest fiscal period, period end, filing availability date, and data age.
5. Use only as-filed information that was knowable on `D` for historical research.

Companies may have different latest fiscal quarters on the same model date. They are not forced into a common calendar quarter.

## 5. Peer Eligibility and Staleness

### 5.1 Provisional data-age bands

`DataAgeDays = model date − latest eligible filing's model-available date`

| Data age | Peer treatment | DataStatus implication |
|---|---|---|
| 0–120 calendar days | Current | No staleness penalty |
| 121–180 calendar days | Usable but stale | `STALE` flag and confidence penalty |
| More than 180 days | Excluded from primary peer normalization | Normally `STALE` or `INSUFFICIENT_HISTORY` |

These thresholds are provisional. Sensitivity tests must include 90/150, 120/180, and 150/210-day alternatives.

### 5.2 Peer-record eligibility

A company-metric observation enters a peer distribution only if:

- the company belongs to the point-in-time universe;
- the applicable sector module is approved for the research run;
- the metric and comparison periods pass construction checks;
- its data age is within the approved limit;
- units, dimensions, and accounting scope are valid;
- its transformation is defined; and
- it has no unresolved critical quality flag.

A weak economic observation remains eligible. Only defective or incomparable data are excluded.

## 6. Peer-Group Hierarchy

Peer groups are selected separately for each metric because coverage can differ.

### 6.1 Provisional hierarchy

| Priority | Peer group | Minimum eligible observations |
|---:|---|---:|
| 1 | GICS sub-industry | 15 |
| 2 | GICS industry | 25 |
| 3 | GICS industry group | 35 |
| 4 | GICS sector, excluding Financials and REITs when using the Operating Company module | 50 |
| 5 | All eligible Operating Companies | 150 |

Use the narrowest peer group meeting the minimum count. Store the chosen level and count for every metric score.

### 6.2 Peer fallback restrictions

- Do not combine Operating Companies with Banks, Insurers, or REITs merely to reach a minimum count.
- Do not substitute a current classification for a historical point-in-time classification.
- Do not switch peer levels silently between the current and comparison run.
- If the peer hierarchy changes, record it and run a rank-stability test.
- A metric with fewer than 15 eligible peers at every approved level is `PEER_GROUP_INSUFFICIENT` and is not normalized.

### 6.3 Multi-industry issuers

Use the issuer's effective primary classification for v0.1. A segment-weighted peer construction is deferred. Material multi-industry ambiguity receives `PEER_CLASSIFICATION_REVIEW`.

## 7. Signal Preparation

### 7.1 Direction alignment

Convert each raw signal to an aligned signal where higher always means stronger evidence:

`AlignedSignal = DirectionMultiplier × RawSignal`

`DirectionMultiplier` is:

- `+1` when higher is favorable;
- `−1` when lower is favorable; or
- unavailable when the relationship is conditional and has not been classified.

Capex intensity is conditional and must first be classified as `EFFICIENCY_SUPPORT`, `INVESTMENT_SUPPORT`, `CASH_BURDEN`, `AMBIGUOUS`, or `INELIGIBLE`. It is not ranked as a simple monotonic metric in v0.1.

### 7.2 Base-effect handling

| Condition | Primary handling |
|---|---|
| Stable positive denominator | Percentage change |
| Rate, margin, or yield | Percentage-point or basis-point change |
| Negative-to-positive or positive-to-negative | Sign-change class plus scaled/absolute change if approved |
| Near-zero denominator | Stable-denominator scaled change or exclusion |
| Both values negative | Approved level/margin change, not ordinary growth |
| Definition or scope change | Reconcile or exclude |

No explosive percentage is allowed to enter normalization solely because the comparison base is immaterial.

### 7.3 Materiality filter

Before peer ranking, signals inside the applicable neutral band may be set to the neutral anchor for status analysis. The unrounded raw result remains stored.

The materiality filter does not erase small peer-rank differences from research diagnostics; it prevents those differences from controlling `FastStatus`.

## 8. Primary Normalization Method

### 8.1 Empirical percentile score

The v0.1 primary method is a directionally aligned empirical percentile rank using midranks for ties.

For peer group size `N` and aligned midrank `r`, where rank 1 is weakest:

`MetricScore = 100 × (r − 0.5) / N`

Properties:

- bounded between approximately 0 and 100;
- monotonic;
- robust to extreme magnitudes;
- interpretable as relative standing; and
- does not assume a normal distribution.

Retain at least four decimal places internally. Display no more than one decimal place for research output.

### 8.2 Tie handling

Identical aligned signals receive the average of their occupied ranks. Approximate or rounded employee values may generate many ties; the tie count and disclosure precision must be retained.

### 8.3 Outlier treatment

Because the primary transform is rank-based, extreme magnitudes cannot push a score beyond the percentile range. However, every input must still pass anomaly review.

For research diagnostics:

- calculate the 2.5th and 97.5th peer percentiles;
- flag observations outside those bounds as `PEER_EXTREME`;
- do not automatically exclude them when source and economics are valid; and
- compare ranks with a 5th/95th-percentile winsorized sensitivity run.

Winsorization changes magnitudes for sensitivity methods, not the factual reported value.

## 9. Secondary Robust-Z Sensitivity Method

The primary percentile result must be tested against a robust-z transformation.

For peer median `M` and median absolute deviation `MAD`:

`RobustZ = 0.6745 × (AlignedSignal − M) / MAD`

Cap `RobustZ` at `[-3, +3]`, then map it to 0–100 using the standard normal cumulative distribution.

When `MAD = 0` or coverage is inadequate, the robust-z method is unavailable. It never replaces the primary percentile score without a documented decision.

The purpose of this sensitivity test is to identify cases where dense ties or small peer groups make empirical ranks unstable.

## 10. Absolute Neutral Bands

The following v0.1 bands are provisional starting points for status classification. They do not directly determine percentile scores.

| Signal family | Adverse | Neutral | Supportive |
|---|---:|---:|---:|
| Revenue YoY growth | Below -1.0% | -1.0% to +1.0% | Above +1.0% |
| Operating-profit YoY growth | Below -2.0% | -2.0% to +2.0% | Above +2.0% |
| CFO/FCF YoY growth with valid base | Below -3.0% | -3.0% to +3.0% | Above +3.0% |
| Operating-margin YoY change | Below -0.25 pp | -0.25 to +0.25 pp | Above +0.25 pp |
| FCF-margin YoY change | Below -0.50 pp | -0.50 to +0.50 pp | Above +0.50 pp |
| Revenue–employee growth spread | Below -1.0 pp | -1.0 to +1.0 pp | Above +1.0 pp |
| Quarter or TTM acceleration | Below -1.0 pp | -1.0 to +1.0 pp | Above +1.0 pp |

These bands must be tested by industry, volatility, company size, and reporting precision. A metric-specific band overrides the generic acceleration band when documented.

## 11. Metric Score Interpretation

| MetricScore | Relative interpretation |
|---:|---|
| 80–100 | Very strong versus peers |
| 65–<80 | Strong |
| 55–<65 | Moderately positive |
| 45–<55 | Peer-neutral |
| 35–<45 | Moderately weak |
| 20–<35 | Weak |
| 0–<20 | Very weak |

These labels describe relative standing only. Absolute direction comes from raw aligned signals and neutral bands.

## 12. Factor Aggregation

### 12.1 Factor score

Within each factor:

`FactorScore = Σ(AppliedMetricWeight × MetricScore) / Σ(AppliedMetricWeight)`

The denominator contains eligible applied weights only after controlled within-factor reweighting. Missing observations are not assigned a zero score.

### 12.2 Reweighting cap

For Operating Company fixture testing:

- no metric may exceed 125% of its original within-factor weight;
- the approved F2 gross-profit fallback may move revenue and operating profit from 45%/45% to 50%/50%;
- weights do not move across factors; and
- residual missing coverage remains visible and affects confidence/status.

### 12.3 Factor coverage floors

| Factor | Provisional floor |
|---|---|
| F1 TTM | Revenue and operating-profit anchors, one cash signal, and at least 60% original weight |
| F2 latest quarter | Revenue and operating-profit anchors and at least 90% original weight after approved fallback |
| F3 quality | Operating-margin anchor, one independent confirmation, and at least 50% original weight |
| F4 acceleration | Two independent families and at least 40% original weight |
| F5 breadth | At least three eligible independent families |

## 13. Composite FastScore

When all required scoreability rules pass:

`FastScore = 0.35(F1) + 0.25(F2) + 0.20(F3) + 0.15(F4) + 0.05(F5)`

The factor weights are not renormalized across missing factors. A required factor below its floor prevents the standard FastScore.

### 13.1 Provisional score-strength bands

| FastScore | Relative recent-strength band |
|---:|---|
| 75–100 | Very strong |
| 60–<75 | Strong |
| 52.5–<60 | Moderately positive |
| 47.5–<52.5 | Peer-neutral |
| 40–<47.5 | Moderately weak |
| 25–<40 | Weak |
| 0–<25 | Very weak |

These bands do not map mechanically to `FastStatus`.

## 14. Level and Momentum Sub-Indices

To support status classification, calculate two transparent sub-indices.

### 14.1 Relative Level Index

F1, F2, and F3 contain 80% of the model and describe recent operating level/quality.

`RelativeLevelIndex = (0.35F1 + 0.25F2 + 0.20F3) / 0.80`

### 14.2 Relative Momentum Index

F4 contains the explicit acceleration and persistence evidence.

`RelativeMomentumIndex = F4`

F5 is retained as breadth confirmation rather than blended into either sub-index.

### 14.3 Absolute Direction Index

Relative ranks alone cannot identify broad deterioration. Therefore calculate an absolute family-direction summary:

- `+1` for each supportive eligible family;
- `0` for neutral;
- `−1` for adverse;
- `0` plus a conflict flag for conflicted; and
- exclude ineligible families from the denominator.

`AbsoluteDirectionIndex = sum of family direction values / eligible family count`

Store supportive, adverse, neutral, conflicted, and ineligible counts separately. This index is a status aid, not part of FastScore in v0.1.

## 15. Family Classification Rules

Each economic family receives one final classification after reconciling its metrics:

- `SUPPORTIVE`
- `NEUTRAL`
- `ADVERSE`
- `CONFLICTED`
- `INELIGIBLE`

### 15.1 Operating Company provisional rules

| Family | Supportive | Adverse | Conflicted |
|---|---|---|---|
| Growth | TTM and/or latest quarter above neutral with no material contradiction | TTM and latest quarter below neutral | TTM and quarter materially disagree |
| Profit | Operating-profit and/or margin evidence above neutral | Profit and margin evidence below neutral | Profit growth and margin direction disagree materially |
| Cash | CFO and FCF broadly supportive | CFO and FCF broadly adverse | CFO and FCF materially diverge |
| Margin | Operating and cash margins broadly agree | Both broadly weaken | Operating margin and FCF/CFO margins materially diverge |
| Productivity | Per-employee evidence and growth spread supportive | Both adverse | Employee precision/age or component disagreement prevents a coherent conclusion |
| Capital | Valid classification supports efficiency/investment quality | Valid classification shows cash/return burden | Investment support and cash burden coexist or classification is ambiguous |

Family thresholds must respect the absolute neutral bands and source precision.

## 16. Provisional FastStatus Rules

Status uses relative level, relative momentum, absolute direction, breadth, and conflict. It is not a score-band lookup.

### 16.1 `ACCELERATING`

Assign only when all are true:

- `RelativeLevelIndex >= 55`;
- `RelativeMomentumIndex >= 60`;
- at least three supportive independent families;
- supportive families outnumber adverse families by at least two;
- no unresolved critical conflict in a module-critical family; and
- absolute level evidence is not broadly negative.

### 16.2 `IMPROVING`

Assign when either pattern holds:

**Positive improvement:**

- `RelativeLevelIndex >= 52.5`;
- momentum is at least neutral (`>= 47.5`) or absolute family direction is clearly supportive; and
- no deterioration rule applies.

**Early recovery:**

- `RelativeLevelIndex` is 35–<52.5;
- `RelativeMomentumIndex >= 60`;
- at least two formerly weak families show supportive acceleration; and
- absolute evidence is improving even if current levels remain weak.

An early recovery is `IMPROVING`, not `ACCELERATING`, until level evidence crosses the required threshold.

### 16.3 `STABLE`

Assign when:

- `RelativeLevelIndex` is 45–55;
- `RelativeMomentumIndex` is 42.5–57.5;
- absolute family evidence is predominantly neutral; and
- there is no material cross-family conflict.

### 16.4 `DECELERATING`

Assign when:

- current level remains at least adequate (`RelativeLevelIndex >= 47.5` or absolute levels remain positive);
- `RelativeMomentumIndex < 42.5` or at least two major families show adverse acceleration; and
- the deterioration threshold is not met.

This rule preserves the strong-but-slowing case.

### 16.5 `DETERIORATING`

Assign when all are true:

- `RelativeLevelIndex < 42.5`;
- `RelativeMomentumIndex < 47.5`, unless missing momentum evidence is replaced by broad absolute deterioration;
- at least three independent families are adverse; and
- adverse families exceed supportive families by at least two.

A single weak metric cannot produce `DETERIORATING` unless a later sector module designates it as critical.

### 16.6 `MIXED`

Assign when a coherent directional classification would conceal material disagreement, including any of:

- at least two supportive and at least two adverse/conflicted families;
- operating growth/profit are supportive while cash and capital are materially adverse/conflicted;
- TTM and latest-quarter evidence point in opposite material directions;
- absolute direction conflicts with relative level/momentum; or
- the result is sensitive to one unresolved conditional classification.

`MIXED` is an economic-evidence result, not a data failure.

### 16.7 `UNSCORED`

Assign when data, history, period comparability, sector methodology, or peer normalization cannot support a standard result. `UNSCORED` never means deterioration.

### 16.8 Status precedence

Apply this order:

1. Critical data/methodology gate → `UNSCORED`.
2. Material conflict rule → `MIXED`.
3. Deterioration rule.
4. Deceleration rule.
5. Acceleration rule.
6. Improvement rule.
7. Stable rule.
8. If none applies → `MIXED` and review.

This precedence prevents a high relative percentile from hiding material economic conflict.

## 17. Persistence Scoring

### 17.1 Quarterly observation classes

For up to four quarterly YoY observations, classify each aligned signal:

- supportive: `+1`;
- neutral: `0`; or
- adverse: `−1`.

### 17.2 Provisional recency weights

From oldest to newest:

- t−3: 10%
- t−2: 20%
- t−1: 30%
- current: 40%

`PersistenceRaw = Σ(class × recency weight)`

Map `PersistenceRaw` from `[-1, +1]` to `[0, 100]`:

`PersistenceScore = 50 × (PersistenceRaw + 1)`

This is the only initial metric allowed to use a deterministic absolute mapping rather than a peer percentile, because it is already a bounded directional-state summary. A peer-percentile sensitivity result should still be stored.

## 18. Breadth Scoring

For each eligible family:

- supportive = 1.0;
- neutral = 0.5;
- adverse = 0.0;
- conflicted = 0.25; and
- ineligible = excluded.

`BreadthScore = 100 × sum(family values) / eligible family count`

The 0.25 conflicted value is provisional. Sensitivity tests must compare 0.0, 0.25, and 0.5.

Breadth requires at least three eligible independent families.

## 19. Conditional Capex Classification

Capex intensity is not peer-ranked until it receives one of these classes:

| Class | Provisional factor input | Required evidence |
|---|---:|---|
| `EFFICIENCY_SUPPORT` | 65 | Intensity falls without material operating impairment |
| `INVESTMENT_SUPPORT` | 60 | Intensity rises with supportive operating growth and no severe cash-quality deterioration |
| `CASH_BURDEN` | 25 | Intensity rises while FCF/margin/returns weaken materially |
| `AMBIGUOUS` | 50 for score sensitivity only; conflict flag required | Investment support and burden cannot be separated |
| `INELIGIBLE` | Missing | Insufficient or incomparable evidence |

These fixed provisional values exist only to test the mapping. They must be compared with exclusion and peer-conditioned alternatives. `AMBIGUOUS` must still contribute a conflict flag even when the score sensitivity uses 50.

## 20. Employee-Data Weight and Confidence

### 20.1 Provisional age treatment

| Employee observation age | Weight multiplier | Confidence treatment |
|---:|---:|---|
| 0–120 days | 1.00 | No age penalty |
| 121–240 days | 0.75 | `CARRIED_EMPLOYEE` |
| 241–365 days | 0.50 | `CARRIED_EMPLOYEE_STALE` |
| More than 365 days | 0.00 | `NO_EMPLOYEE_SIGNAL` |

Approximate or materially rounded disclosures apply an additional 0.80 multiplier for the employee sleeve during research testing.

Combined employee weight multiplier:

`EmployeeWeightMultiplier = AgeMultiplier × PrecisionMultiplier`

The removed employee weight may be redistributed only under the Operating Company mapping cap. It is never treated as adverse performance.

### 20.2 Sensitivity alternatives

Test maximum ages of 270, 365, and 450 days and precision multipliers of 0.6, 0.8, and 1.0.

## 21. Overall Scoreability and Coverage

A standard provisional FastScore requires:

- F1, F2, and F3 factor floors;
- F4 factor floor and required history;
- at least three breadth families;
- at least 70% original total metric-weight coverage before reweighting;
- an approved Operating Company mapping;
- sufficient peers for each required normalized metric; and
- no unresolved critical gate.

### 21.1 Coverage bands

| Original total coverage | Treatment |
|---:|---|
| 85–100% | Full research coverage |
| 70–<85% | Partial but potentially scoreable |
| Below 70% | No standard FastScore |

Factor floors still apply even when total coverage exceeds 70%.

## 22. Provisional DataConfidence

`DataConfidence` measures evidence reliability and is not multiplied into `FastScore`.

### 22.1 Component architecture

| Component | Weight | Full-credit condition |
|---|---:|---|
| Source authority and lineage | 20% | Filed facts with complete accession/concept/context lineage |
| Period construction integrity | 25% | All identities pass; derived observations reproduce exactly |
| Point-in-time integrity | 20% | Filing date, buffer, universe, and as-filed vintage verified |
| Comparability and timeliness | 15% | Comparable fiscal periods and current data |
| Metric/factor coverage | 15% | At least 85% original coverage and all factor floors |
| Denominator/definition quality | 5% | Employee, capex, and non-GAAP definitions timely and precise |
| **Total** | **100%** | |

Score each component from 0–100, then:

`DataConfidence = Σ(ComponentWeight × ComponentScore)`

### 22.2 Provisional component deductions

Use attributable deductions, never discretionary blanket haircuts.

| Condition | Affected component | Provisional deduction |
|---|---|---:|
| Derived quarter that fully reconciles | Period construction | 0–2 points per affected factor, sensitivity only |
| Derived Q4 that fully reconciles | Period construction | 2 points |
| Proxy-bracketed rather than direct universe history | Point-in-time | 5 points |
| Data age 121–180 days | Comparability/timeliness | 15 points |
| Carried employee 121–240 days | Denominator/definition | 15 points |
| Carried employee 241–365 days | Denominator/definition | 35 points |
| Approximate employee disclosure | Denominator/definition | 20 points |
| Vendor-only fact | Source authority | 25 points |
| Unresolved noncritical definition change | Comparability or denominator | 20 points |
| Total coverage 70–<85% | Coverage | Scale coverage component proportionally |

Deductions apply only to their components and are capped at the component's available points.

### 22.3 Confidence bands

| DataConfidence | Interpretation |
|---:|---|
| 85–100 | High confidence |
| 70–<85 | Usable with limitations |
| 55–<70 | Review required |
| Below 55 | Insufficient for a standard score |

## 23. Provisional DataStatus Logic

Apply the most restrictive applicable status using this precedence:

1. `SECTOR_MODULE_UNAVAILABLE`
2. `PERIOD_INCOMPARABLE`
3. `INSUFFICIENT_HISTORY`
4. `REVIEW_REQUIRED`
5. `STALE`
6. `PARTIAL`
7. `PASS`

### 23.1 Status rules

| DataStatus | Provisional rule |
|---|---|
| `PASS` | All factor floors, at least 85% coverage, confidence at least 85, and no unresolved material flags |
| `PARTIAL` | Scoreability floors pass, coverage 70–<85 or meaningful noncritical evidence is missing, confidence at least 70 |
| `STALE` | Required observation is 121–180 days old but remains within the permitted peer window |
| `REVIEW_REQUIRED` | Confidence 55–<70 or a material noncritical ambiguity remains |
| `INSUFFICIENT_HISTORY` | Required YoY, TTM, acceleration, or peer history is unavailable |
| `PERIOD_INCOMPARABLE` | Fiscal periods cannot be compared defensibly |
| `SECTOR_MODULE_UNAVAILABLE` | No approved applicable module exists |

Only `PASS`, `PARTIAL`, and conditionally `STALE` may carry a non-null provisional FastScore.

## 24. Microsoft Fixture Application Gate

The Microsoft FY2026 scoring fixture currently has:

- full raw evidence coverage for F1, F2, F3, and F5;
- 48% provisional raw availability for F4;
- a valid mixed operating/cash/capital evidence pattern;
- no approved peer distribution; and
- incomplete prior-quarter TTM and margin acceleration inputs.

Under this document, Microsoft cannot yet receive a numerical score until:

1. the required F4 history is constructed;
2. a point-in-time Operating Company peer snapshot is assembled;
3. each required metric has a valid peer group; and
4. the provisional rules are approved for fixture testing.

Once those conditions pass, Microsoft's status must be tested against the `MIXED` precedence rule before any acceleration or improvement label.

## 25. Sensitivity-Test Matrix

Every research run must compare at least:

| Dimension | Primary | Alternatives |
|---|---|---|
| Normalization | Empirical percentile | Robust-z CDF |
| Peer level | Narrowest group meeting minimum | One level broader |
| Minimum peers | 15/25/35/50/150 hierarchy | 10/20/30/40/100 and 20/30/40/60/175 |
| Staleness | 120/180 days | 90/150 and 150/210 |
| Outlier diagnostic | 2.5/97.5 | 5/95 |
| Reweight cap | 125% | 100% and 150% |
| Total coverage floor | 70% | 65% and 80% |
| Neutral score band | 47.5–52.5 | 45–55 |
| Acceleration status cutoff | 60 | 55 and 65 |
| Conflict breadth value | 0.25 | 0.0 and 0.5 |
| Employee maximum age | 365 days | 270 and 450 days |

Report rank correlations, score changes, status changes, coverage, and turnover for each alternative.

## 26. Calibration and Validation Requirements

### 26.1 Calibration sample

Use a point-in-time, sector-balanced history spanning:

- economic expansion and recession;
- high- and low-rate environments;
- commodity and inventory cycles;
- high-capex and low-capex business models;
- acquisition-heavy and organically growing companies;
- positive, negative, and sign-changing bases; and
- 52/53-week fiscal calendars.

### 26.2 Predeclared evaluation measures

- cross-sectional score dispersion;
- month-to-month and quarter-to-quarter rank stability;
- status transition frequency;
- false reversal rate;
- coverage and missingness by sector/industry;
- sensitivity to one metric and one filing;
- forward-return information coefficient and spreads;
- drawdown and false-positive behavior;
- Core-only versus Fast-only versus Core/Fast state-matrix comparisons; and
- interpretability and reproducibility.

### 26.3 Locking rule

After calibration:

1. choose parameters using the in-sample period;
2. record them in the Decision Register;
3. freeze the rules;
4. evaluate them out of sample without retuning; and
5. retain failed or superseded parameter sets for audit.

## 27. Rejection Criteria

Revise or reject this provisional framework if:

- peer groups frequently fall below minimum sizes;
- status outcomes are dominated by arbitrary neutral bands;
- small input changes cause frequent status flips;
- missing employee data systematically biases sectors;
- percentile normalization hides broad absolute deterioration;
- the capex classification produces unstable discretionary outcomes;
- F4 acceleration overwhelms strong TTM evidence despite its 15% cap;
- results depend materially on current rather than point-in-time classifications; or
- Fast APAM adds no stable information beyond annual Core APAM.

## 28. Decisions Proposed for Approval

| Decision | Provisional rule |
|---|---|
| Primary normalization | Directionally aligned empirical percentile with midranks |
| Sensitivity normalization | Median/MAD robust-z mapped through normal CDF |
| Peer hierarchy | Sub-industry → industry → industry group → sector → Operating Company universe |
| Staleness | Current through 120 days; stale to 180; exclude after 180 |
| Reweighting cap | 125%, with documented F2 exception |
| Total scoreability coverage | 70%; full research coverage at 85% |
| FastScore bands | 75/60/52.5/47.5/40/25 boundaries |
| Status basis | Relative level + relative momentum + absolute family direction + conflict precedence |
| Persistence | 10/20/30/40 recency weights |
| Breadth | Supportive 1.0, neutral 0.5, conflicted 0.25, adverse 0.0 |
| Employee carry | 1.0/0.75/0.50/0.0 age multipliers through 365 days |
| DataConfidence | Six-component weighted system |

Approval of these rules authorizes provisional fixture and sensitivity testing only.

## 29. Recommended Next Step

After approval:

1. extend the Microsoft fixture to complete prior-quarter TTM and margin acceleration;
2. construct a point-in-time Operating Company peer snapshot for 2026-07-31;
3. calculate provisional Microsoft metric percentiles and factor scores;
4. run the sensitivity matrix; and
5. determine whether the provisional `MIXED` status remains stable.

Do not begin broad production implementation until the peer snapshot, Microsoft numerical fixture, Broadridge/Walmart fixtures, and threshold sensitivity tests pass.

## 30. Revision History

| Version | Date | Change | Status |
|---|---|---|---|
| 0.1 | 2026-09-20 | Initial provisional normalization, status, confidence, and threshold framework | Proposed for research approval |

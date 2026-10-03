# Operating Company Metric-to-Factor Mapping

**Version:** 0.1  
**Status:** Draft for approval and controlled fixture testing  
**Module:** Fast APAM — Operating Companies  
**Governing documents:** `Fast_APAM_Scoring_and_Status_Specification.md`, `Fast_APAM_Metric_Dictionary.md`, `Period_Construction_Rules.md`, `Data_Contract.md`, and `Decision_Register.md`  
**Implementation status:** No production scoring implementation authorized by this document

## 1. Purpose

This document selects the initial Operating Company metrics and maps them into the five-factor Fast APAM scoring architecture. It defines provisional within-factor weights, economic-family boundaries, fallback relationships, missing-data rules, coverage requirements, and the fixture calculations needed before implementation.

The mapping preserves the governing Fast APAM design:

- Core APAM measures durable, multi-year quality.
- Fast APAM measures recent operating direction.
- Standalone-quarter YoY and TTM YoY comparisons are primary.
- Raw sequential QoQ changes are diagnostic only and receive zero primary weight.
- Acceleration is a graded contribution, not an automatic elimination gate.
- Weak economic results reduce the score or status; only invalid or insufficient evidence prevents scoring.

## 2. Applicability

The Operating Company module applies when ordinary commercial measures—revenue, operating income, operating cash flow, capital expenditure, margins, and employee productivity—represent the issuer's economics.

It does not apply mechanically to:

- banks and other deposit-taking institutions;
- insurers;
- asset managers or brokers requiring a Financials submodule;
- equity REITs;
- mortgage REITs; or
- issuers whose principal economics cannot be represented by the selected operating metrics.

An issuer outside the approved module receives `SECTOR_MODULE_UNAVAILABLE` rather than an improvised Operating Company score.

## 3. Five-Factor Architecture

| Factor | Model weight | Purpose |
|---|---:|---|
| `F1_TTM` | 35% | Stable recent operating, cash-generation, and productivity evidence |
| `F2_QUARTER` | 25% | Latest comparable standalone-quarter YoY evidence |
| `F3_QUALITY` | 20% | Margin, conversion, operating-leverage, and productivity confirmation |
| `F4_ACCELERATION` | 15% | Change in comparable YoY rates and persistence |
| `F5_BREADTH` | 5% | Agreement across independent economic families |
| **Total** | **100%** | |

The factor weights are the approved research architecture. All within-factor weights in this document are provisional and must be validated before production.

## 4. Metric Selection Principles

1. Prefer filed GAAP statement components with clear period construction.
2. Use TTM evidence to stabilize seasonal cash flow and investment cycles.
3. Use the latest comparable fiscal quarter for recency, never calendar-quarter coercion.
4. Recompute margins from compatible numerator and denominator components.
5. Do not count two expressions of the same economic fact as independent breadth.
6. Treat employee productivity as an optional evidence sleeve when the denominator is valid.
7. Preserve profit/cash-flow divergence instead of averaging it away invisibly.
8. Use sector- or industry-specific alternates only after documented approval.
9. Do not treat rising capex as automatically favorable or unfavorable.
10. Keep ROIC aligned with Core APAM and outside the initial Fast v0.1 score until its interim definition is approved.

## 5. Economic Families

The Operating Company module uses six controlled economic families.

| Family ID | Family | Principal metrics | Breadth vote |
|---|---|---|---:|
| `EF_GROWTH` | Revenue/activity growth | Revenue | One |
| `EF_PROFIT` | Operating profitability | Operating income; EBIT only as alternate | One |
| `EF_CASH` | Cash generation | CFO, FCF | One |
| `EF_MARGIN` | Margin and operating leverage | Operating margin, FCF margin, operating-leverage spread | One |
| `EF_PRODUCTIVITY` | Workforce productivity | Revenue/employee, operating income/employee, revenue–employee growth spread | One when eligible |
| `EF_CAPITAL` | Capital efficiency and investment burden | Capex intensity; future ROIC | One when eligible |

Metrics within one family may improve robustness but do not create extra independent breadth votes.

## 6. v0.1 Metric Tiers

### 6.1 Required anchors

These metrics form the initial scoreability anchors:

- `OP_REVENUE`
- `OP_OPERATING_INCOME`, with `OP_EBIT` allowed only as an approved alternate
- `OP_CFO`
- `OP_CAPEX`
- derived `OP_FCF`
- `OP_OPERATING_MARGIN`

Failure to obtain valid revenue and operating-profit comparisons generally prevents the standard Operating Company module from scoring. Missing CFO or capex may still permit a limited partial result only after the minimum-coverage policy is approved and the cash family is visibly absent.

### 6.2 Conditional metrics

These enter only when their inputs and interpretations are defensible:

- `OP_GROSS_PROFIT`
- `OP_GROSS_MARGIN`
- `OP_CFO_MARGIN`
- `OP_FCF_MARGIN`
- `OP_CAPEX_INTENSITY`
- `OP_CASH_CONVERSION`
- `OP_FCF_CONVERSION`
- `OP_REVENUE_PER_EMPLOYEE`
- `OP_OPERATING_INCOME_PER_EMPLOYEE`
- `OP_FCF_PER_EMPLOYEE`
- `OP_REVENUE_GROWTH_MINUS_EMPLOYEE_GROWTH`
- `OP_OPERATING_LEVERAGE_SPREAD`

### 6.3 Deferred metrics

The following remain outside the v0.1 composite pending further definition or stability testing:

- `OP_ROIC`
- `OP_INCREMENTAL_ROIC`
- `OP_ASSET_TURNOVER`
- `OP_WORKING_CAPITAL_EFFICIENCY`

They may be calculated as research diagnostics when their definitions are documented, but they receive zero production-intent weight in this mapping.

## 7. Factor 1 — TTM Operating and Productivity Improvement

**Factor weight:** 35% of `FastScore`  
**Purpose:** Measure recent operating strength using a four-quarter window that reduces seasonal noise.

### 7.1 Provisional within-factor mapping

| Sleeve | Metric signal | Economic family | Weight within F1 | Eligibility |
|---|---|---|---:|---|
| Revenue | `OP_REVENUE` TTM YoY | `EF_GROWTH` | 20% | Required |
| Operating profit | `OP_OPERATING_INCOME` TTM YoY | `EF_PROFIT` | 25% | Required; EBIT alternate allowed |
| Operating cash flow | `OP_CFO` TTM YoY | `EF_CASH` | 15% | Required for full coverage |
| Free cash flow | `OP_FCF` TTM YoY or approved alternate transformation | `EF_CASH` | 20% | Required for full coverage; base protection applies |
| Workforce productivity | Productivity composite | `EF_PRODUCTIVITY` | 20% | Conditional on valid employee data |
| **Total** | | | **100%** | |

### 7.2 Productivity composite

When eligible, the productivity sleeve is provisionally composed of:

| Metric | Productivity-sleeve weight |
|---|---:|
| `OP_REVENUE_PER_EMPLOYEE` TTM YoY | 50% |
| `OP_OPERATING_INCOME_PER_EMPLOYEE` TTM YoY or approved scaled change | 35% |
| `OP_REVENUE_GROWTH_MINUS_EMPLOYEE_GROWTH` | 15% |
| **Total** | **100%** |

`OP_FCF_PER_EMPLOYEE` is initially diagnostic because it substantially overlaps the FCF signal and may amplify capex-cycle effects. It may replace operating-income-per-employee only through an approved industry mapping; it does not enter alongside it by default.

### 7.3 Employee-data treatment

| Employee class | F1 treatment |
|---|---|
| `OBSERVED_EMPLOYEE` | Productivity sleeve eligible at full provisional weight |
| `CARRIED_EMPLOYEE` | Sleeve may be eligible with disclosed age, reduced confidence, and future decay rule |
| `NO_EMPLOYEE_SIGNAL` | Sleeve is missing, never zero; factor may remain partially scoreable |

Until an age-decay schedule is approved, carried employee observations must be identified separately in fixtures and may not be labeled full-confidence evidence.

### 7.4 Base-effect rules

- Revenue normally uses percentage growth.
- Operating income uses percentage growth only when the base is economically suitable.
- CFO and FCF use percentage growth only when signs and bases are suitable.
- Across zero, negative, or immaterial bases, use an approved margin, absolute, or scaled change; otherwise exclude with `BASE_EFFECT`.
- Exclusion from percentage growth does not turn the reported economic result into missing. The valid raw value remains in the audit output.

## 8. Factor 2 — Latest Comparable-Quarter YoY Improvement

**Factor weight:** 25% of `FastScore`  
**Purpose:** Capture the newest comparable operating evidence without relying on seasonal sequential changes.

### 8.1 Provisional within-factor mapping

| Metric signal | Economic family | Weight within F2 | Eligibility |
|---|---|---:|---|
| `OP_REVENUE` latest standalone-quarter YoY | `EF_GROWTH` | 45% | Required |
| `OP_OPERATING_INCOME` latest standalone-quarter YoY | `EF_PROFIT` | 45% | Required; EBIT alternate allowed |
| `OP_GROSS_PROFIT` latest standalone-quarter YoY | `EF_PROFIT` | 10% | Conditional; industry applicability required |
| **Total** | | **100%** | |

### 8.2 Why quarterly cash flow is excluded from F2 by default

Standalone-quarter CFO, capex, and FCF can be reconstructed and displayed, but they are often highly seasonal and affected by working-capital timing. They remain diagnostics in F2 unless an approved industry rule demonstrates that quarterly cash flow is comparable and useful. TTM cash-flow evidence remains primary in F1 and F3.

### 8.3 Gross-profit fallback

If gross profit is unavailable or economically inappropriate:

- do not manufacture it from incompatible cost concepts;
- do not treat it as zero;
- redistribute its provisional sleeve only between revenue and operating income, subject to the reweighting cap; and
- mark F2 coverage below 100% if the cap leaves residual weight.

## 9. Factor 3 — Margin, Cash Quality, and Operating Confirmation

**Factor weight:** 20% of `FastScore`  
**Purpose:** Determine whether growth is supported by margins, cash conversion, operating leverage, productivity, and a defensible investment burden.

### 9.1 Provisional within-factor mapping

| Sleeve | Metric signal | Family | Weight within F3 | Eligibility |
|---|---|---|---:|---|
| Operating margin | TTM YoY percentage-point change in `OP_OPERATING_MARGIN` | `EF_MARGIN` | 30% | Required |
| FCF margin | TTM YoY percentage-point change in `OP_FCF_MARGIN` | `EF_CASH`/`EF_MARGIN` | 20% | Required for full coverage |
| Operating leverage | `OP_OPERATING_LEVERAGE_SPREAD` | `EF_MARGIN` | 20% | Conditional on valid profit growth signal |
| Workforce confirmation | `OP_REVENUE_GROWTH_MINUS_EMPLOYEE_GROWTH` | `EF_PRODUCTIVITY` | 15% | Conditional on employee data |
| Investment burden | TTM YoY change in `OP_CAPEX_INTENSITY` | `EF_CAPITAL` | 15% | Conditional interpretation |
| **Total** | | | **100%** | |

### 9.2 Capex-intensity interpretation

Capex intensity is not scored with a universal “lower is better” rule. It is classified as:

- `EFFICIENCY_SUPPORT`: intensity falls while operating capacity and growth remain adequate;
- `INVESTMENT_SUPPORT`: intensity rises with credible operating growth or disclosed capacity investment;
- `CASH_BURDEN`: intensity rises while cash generation and returns weaken;
- `AMBIGUOUS`: evidence is insufficient to distinguish investment from deterioration.

Until a deterministic classification rule is validated, capex intensity remains a quality modifier and confounder rather than a simple monotonic rank.

### 9.3 Cash-conversion diagnostics

`OP_CASH_CONVERSION`, `OP_FCF_CONVERSION`, and `OP_CFO_MARGIN` should be calculated when valid, but they are not additional independent sleeves in v0.1. They support review of the FCF-margin result and may trigger `MIXED` when accounting profit and cash generation materially diverge.

### 9.4 Gross margin

Gross margin is an industry-sensitive supplemental metric. It may replace part of the operating-margin sleeve only under a documented industry mapping. It cannot be added as a new independent margin family vote without changing the approved architecture.

## 10. Factor 4 — Acceleration and Persistence

**Factor weight:** 15% of `FastScore`  
**Purpose:** Measure whether comparable YoY operating evidence is strengthening or weakening through time.

Acceleration is defined as change in a YoY rate—not raw QoQ change.

### 10.1 Provisional sleeve mapping

| Sleeve | Component signals | Family | Weight within F4 |
|---|---|---|---:|
| Revenue acceleration | Quarter YoY acceleration and TTM YoY acceleration for revenue | `EF_GROWTH` | 25% |
| Profit acceleration | Quarter YoY acceleration and TTM YoY acceleration for operating income | `EF_PROFIT` | 30% |
| Cash acceleration | TTM YoY acceleration for CFO/FCF, using one family composite | `EF_CASH` | 15% |
| Margin acceleration | Change in operating-margin YoY improvement | `EF_MARGIN` | 15% |
| Persistence | Recent directionally aligned YoY history across eligible families | Cross-family | 15% |
| **Total** | | | **100%** |

### 10.2 Within-sleeve quarter/TTM blend

For revenue and operating-profit acceleration:

- latest-quarter YoY acceleration: provisional 60% of the sleeve;
- TTM YoY acceleration: provisional 40% of the sleeve.

This keeps the factor responsive while retaining TTM confirmation. The blend is provisional and must be sensitivity-tested.

### 10.3 Cash acceleration composite

Within the cash sleeve:

- CFO TTM acceleration: provisional 40%;
- FCF TTM acceleration: provisional 60%.

If the FCF growth base is unsuitable, use a validated margin/absolute alternate or rely on CFO alone within the sleeve subject to the reweighting cap. Quarterly cash acceleration remains diagnostic unless an industry rule approves it.

### 10.4 Persistence rule

The initial fixture calculation should record up to four consecutive quarterly YoY observations for each eligible family. Persistence should distinguish:

- consistently positive/improving;
- positive but slowing;
- neutral or alternating;
- negative but recovering; and
- consistently negative/deteriorating.

Exact numerical persistence weights and neutral bands remain `RESEARCH_REQUIRED`. Older observations must not overpower the latest quarter and TTM.

### 10.5 Acceleration guardrails

- Positive acceleration from a deeply negative level does not by itself imply strong recent performance.
- Negative acceleration from a high positive level may support `DECELERATING`, not necessarily `DETERIORATING`.
- A single acceleration signal cannot eliminate an otherwise scoreable company.
- Acceleration requires sufficient comparable history; missing history is not a zero acceleration score.

## 11. Factor 5 — Breadth and Consistency

**Factor weight:** 5% of `FastScore`  
**Purpose:** Measure agreement across independent families without double counting related metrics.

### 11.1 Eligible family votes

The breadth calculation considers:

1. `EF_GROWTH`
2. `EF_PROFIT`
3. `EF_CASH`
4. `EF_MARGIN`
5. `EF_PRODUCTIVITY`, when eligible
6. `EF_CAPITAL`, when a deterministic interpretation is available

### 11.2 Family classification

Each eligible family receives one directionally aligned classification:

- `SUPPORTIVE`
- `NEUTRAL`
- `ADVERSE`
- `CONFLICTED`
- `INELIGIBLE`

Multiple metrics inside a family are reconciled into this one classification. For example, CFO and FCF do not produce two breadth votes.

### 11.3 Provisional breadth calculation

For fixtures, record:

- supportive eligible families;
- adverse eligible families;
- conflicted eligible families;
- neutral eligible families; and
- total eligible families.

A provisional normalized breadth score may be tested using equal family influence, but the final formula and neutral bands remain `RESEARCH_REQUIRED`. `INELIGIBLE` families are excluded from the denominator and reduce `DataConfidence`; they are not adverse votes.

### 11.4 Mixed-evidence trigger

The following should trigger review for a possible `MIXED` status:

- growth and profit are supportive while cash is materially adverse;
- revenue is supportive while profit and margin are adverse;
- accounting profit improves while both CFO and FCF deteriorate materially;
- productivity appears supportive only because employee data are stale; or
- capital burden materially contradicts operating improvement.

The final `MIXED` threshold must be calibrated. The model must preserve the underlying disagreement even when a composite score is calculated.

## 12. Master Mapping Matrix

| Metric or signal | F1 TTM | F2 Quarter | F3 Quality | F4 Acceleration | F5 Breadth | Diagnostic |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| Revenue | Primary | Primary | — | Primary | Growth vote | Raw QoQ |
| Operating income | Primary | Primary | Supports operating leverage | Primary | Profit vote | Raw QoQ |
| EBIT | Alternate | Alternate | Alternate | Alternate | Same profit vote | Definition reconciliation |
| Gross profit | — | Conditional | Supports gross margin | Conditional research | Same profit vote | Industry context |
| CFO | Primary | — | Supports conversion review | TTM only | Cash vote | Standalone-quarter cash flow |
| Capex | Component | — | Conditional intensity | Through FCF/capex context | Capital vote when classifiable | Investment-cycle review |
| FCF | Primary | — | Through FCF margin | TTM only | Same cash vote | Standalone-quarter FCF |
| Operating margin | — | — | Primary | Primary | Margin vote | Level |
| FCF margin | — | — | Primary | Conditional | Cash/margin reconciliation | Level |
| CFO margin | — | — | Diagnostic support | — | Same cash vote | Level |
| Operating-leverage spread | — | — | Primary | Conditional | Same margin vote | — |
| Capex intensity | — | — | Conditional modifier | Conditional research | Capital vote when classifiable | Level and cycle |
| Revenue/employee | Productivity composite | — | Supports productivity | Conditional research | Productivity vote | Employee age |
| Operating income/employee | Productivity composite | — | Supports productivity | Conditional research | Same productivity vote | Employee age |
| FCF/employee | Diagnostic | — | Diagnostic | — | Same productivity/cash evidence | Employee age |
| Revenue growth minus employee growth | Productivity composite | — | Primary conditional | Conditional | Same productivity vote | Employee age |
| ROIC | Deferred | — | Deferred | Deferred | — | Research only |
| Raw sequential QoQ | — | — | — | — | — | Zero primary weight |

## 13. Alternate and Fallback Hierarchy

### 13.1 Profitability hierarchy

1. Use `OP_OPERATING_INCOME` when valid and consistent.
2. Use `OP_EBIT` only when operating income is unavailable or materially unsuitable and the EBIT definition is approved.
3. Do not use both as separate weighted evidence.
4. If neither is defensible, the standard module normally becomes `INSUFFICIENT_HISTORY` or `REVIEW_REQUIRED`.

### 13.2 Cash hierarchy

1. Use filed CFO.
2. Aggregate approved capex purchase concepts.
3. Derive FCF as CFO minus capex.
4. When capex mapping is unresolved, CFO may remain valid while FCF is excluded.
5. Do not substitute net income for CFO or FCF.

### 13.3 Productivity hierarchy

1. Use an observed, dated employee count.
2. Use a carried count only under an approved age rule.
3. If no valid count exists, use `NO_EMPLOYEE_SIGNAL`.
4. Do not impute employee counts from peers, revenue, or prior trends.

### 13.4 Industry-specific activity bases

An activity measure may replace revenue only through a documented industry rule that defines:

- the economic rationale;
- filed source and availability;
- comparable-period construction;
- directionality;
- peer-group scope;
- fallback behavior; and
- fixture evidence.

## 14. Double-Counting Rules

The following constraints are mandatory:

- Operating income and EBIT share one profit sleeve.
- CFO, FCF, CFO margin, FCF margin, and cash-conversion metrics share one cash family for breadth.
- Revenue growth and revenue per employee may enter different factors, but the productivity sleeve must explicitly account for the shared revenue numerator.
- Operating-income growth, operating margin, and operating leverage may enter different factors, but they share profitability information and cannot be treated as three independent breadth votes.
- FCF and FCF per employee cannot both receive full independent weight in F1.
- Gross profit and operating income are not automatically independent profit votes.
- A metric cannot be counted twice within the same factor unless the mapping explicitly separates level, change, and acceleration and the weights are capped.

## 15. Missing Data and Provisional Coverage Rules

Missing metrics are excluded with reason codes. They are never replaced with zero.

### 15.1 Factor scoreability floors for fixtures

The following are provisional test rules, not approved production thresholds:

| Factor | Provisional minimum evidence |
|---|---|
| `F1_TTM` | Valid revenue and operating-profit TTM signals plus at least one valid cash signal; at least 60% original within-factor weight available |
| `F2_QUARTER` | Valid revenue and operating-profit quarter YoY signals; at least 90% original weight available after approved gross-profit handling |
| `F3_QUALITY` | Valid operating-margin signal plus one independent cash, productivity, or capital-quality confirmation; at least 50% original weight available |
| `F4_ACCELERATION` | At least two independent eligible families with required history; at least 40% original weight available |
| `F5_BREADTH` | At least three eligible independent families |

### 15.2 Overall scoreability floor for fixtures

A provisional `FastScore` may be calculated only when:

- F1 and F2 meet their floors;
- F3 has a valid operating-margin anchor;
- at least two independent economic families are represented beyond raw revenue;
- no critical period, filing-date, unit, dimension, or sector gate is unresolved; and
- at least 70% of the original total metric weight is observable before any reweighting.

Failure of F4 because acceleration history is unavailable should normally produce `INSUFFICIENT_HISTORY` for the full score. A separate level-only diagnostic may be retained but must not be labeled the standard FastScore.

All numerical floors in this section are `PROVISIONAL_FIXTURE_RULES` and must be tested before approval.

## 16. Controlled Reweighting

### 16.1 Permitted reweighting

- Reweight only inside the same factor.
- Prefer direct economic substitutes inside the same sleeve or family.
- Do not transfer missing F4 acceleration weight into F1 or F2.
- Do not transfer missing employee productivity weight into unrelated cash or profit signals without a documented rule.
- Do not allow one remaining metric to represent an entire multi-family factor.

### 16.2 Provisional expansion cap

For fixture testing, no metric may exceed 125% of its original within-factor weight after redistribution, except the explicit F2 gross-profit fallback described below.

For F2 when gross profit is missing:

- revenue may increase from 45% to 50%;
- operating income may increase from 45% to 50%; and
- F2 may reach 100% coverage because the two required anchors remain.

This exception must be validated for industry bias.

### 16.3 Residual missing weight

When the expansion cap prevents full redistribution:

- do not treat residual weight as a zero metric score;
- compute the factor from eligible observed weights only if the factor floor is met;
- publish original coverage and post-reweighting coverage;
- reduce `DataConfidence`; and
- assign `PARTIAL` when missingness is meaningful.

The economic score and the evidence-coverage score remain separate.

## 17. Factor Calculation Record

For each factor, fixtures and future implementation must retain:

- original metric weights;
- metric eligibility states;
- exclusion reason codes;
- observed raw and directionally aligned signals;
- provisional normalized metric scores;
- applied post-reweighting weights;
- original-weight coverage;
- post-reweighting coverage;
- factor score;
- family representation;
- flags and reviewer notes; and
- mapping-version identifier.

## 18. DataConfidence Implications

This mapping does not finalize the `DataConfidence` formula. It identifies the conditions that must affect it:

- derived versus directly reported quarters;
- derived Q4;
- source authority and unresolved vendor dependence;
- missing factor sleeves;
- employee observation age;
- base-effect substitutions;
- extra-week or fiscal-calendar flags;
- acquisitions, divestitures, or discontinued-operation scope changes;
- taxonomy or dimension changes;
- conflicting direct and derived facts; and
- stale filings relative to the model date.

A low-quality strong signal cannot silently receive the same confidence as a fully filed, comparable signal.

## 19. Status Interpretation Support

The mapping supplies evidence to the `FastStatus` framework but does not replace it with simple score bands.

| Evidence pattern | Likely status candidate |
|---|---|
| Positive TTM and quarter evidence with broad positive acceleration | `ACCELERATING` |
| Positive or recovering TTM/quarter evidence without broad acceleration | `IMPROVING` |
| Results within calibrated neutral ranges | `STABLE` |
| Positive levels with weakening quarter/TTM rates | `DECELERATING` |
| Negative levels and direction across multiple families | `DETERIORATING` |
| Material conflict between growth, profit, cash, margin, or productivity | `MIXED` |
| Failed data or history requirements | `UNSCORED` |

Exact status thresholds remain outside this mapping until calibration.

## 20. Confounder Treatment

| Confounder | Mapping treatment |
|---|---|
| Acquisition | Construct valid reported periods; flag scope effect; use organic data only if filed consistently |
| Divestiture/discontinued operation | Use comparable continuing scope when defensible; otherwise exclude comparison |
| Restructuring | Preserve reported metric and flag material unusual costs |
| Working-capital timing | Prioritize TTM cash evidence; retain quarter cash diagnostics |
| Capex surge | Preserve FCF deterioration and capex-investment context; do not automatically reject issuer |
| Currency | Use reported results; constant-currency evidence is separate and cannot silently replace it |
| Extra fiscal week | Retain reported YoY comparison with flag; normalization is diagnostic only |
| Tax/accounting change | Affect only relevant metrics and confidence; no blanket override without evidence |

## 21. Fixture Calculation Requirements

For each Microsoft, Broadridge, and Walmart fixture date, calculate and retain:

### 21.1 Base periods

- eight comparable standalone quarters where available;
- current and prior-year TTM windows;
- filing/model-available dates;
- reported versus reconstructed origin; and
- as-filed vintage lineage.

### 21.2 Required metric signals

- revenue quarter YoY and TTM YoY;
- operating-income quarter YoY and TTM YoY;
- operating-margin quarter and TTM YoY change;
- CFO TTM YoY;
- capex TTM YoY and intensity change;
- FCF TTM YoY and FCF-margin change;
- revenue and operating-profit acceleration;
- cash acceleration when valid;
- employee metrics when eligible; and
- independent-family breadth classifications.

### 21.3 Mapping output

- F1–F5 eligibility;
- original coverage by factor;
- applied provisional weights;
- all excluded metrics and reasons;
- confounder flags;
- candidate `FastStatus` with rationale; and
- `DataStatus` and confidence inputs.

The fixtures must record calculations before comparison with any expected-result document.

## 22. Expected Fixture Behaviors

These expectations guide review but do not preassign scores.

### 22.1 Microsoft

Strong revenue, operating-profit, and CFO evidence combined with weaker FCF caused by substantially higher capex should remain visible as disagreement between operating and cash/investment sleeves. The company must not be automatically rejected, and the FCF weakness must not be hidden.

### 22.2 Broadridge

Seasonal cash flow should demonstrate why TTM cash evidence is primary and raw sequential cash changes are diagnostic. Strong annual/TTM confirmation should not be overturned by normal quarter-to-quarter timing.

### 22.3 Walmart

Modest revenue and operating-profit evidence with stronger CFO/FCF should produce a multifactor assessment. Working-capital and extra-week effects must remain visible where applicable.

## 23. Sensitivity Tests Before Approval

The provisional mapping must be tested against:

- removing the employee-productivity sleeve;
- replacing operating income with EBIT where permitted;
- excluding gross profit from F2;
- alternative cash-family weights;
- 100%, 125%, and 150% reweighting caps;
- different factor coverage floors;
- sign-changing CFO/FCF bases;
- high-capex technology and industrial companies;
- low-capex service companies;
- retailers with working-capital seasonality;
- 52/53-week issuers;
- acquisition-heavy companies; and
- negative-margin or early-recovery companies.

The mapping should be rejected or revised if small, economically immaterial input changes cause unstable score or status jumps.

## 24. Approval Decisions Required

| Decision | Proposed v0.1 rule | Status |
|---|---|---|
| Profit anchor | Operating income primary; EBIT alternate only | Proposed |
| F1 weights | 20% revenue, 25% operating profit, 15% CFO, 20% FCF, 20% productivity | Proposed |
| F2 weights | 45% revenue, 45% operating profit, 10% gross profit | Proposed |
| F3 weights | 30% operating margin, 20% FCF margin, 20% operating leverage, 15% workforce, 15% capex intensity | Proposed |
| F4 sleeves | 25% revenue, 30% profit, 15% cash, 15% margin, 15% persistence | Proposed |
| F5 basis | One vote per eligible independent family | Proposed |
| Quarterly cash flow | Diagnostic in F2 by default | Proposed |
| Employee sleeve | Conditional; missing is not zero | Proposed |
| ROIC | Deferred from v0.1 Fast composite | Proposed |
| Expansion cap | 125%, with explicit F2 gross-profit exception | Provisional fixture rule |
| Overall coverage floor | 70% original metric weight plus factor anchors | Provisional fixture rule |

Approval should be recorded in the Decision Register with the mapping version and any modifications.

## 25. Acceptance Criteria

This mapping is ready to become the fixture baseline when:

- the required anchors and alternates are approved;
- all provisional within-factor weights are accepted for research testing;
- the independent family boundaries are approved;
- double-count rules are accepted;
- provisional coverage and reweighting rules are accepted for fixtures;
- capex-intensity treatment is accepted as conditional rather than monotonic;
- ROIC deferral is approved; and
- fixture worksheets can reproduce every mapped input and exclusion.

Approval authorizes controlled fixture calculations and sensitivity analysis. It does not authorize production scoring thresholds or a live model.

## 26. Recommended Next Step

After approval, create `Operating_Company_Scoring_Fixture_Template.md`. The template should provide locked sections for:

- filing eligibility;
- source facts and quarter reconstruction;
- TTM and YoY calculations;
- metric eligibility and base-effect decisions;
- F1–F5 weights and coverage;
- score/status candidates;
- confidence inputs and data status;
- difference log; and
- reviewer sign-off.

The first completed templates should cover Microsoft, Broadridge, and Walmart before production code begins.

## 27. Revision History

| Version | Date | Change | Status |
|---|---|---|---|
| 0.1 | 2026-09-20 | Initial Operating Company metric-to-factor mapping | Draft for approval |

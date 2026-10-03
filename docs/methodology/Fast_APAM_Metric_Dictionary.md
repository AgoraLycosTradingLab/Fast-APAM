# Fast APAM Metric Dictionary

**Version:** 0.1  
**Status:** Draft for approval and fixture development  
**Companion documents:** `Fast_APAM_Scoring_and_Status_Specification.md`, `Period_Construction_Rules.md`, `Data_Contract.md`, and `Decision_Register.md`  
**Implementation status:** No production implementation authorized by this document

## 1. Purpose

This dictionary translates the approved Fast APAM scoring architecture into a controlled catalog of financial and operating metrics. It defines what each metric means, how it is constructed, which comparisons are valid, whether higher or lower values represent stronger evidence, where the metric enters the scoring architecture, and which safeguards must be applied.

Fast APAM remains a separate companion to Core APAM:

- Core APAM measures durable, multi-year business quality.
- Fast APAM detects recent acceleration, improvement, deceleration, or deterioration.
- Primary Fast APAM evidence comes from standalone-quarter year-over-year and trailing-twelve-month year-over-year comparisons.
- Raw sequential quarter-over-quarter changes are diagnostic only and receive zero primary scoring weight.
- Acceleration contributes to scoring and status classification but is not normally an elimination gate.

## 2. Scope and Approval Boundary

This document defines:

- canonical metric names and identifiers;
- formulas and source components;
- duration, instant, ratio, and per-share classifications;
- applicable comparison types;
- favorable direction;
- scoring-factor placement;
- sector-module applicability;
- missing-data and base-effect treatment;
- construction and comparability safeguards; and
- provisional versus approved metric status.

This document does not finalize:

- production weights within factor groups;
- peer-group definitions;
- winsorization thresholds;
- materiality bands;
- status thresholds;
- confidence penalties;
- employee carry-forward limits; or
- Financials and REIT production modules.

Those items remain subject to fixture testing, calibration, and Decision Register approval.

## 3. Metric Record Schema

Every metric definition must contain the following fields before it is eligible for implementation.

| Field | Required meaning |
|---|---|
| `metric_id` | Stable machine-readable identifier |
| `metric_name` | Human-readable name |
| `module` | Operating Company, Bank, Insurer, Asset Manager/Broker, or Equity REIT |
| `metric_family` | Independent economic family used for breadth and double-count control |
| `metric_class` | Duration, instant, ratio, margin, per-share, count, or derived signal |
| `canonical_formula` | Required economic definition |
| `source_components` | Required reported facts or company disclosures |
| `quarter_method` | Direct, cumulative reconstruction, recomputation, or not applicable |
| `ttm_method` | Four-quarter sum, recomputation, latest instant value, average balance, or not applicable |
| `comparison_method` | YoY percentage, percentage-point change, basis-point change, absolute change, or scaled change |
| `favorable_direction` | Higher, lower, conditional, or neutral diagnostic |
| `factor_placement` | TTM, latest quarter, quality, acceleration/persistence, breadth, or diagnostic only |
| `availability_class` | Filed statement, filing note, filed supplemental, or derived |
| `missing_rule` | Exclude, substitute approved alternate, or make module unscoreable |
| `base_effect_rule` | Standard percentage, alternate transformation, or exclusion |
| `quality_flags` | Metric-specific warnings or failure states |
| `approval_state` | Approved for fixtures, provisional, research required, or excluded |

## 4. Controlled Classifications

### 4.1 Metric classes

| Class | Definition | Period treatment |
|---|---|---|
| `DURATION` | Activity accumulated over a period | May be reconstructed and summed |
| `INSTANT` | Balance at a specific date | Never reconstructed by subtraction or summed across quarters |
| `MARGIN` | Numerator divided by a related revenue or activity base | Recompute from period-compatible components |
| `RATIO` | Relationship between two values | Recompute using compatible components or use valid disclosed ratio |
| `PER_SHARE` | Amount divided by weighted or ending shares | Do not reconstruct by subtracting cumulative per-share values |
| `COUNT` | Employees, customers, units, properties, or similar measure | Use observation date and staleness rules |
| `DERIVED_SIGNAL` | Growth, change, acceleration, persistence, or breadth | Calculate only from validated base metrics |

### 4.2 Availability classes

| Class | Source precedence |
|---|---|
| `FILED_STATEMENT` | SEC-filed primary financial statement |
| `FILED_NOTE` | SEC-filed footnote or table |
| `FILED_SUPPLEMENTAL` | Filed company schedule, reconciliation, or exhibit |
| `DERIVED` | Calculated from eligible filed components with retained lineage |
| `VENDOR_NORMALIZED` | Convenience layer only; reconcile material conflicts to filed data |

Fast APAM v1 uses filed information as the accounting truth layer. Earnings-release-only, transcript, estimate, guidance, and alternative-data metrics are outside the initial production-grade scope.

### 4.3 Factor identifiers

| Factor ID | Factor group | Initial model weight |
|---|---|---:|
| `F1_TTM` | TTM productivity and operating improvement | 35% |
| `F2_QUARTER` | Latest comparable-quarter YoY improvement | 25% |
| `F3_QUALITY` | Margin and capital or sector-quality confirmation | 20% |
| `F4_ACCELERATION` | Acceleration and persistence | 15% |
| `F5_BREADTH` | Breadth and consistency | 5% |
| `DIAGNOSTIC` | Context only | 0% |

These are research weights. The dictionary assigns metrics to factors but does not approve final within-factor weights.

## 5. Universal Signal Definitions

The following derived signals apply to eligible base metrics across modules.

| Metric ID | Name | Formula | Favorable direction | Primary placement | Safeguard |
|---|---|---|---|---|---|
| `SIG_Q_YOY_PCT` | Standalone-quarter YoY percentage change | `current quarter / prior-year comparable quarter - 1` | Depends on base metric | `F2_QUARTER` | Base must be suitable for percentage growth |
| `SIG_TTM_YOY_PCT` | TTM YoY percentage change | `current TTM / prior-year TTM - 1` | Depends on base metric | `F1_TTM` | Both TTM windows require four valid quarters |
| `SIG_Q_YOY_PP` | Quarter YoY percentage-point change | `current-quarter rate - prior-year comparable-quarter rate` | Depends on base metric | `F2_QUARTER` or `F3_QUALITY` | Use for margins, yields, occupancy, and rates |
| `SIG_TTM_YOY_PP` | TTM YoY percentage-point change | `current-TTM rate - prior-year-TTM rate` | Depends on base metric | `F1_TTM` or `F3_QUALITY` | Ratio must be recomputed consistently |
| `SIG_Q_ACCEL` | Quarter YoY acceleration | `current quarter YoY signal - preceding fiscal quarter YoY signal` | Positive after direction alignment | `F4_ACCELERATION` | Not raw QoQ growth |
| `SIG_TTM_ACCEL` | TTM YoY acceleration | `current TTM YoY signal - preceding fiscal quarter TTM YoY signal` | Positive after direction alignment | `F4_ACCELERATION` | Requires consecutive comparable TTM observations |
| `SIG_PERSISTENCE` | Directional persistence | Weighted recent history of directionally aligned YoY signals | Higher is stronger | `F4_ACCELERATION` | Initial window up to four quarters; calibration required |
| `SIG_BREADTH` | Independent-family breadth | Supporting eligible families divided by eligible independent families | Higher is stronger | `F5_BREADTH` | Correlated expressions of the same fact count once |
| `SIG_RAW_QOQ` | Raw sequential-quarter change | `current quarter / immediately prior quarter - 1` | Diagnostic only | `DIAGNOSTIC` | Zero primary weight because of seasonality |

### 5.1 Direction alignment

Before normalization, every signal is aligned so a higher value means stronger recent evidence. Metrics whose economic improvement is represented by a decline—such as the bank efficiency ratio, combined ratio, leverage, or credit losses—are directionally inverted for scoring while retaining their reported sign in the audit output.

### 5.2 Percentage-growth eligibility

Standard percentage growth is allowed only when:

- the denominator is economically meaningful;
- the current and comparison values share a defensible sign;
- the base is not immaterial or near zero;
- the concepts, units, dimensions, and consolidation scopes agree; and
- the periods are comparable.

Otherwise use an approved absolute, percentage-point, basis-point, or scaled change, or exclude the signal with `BASE_EFFECT`.

## 6. Common Period-Construction Rules

### 6.1 Duration metrics

- Q1 uses the valid three-month value.
- Q2 equals six-month cumulative value minus Q1 when a compatible direct quarter is unavailable.
- Q3 equals nine-month cumulative value minus six-month cumulative value when a compatible direct quarter is unavailable.
- Q4 equals annual value minus nine-month cumulative value.
- TTM equals four valid standalone quarters.

Every derived quarter retains both source facts, calculation lineage, validation status, and tolerances.

### 6.2 Instant metrics

Instant facts use the applicable balance-sheet or observation date. They are not subtracted to reconstruct quarters and are not summed to construct TTM. When an average balance is required, use an approved averaging method and disclose it.

### 6.3 Margins and ratios

Margins and ratios are recomputed from period-compatible numerator and denominator components whenever possible. Cumulative margins are not subtracted to produce standalone-quarter margins.

### 6.4 Per-share metrics

Cumulative EPS, FFO per share, AFFO per share, and similar measures must not be subtracted unless an explicit validated methodology accounts for weighted-average share differences. Prefer direct quarterly per-share disclosures or derive the aggregate numerator first and then divide by a compatible share measure.

### 6.5 Filing and restatement rule

No metric is available before the SEC acceptance timestamp plus the approved processing buffer. Historical model runs use the `AS_FILED` view. Later recasts or amendments enter only when actually available and remain separate in the `LATEST_RESTATED` view.

## 7. Operating Company Module

### 7.1 Applicability

This module applies to non-financial, non-REIT businesses for which revenue, operating income, operating cash flow, capital expenditure, margins, and capital efficiency are economically meaningful.

### 7.2 Core operating metrics

| Metric ID | Metric | Class | Canonical formula/source | Quarter and TTM treatment | Favorable direction | Families and factors | Status |
|---|---|---|---|---|---|---|---|
| `OP_REVENUE` | Revenue | `DURATION` | Consolidated revenue from continuing operations | Reconstruct quarter; sum four quarters for TTM | Higher YoY growth | Growth; `F1_TTM`, `F2_QUARTER`, `F4_ACCELERATION` | Approved for fixtures |
| `OP_GROSS_PROFIT` | Gross profit | `DURATION` | Revenue less cost of revenue, or valid reported gross profit | Reconstruct components consistently; sum TTM | Higher YoY growth | Profitability; `F1_TTM`, `F2_QUARTER` | Provisional by industry |
| `OP_OPERATING_INCOME` | Operating income | `DURATION` | Consolidated operating income from continuing operations | Reconstruct quarter; sum TTM | Higher YoY growth | Profitability; `F1_TTM`, `F2_QUARTER`, `F4_ACCELERATION` | Approved for fixtures |
| `OP_EBIT` | EBIT | `DURATION` | Approved EBIT definition used consistently across periods | Derive only from compatible components; sum TTM | Higher YoY growth | Profitability; alternate to operating income | Provisional alternate |
| `OP_CFO` | Cash flow from operations | `DURATION` | Net cash provided by operating activities | Reconstruct cumulative cash flow; sum TTM | Higher YoY growth | Cash generation; mainly `F1_TTM` | Approved for fixtures |
| `OP_CAPEX` | Capital expenditures | `DURATION` | Cash purchases of property/equipment plus approved capitalized asset additions | Reconstruct cumulative cash flow; sum TTM | Conditional | Investment intensity; `F3_QUALITY` or diagnostic | Approved with mapping review |
| `OP_FCF` | Free cash flow | `DURATION` | `CFO - capital expenditures` under one documented definition | Derive after standalone and TTM component construction | Higher YoY growth | Cash generation; `F1_TTM`, `F3_QUALITY`, `F4_ACCELERATION` | Approved for fixtures |
| `OP_EMPLOYEES` | Employee count | `COUNT` | Reported workforce count at disclosed observation date | No quarter subtraction or TTM sum; apply age class | Conditional denominator | Productivity; supports `F1_TTM`, `F3_QUALITY` | Provisional carry rules |
| `OP_INVESTED_CAPITAL` | Invested capital | `INSTANT` | Approved debt-plus-equity-less-nonoperating-cash definition | Use period-end or approved average balance | Lower for same operating output; conditional | Capital efficiency; `F3_QUALITY` | Research required |

### 7.3 Operating margins and cash-quality metrics

| Metric ID | Metric | Formula | Comparison | Favorable direction | Factor | Key safeguard |
|---|---|---|---|---|---|---|
| `OP_GROSS_MARGIN` | Gross margin | `gross profit / revenue` | YoY percentage-point change for quarter and TTM | Higher | `F3_QUALITY` | Recompute from compatible components |
| `OP_OPERATING_MARGIN` | Operating margin | `operating income / revenue` | YoY percentage-point change for quarter and TTM | Higher | `F3_QUALITY`, acceleration derivative | Preserve negative-margin base flags |
| `OP_FCF_MARGIN` | FCF margin | `FCF / revenue` | YoY percentage-point change, principally TTM | Higher | `F3_QUALITY` | Use consistent FCF definition |
| `OP_CFO_MARGIN` | CFO margin | `CFO / revenue` | YoY percentage-point change, principally TTM | Higher | `F3_QUALITY` | Seasonal working capital may distort quarter |
| `OP_CAPEX_INTENSITY` | Capex intensity | `capex / revenue` | YoY percentage-point change | Conditional | `F3_QUALITY` or diagnostic | Rising capex may represent investment, not deterioration |
| `OP_CASH_CONVERSION` | Cash conversion | `CFO / operating income` or approved alternate | TTM level and YoY change | Generally higher within valid ranges | `F3_QUALITY` | Invalid around zero/negative operating income |
| `OP_FCF_CONVERSION` | FCF conversion | `FCF / operating income` or approved alternate | TTM level and YoY change | Generally higher within valid ranges | `F3_QUALITY` | Base effects and capex cycles require flags |

### 7.4 Productivity metrics

| Metric ID | Metric | Formula | Comparison | Favorable direction | Factor | Employee requirement |
|---|---|---|---|---|---|---|
| `OP_REVENUE_PER_EMPLOYEE` | Revenue per employee | `TTM revenue / employee count` | TTM YoY percentage change | Higher | `F1_TTM`, `F3_QUALITY` | Observed or valid carried count |
| `OP_OPERATING_INCOME_PER_EMPLOYEE` | Operating income per employee | `TTM operating income / employee count` | TTM YoY percentage or scaled change | Higher | `F1_TTM`, `F3_QUALITY` | Observed or valid carried count; base-effect protection |
| `OP_FCF_PER_EMPLOYEE` | FCF per employee | `TTM FCF / employee count` | TTM YoY percentage or scaled change | Higher | `F1_TTM`, `F3_QUALITY` | Observed or valid carried count; base-effect protection |
| `OP_REVENUE_GROWTH_MINUS_EMPLOYEE_GROWTH` | Revenue–employee growth spread | `TTM revenue YoY - employee-count YoY` | Percentage-point spread | Higher | `F3_QUALITY`, `F4_ACCELERATION` | Both observations must be valid and dated |
| `OP_OPERATING_LEVERAGE_SPREAD` | Operating leverage spread | `operating-income YoY - revenue YoY` | Percentage-point spread | Higher | `F3_QUALITY`, `F4_ACCELERATION` | Invalid if profit base changes sign without alternate rule |

Employee classifications are:

- `OBSERVED_EMPLOYEE`: timely disclosed count;
- `CARRIED_EMPLOYEE`: prior count carried under an approved maximum age, with reduced weight/confidence; and
- `NO_EMPLOYEE_SIGNAL`: employee metrics excluded without substituting zero.

The employee age-decay schedule remains `RESEARCH_REQUIRED`.

### 7.5 Capital-efficiency metrics

| Metric ID | Metric | Formula | Comparison | Favorable direction | Factor | Status |
|---|---|---|---|---|---|---|
| `OP_ROIC` | Return on invested capital | `NOPAT / average invested capital` | TTM level and YoY percentage-point change | Higher | `F3_QUALITY` | Research required definition |
| `OP_INCREMENTAL_ROIC` | Incremental return on capital | `change in NOPAT / change in invested capital` | Multi-observation or TTM change | Higher when denominator meaningful | `F3_QUALITY` | Deferred pending stability tests |
| `OP_ASSET_TURNOVER` | Asset turnover | `TTM revenue / average assets` | YoY change | Higher, industry dependent | `F3_QUALITY` | Provisional |
| `OP_WORKING_CAPITAL_EFFICIENCY` | Working-capital efficiency | Approved cash-conversion-cycle or revenue/net-working-capital measure | YoY change | Conditional | `F3_QUALITY` | Industry-specific and research required |

ROIC and working-capital definitions must remain consistent with Core APAM where possible. Any deliberate difference requires a Decision Register entry.

### 7.6 Operating-company alternates and exclusions

| Situation | Approved handling |
|---|---|
| Revenue unavailable or economically misleading | Use an approved industry-specific activity base only after module approval |
| Operating income unavailable | Use approved EBIT alternate; do not count both as independent evidence |
| FCF negative or sign-changing | Use margin/absolute/scaled change with `BASE_EFFECT`; do not force percentage growth |
| Capex taxonomy fragmented | Aggregate only approved purchase concepts; retain component lineage |
| Acquisitions materially alter scope | Flag `ACQUISITION_EFFECT`; organic evidence used only if filed and consistently defined |
| Divestiture or discontinued operations | Use continuing-operation scope where defensible; otherwise exclude affected comparison |
| Fiscal extra week | Keep reported result primary, flag it, and use duration-normalized data only as diagnostic sensitivity |

## 8. Bank Module

**Module status:** Provisional; no production Bank FastScore until the submodule and fixtures are approved.

Industrial-company revenue, FCF, and ROIC metrics are not mechanically applicable to banks.

| Metric ID | Metric | Class/formula | Primary comparison | Favorable direction | Family and factor | Principal safeguards |
|---|---|---|---|---|---|---|
| `BK_NET_INTEREST_INCOME` | Net interest income | `DURATION`; reported taxable-equivalent basis only if consistent | Quarter and TTM YoY | Higher | Earnings; `F1_TTM`, `F2_QUARTER` | Maintain basis consistency |
| `BK_NET_INTEREST_MARGIN` | Net interest margin | `RATIO`; disclosed NIM | Quarter and TTM YoY bp change | Higher | Spread quality; `F3_QUALITY` | Average earning-asset basis must be comparable |
| `BK_NONINTEREST_INCOME` | Noninterest income | `DURATION`; approved fee and other income scope | Quarter and TTM YoY | Higher, with quality review | Fee earnings; `F1_TTM`, `F2_QUARTER` | Securities gains and unusual items flagged |
| `BK_NONINTEREST_EXPENSE` | Noninterest expense | `DURATION` | Quarter and TTM YoY relative to revenue | Lower for equal output | Efficiency; `F3_QUALITY` | Restructuring and FDIC assessments flagged |
| `BK_EFFICIENCY_RATIO` | Efficiency ratio | Disclosed or consistently derived expenses/revenue | YoY bp change | Lower | Efficiency; `F3_QUALITY`, `F4_ACCELERATION` | Definition must be stable |
| `BK_PREPROVISION_NET_REVENUE` | Pre-provision net revenue | Approved revenue less noninterest expense definition | Quarter and TTM YoY | Higher | Operating strength; `F1_TTM`, `F2_QUARTER` | Definition reconciliation required |
| `BK_LOANS` | Loans | `INSTANT`; period-end or approved average loans | YoY growth | Conditional positive | Balance-sheet growth; quality confirmation | Acquisition and runoff effects flagged |
| `BK_DEPOSITS` | Deposits | `INSTANT`; period-end or approved average deposits | YoY growth and mix change | Conditional positive | Funding; `F3_QUALITY` | Brokered/uninsured/high-cost mix matters |
| `BK_DEPOSIT_COST` | Cost of deposits | `RATIO` | YoY bp change | Lower, conditional on rate cycle | Funding quality; `F3_QUALITY` | Rate environment required for interpretation |
| `BK_NET_CHARGE_OFF_RATE` | Net charge-off rate | Net charge-offs / average loans | YoY bp change | Lower | Credit quality; `F3_QUALITY` | Portfolio-mix changes flagged |
| `BK_NPA_RATIO` | Nonperforming asset ratio | Nonperforming assets / loans or assets | YoY bp change | Lower | Credit quality; `F3_QUALITY` | Denominator consistency required |
| `BK_PROVISION` | Credit-loss provision | `DURATION` | YoY change scaled by average loans | Lower deterioration, conditional | Credit quality; `F3_QUALITY` | Reserve builds can be prudent rather than purely negative |
| `BK_CET1_RATIO` | CET1 capital ratio | `RATIO` | YoY bp change and level | Higher within efficient range | Capital; `F3_QUALITY` | Standardized/advanced basis consistency |
| `BK_TBVPS` | Tangible book value per share | `PER_SHARE` | YoY change | Higher | Capital compounding; `F1_TTM`, `F3_QUALITY` | Share issuance and OCI effects flagged |
| `BK_ROTCE` | Return on tangible common equity | `RATIO` | TTM level and YoY pp change | Higher | Return quality; `F3_QUALITY` | Tangible equity definition consistent |

Bank breadth should count earnings, efficiency, funding, credit, and capital as separate families. Multiple credit ratios do not each count as independent breadth confirmation.

## 9. Insurer Module

**Module status:** Provisional; property/casualty, life, and health insurers may require distinct mappings.

| Metric ID | Metric | Class/formula | Primary comparison | Favorable direction | Family and factor | Principal safeguards |
|---|---|---|---|---|---|---|
| `IN_PREMIUMS` | Premiums or premium equivalent | `DURATION`; approved written/earned basis | Quarter and TTM YoY | Higher with pricing/retention context | Growth; `F1_TTM`, `F2_QUARTER` | Written and earned bases not mixed |
| `IN_UNDERWRITING_INCOME` | Underwriting income | `DURATION` | Quarter and TTM YoY or scaled change | Higher | Underwriting; `F1_TTM`, `F2_QUARTER` | Sign changes require base protection |
| `IN_COMBINED_RATIO` | Combined ratio | `RATIO` | Quarter and TTM YoY bp change | Lower | Underwriting quality; `F3_QUALITY`, `F4_ACCELERATION` | Definition and catastrophe treatment consistent |
| `IN_LOSS_RATIO` | Loss ratio | `RATIO` | YoY bp change | Lower | Claims quality; `F3_QUALITY` | Prior-year development isolated where possible |
| `IN_EXPENSE_RATIO` | Expense ratio | `RATIO` | YoY bp change | Lower | Efficiency; `F3_QUALITY` | Acquisition-cost accounting consistency |
| `IN_RESERVE_DEVELOPMENT` | Reserve development | Favorable/adverse development scaled to premiums or reserves | YoY/TTM comparison | More favorable, but persistent releases flagged | Reserve quality; `F3_QUALITY` | Releases are not automatically operating acceleration |
| `IN_CATASTROPHE_LOSS` | Catastrophe loss burden | Cat losses / earned premiums | YoY pp change | Lower, treated as confounder | Diagnostic/quality | Geographic and event variation disclosed |
| `IN_NET_INVESTMENT_INCOME` | Net investment income | `DURATION` | Quarter and TTM YoY | Higher | Investment contribution; `F1_TTM`, `F2_QUARTER` | Market and portfolio-yield effects flagged |
| `IN_BOOK_VALUE_PS` | Book value per share | `PER_SHARE` | YoY change | Higher | Capital compounding; `F1_TTM`, `F3_QUALITY` | AOCI basis must be explicit |
| `IN_OPERATING_ROE` | Operating return on equity | `RATIO` | TTM level and YoY pp change | Higher | Return quality; `F3_QUALITY` | Company-defined adjustments reconciled |
| `IN_CAPITAL_ADEQUACY` | Regulatory capital adequacy | Applicable filed ratio | YoY change and level | Higher within efficient range | Capital; `F3_QUALITY` | Jurisdiction/product mapping required |

Catastrophe losses, reserve changes, reinsurance changes, and accounting transitions receive explicit flags rather than opaque overrides.

## 10. Asset Manager and Broker Module

**Module status:** Provisional; pure asset managers and capital-markets brokers may require different weighting.

| Metric ID | Metric | Class/formula | Primary comparison | Favorable direction | Family and factor | Principal safeguards |
|---|---|---|---|---|---|---|
| `AM_AUM` | Assets under management | `INSTANT`; ending or average AUM | YoY growth | Higher, with source attribution | Scale; `F1_TTM`, `F2_QUARTER` | Separate markets, FX, acquisitions, and flows |
| `AM_NET_FLOWS` | Net client flows | `DURATION` | Quarter and TTM; scaled to beginning AUM | Higher | Organic growth; `F1_TTM`, `F2_QUARTER` | Definitions consistent by product |
| `AM_ORGANIC_GROWTH_RATE` | Organic growth rate | Net flows / beginning AUM | YoY pp change and level | Higher | Organic growth; `F3_QUALITY` | Acquired flows excluded |
| `AM_FEE_REVENUE` | Management/advisory fee revenue | `DURATION` | Quarter and TTM YoY | Higher | Revenue; `F1_TTM`, `F2_QUARTER` | Performance fees separated where material |
| `AM_FEE_RATE` | Effective fee rate | Fee revenue / average AUM | YoY bp change | Higher, conditional on mix | Pricing quality; `F3_QUALITY` | Product mix effects flagged |
| `AM_COMP_RATIO` | Compensation ratio | Compensation expense / net revenue | YoY pp change | Lower | Efficiency; `F3_QUALITY` | Broker and asset-manager bases may differ |
| `AM_OPERATING_MARGIN` | Operating or pre-tax margin | Approved numerator / net revenue | Quarter and TTM YoY pp change | Higher | Profitability; `F3_QUALITY` | Adjusted definitions reconciled |
| `AM_TRANSACTION_REVENUE` | Transaction revenue | `DURATION` | Quarter and TTM YoY | Higher but cyclical | Activity; `F1_TTM`, `F2_QUARTER` | Market-volume dependence flagged |
| `AM_CLIENT_ASSETS` | Client assets | `INSTANT` | YoY growth | Higher | Scale; alternate | Avoid double counting with AUM |
| `AM_EXCESS_CAPITAL_LIQUIDITY` | Capital/liquidity measure | Filed applicable measure | YoY change and level | Higher within efficient range | Capital; `F3_QUALITY` | Regulatory/business model context required |

Market appreciation must not be treated as equivalent to organic growth. When flow attribution is unavailable, AUM growth receives reduced confirmation and may support `MIXED` rather than `ACCELERATING`.

## 11. Equity REIT Module

**Module status:** Provisional. Mortgage REITs are excluded pending a separate approved methodology.

| Metric ID | Metric | Class/formula | Primary comparison | Favorable direction | Family and factor | Principal safeguards |
|---|---|---|---|---|---|---|
| `RE_SAME_STORE_NOI` | Same-store NOI growth | Company-defined comparable-property NOI growth | Quarter and TTM YoY | Higher | Property operations; `F1_TTM`, `F2_QUARTER` | Pool definition and acquisitions consistent |
| `RE_NOI_MARGIN` | NOI margin | Property NOI / property revenue | YoY pp change | Higher | Property quality; `F3_QUALITY` | Definition consistent |
| `RE_FFO` | Funds from operations | Nareit or reconciled company definition | Quarter and TTM YoY | Higher | Earnings; `F1_TTM`, `F2_QUARTER` | Definition changes reconciled |
| `RE_FFO_PER_SHARE` | FFO per diluted share | Valid direct disclosure or aggregate FFO / compatible shares | Quarter and TTM YoY | Higher | Per-share earnings; `F1_TTM`, `F2_QUARTER` | Do not subtract cumulative per-share values |
| `RE_AFFO` | Adjusted FFO | Consistently reconciled company definition | Quarter and TTM YoY | Higher | Recurring cash earnings; `F1_TTM` | Adjustment consistency required |
| `RE_AFFO_PER_SHARE` | AFFO per diluted share | Valid direct disclosure or aggregate AFFO / compatible shares | Quarter and TTM YoY | Higher | Per-share cash earnings; `F1_TTM`, `F2_QUARTER` | Dilution and definition changes flagged |
| `RE_OCCUPANCY` | Occupancy | Leased or economic occupancy, consistently defined | YoY pp change | Higher | Demand quality; `F3_QUALITY` | Physical/economic occupancy not mixed |
| `RE_LEASING_SPREAD` | Leasing spread | Cash or GAAP rent change on comparable renewals/new leases | YoY pp change and level | Higher | Pricing; `F3_QUALITY`, `F4_ACCELERATION` | New/renewal and cash/GAAP definitions retained |
| `RE_GA_EFFICIENCY` | G&A efficiency | G&A / revenue, NOI, or assets under approved property-type rule | YoY pp change | Lower | Efficiency; `F3_QUALITY` | Denominator consistent |
| `RE_RECURRING_CAPEX` | Recurring capital expenditures | Filed recurring/maintenance capital expenditure | TTM YoY and intensity | Lower for equal NOI, conditional | Capital burden; `F3_QUALITY` | Development capex separated |
| `RE_NET_DEBT_EBITDA` | Net debt to EBITDAre | Filed or consistently derived leverage ratio | YoY change and level | Lower | Leverage; `F3_QUALITY` | EBITDAre and debt definitions consistent |
| `RE_FIXED_CHARGE_COVERAGE` | Fixed-charge coverage | Approved filed definition | YoY change and level | Higher | Debt service; `F3_QUALITY` | Definition consistency required |
| `RE_INTEREST_BURDEN` | Interest burden | Interest expense / NOI, EBITDAre, or revenue under approved rule | YoY pp change | Lower | Financing quality; `F3_QUALITY` | Capitalized interest and refinancing effects flagged |
| `RE_DEBT_MATURITY_RISK` | Near-term debt maturity burden | Debt due within approved horizon / total debt or liquidity | YoY change and level | Lower | Liquidity; `F3_QUALITY` | Horizon requires approval |
| `RE_EXTERNAL_GROWTH_SHARE` | Acquisition/development contribution | Disclosed external contribution to NOI/earnings | Diagnostic or scaled | Conditional | Confounder/diagnostic | Separates same-store from acquisition growth |

REIT breadth should distinguish property operations, per-share earnings, leasing/occupancy, expense efficiency, and balance-sheet quality. Aggregate growth without per-share confirmation must not automatically qualify as broad improvement.

## 12. Independent Metric Families and Double-Count Control

Breadth is measured across independent economic families, not the raw number of metrics.

### 12.1 Operating companies

1. Revenue/activity growth
2. Operating profitability
3. Cash generation
4. Employee productivity
5. Margin quality
6. Capital efficiency

Examples of non-independent pairs:

- operating income and EBIT when definitions substantially overlap;
- CFO and CFO margin;
- FCF and FCF margin;
- revenue per employee and revenue-growth-minus-employee-growth; and
- several margin expressions driven by the same numerator.

### 12.2 Sector modules

- Banks: earnings, efficiency, funding, credit, and capital.
- Insurers: premium growth, underwriting, reserves/catastrophes, investment contribution, and capital.
- Asset managers/brokers: organic flows, asset scale, fee economics, operating efficiency, and capital.
- REITs: same-store operations, per-share earnings, leasing/occupancy, recurring capital burden, and leverage/liquidity.

Within-family metrics may improve robustness but cannot each receive an independent breadth vote.

## 13. Missing Data and Substitution Rules

### 13.1 General rule

Missing data are not zero and are not imputed from peers. Each missing item receives a reason code and is excluded or replaced only by an approved economic alternate.

### 13.2 Approved alternate relationships

| Primary metric | Possible alternate | Constraint |
|---|---|---|
| Operating income | EBIT | Use one, not both as independent evidence; definitions must be consistent |
| Gross profit | Revenue plus cost of revenue | Derive only when scope and signs reconcile |
| FCF | CFO minus approved capex aggregation | Required components must be valid |
| Direct standalone duration value | Compatible cumulative-period subtraction | Period rules and identities must pass |
| Direct Q4 duration value | Annual minus nine-month total | Annual and nine-month bases must be compatible |
| Employee productivity | None | If employee count is invalid, use `NO_EMPLOYEE_SIGNAL` |
| Same-store NOI | None from generic revenue | Exclude rather than fabricate property comparability |
| Bank organic funding quality | Deposit mix measures | Only if filed and consistently defined |

### 13.3 Missing reason codes

- `NOT_YET_AVAILABLE`
- `CONCEPT_UNMAPPED`
- `DERIVATION_FAILED`
- `PERIOD_INCOMPARABLE`
- `QUALITY_REJECTED`
- `CONFLICT_UNRESOLVED`
- `INSUFFICIENT_HISTORY`
- `SECTOR_NOT_APPLICABLE`
- `BASE_EFFECT`
- `STALE_DENOMINATOR`

## 14. Metric-Level Quality Flags

| Flag | Meaning | Normal treatment |
|---|---|---|
| `DERIVED_QUARTER` | Quarter reconstructed from cumulative facts | Retain with lineage; confidence treatment pending calibration |
| `DERIVED_Q4` | Q4 calculated from annual minus nine-month total | Retain if identities pass |
| `RESTATED` | Value changed by later filing | Keep as-filed and latest-restated views separate |
| `TAXONOMY_CHANGE` | Concept or mapping changed | Reconcile or review |
| `DIMENSION_CHANGE` | Segment/geography/product dimensions changed | Use consolidated compatible facts or exclude |
| `UNIT_MISMATCH` | Units differ or cannot be reconciled | Hard failure until resolved |
| `BASE_EFFECT` | Percentage change is unstable or misleading | Use approved alternate or exclude |
| `SIGN_CHANGE` | Current/comparison value crosses zero | Do not use ordinary percentage growth |
| `EXTRA_WEEK` | 52/53-week difference affects duration | Flag; normalized sensitivity remains diagnostic |
| `STUB_PERIOD` | Transition or shortened period | Usually `PERIOD_INCOMPARABLE` |
| `ACQUISITION_EFFECT` | Scope changed materially through acquisition | Preserve flag; organic evidence only if filed consistently |
| `DIVESTITURE_EFFECT` | Scope changed through disposal | Use continuing scope if defensible |
| `ONE_TIME_ITEM` | Material unusual item | Preserve reported result and flag; adjustment requires policy |
| `WORKING_CAPITAL_TIMING` | Cash flow affected by timing | TTM priority; do not discard valid result |
| `CAPEX_CYCLE` | FCF affected by unusual investment cycle | Preserve economic divergence and flag |
| `CARRIED_EMPLOYEE` | Workforce count carried from earlier disclosure | Reduce employee-signal confidence/weight under future rule |
| `VENDOR_ONLY` | No filed-source confirmation | Lower confidence or exclude under source policy |
| `DEFINITION_CHANGE` | Non-GAAP/sector metric definition changed | Reconcile or exclude comparison |

Quality flags describe evidence; they do not automatically erase economically unfavorable observations.

## 15. Metrics Excluded from Primary Scoring

The following are excluded from primary v1 scoring unless a later approved module changes their treatment:

| Metric or method | Reason |
|---|---|
| Raw sequential-quarter growth | Seasonality; diagnostic only |
| Quarterly employee productivity using an invented quarterly headcount | False precision |
| Cumulative margin subtraction | Mathematically invalid construction |
| Summed balance-sheet values | Instant facts are not duration flows |
| Cumulative EPS subtraction | Weighted-average share bases differ |
| Generic FCF for banks and insurers | Does not represent sector economics reliably |
| Generic industrial ROIC for Financials | Capital is operating input and regulated differently |
| GAAP net income as the primary REIT operating measure | Property sales and depreciation reduce comparability |
| Market-price momentum | Outside filed-fundamentals Fast APAM scope |
| Analyst estimates and guidance | Deferred, separately timestamped layer |
| AI narrative or attribution | Separate attribution layer; not proof of measured productivity |

## 16. Metric Approval States

| State | Meaning |
|---|---|
| `APPROVED_FOR_FIXTURES` | May be used in hand calculations and controlled test fixtures |
| `PROVISIONAL` | Definition is useful but requires methodology or calibration approval |
| `RESEARCH_REQUIRED` | Material definition or data-coverage question remains |
| `EXCLUDED_V1` | Not part of initial model |
| `APPROVED_PRODUCTION` | Available only after validation and Decision Register approval |

No metric in this v0.1 dictionary is automatically `APPROVED_PRODUCTION`.

## 17. Initial Operating-Company Fixture Set

The first metric calculations should focus on the following minimum operating-company set:

| Priority | Metric | Required outputs |
|---:|---|---|
| 1 | Revenue | Standalone quarter, TTM, quarter YoY, TTM YoY, acceleration |
| 2 | Operating income | Standalone quarter, TTM, quarter YoY, TTM YoY, acceleration |
| 3 | Operating margin | Quarter and TTM level, YoY pp change, acceleration |
| 4 | CFO | Standalone quarter, TTM, quarter diagnostic, TTM YoY |
| 5 | Capex | Standalone quarter, TTM, intensity, flags |
| 6 | FCF | Standalone quarter, TTM, TTM YoY, FCF margin, acceleration |
| 7 | Employee count | Observation value/date, quality class, age |
| 8 | Revenue per employee | TTM level and YoY change when eligible |
| 9 | Operating income per employee | TTM level and YoY/alternate change when eligible |
| 10 | Revenue–employee growth spread | TTM growth spread when eligible |

Microsoft, Broadridge, and Walmart should be used to verify that the dictionary captures respectively:

- strong operating evidence with FCF/capex divergence;
- seasonal cash flow where TTM is more reliable than sequential change; and
- modest accounting-profit growth with stronger cash generation and possible calendar/working-capital effects.

No expected score or status should be assigned merely from these qualitative expectations.

## 18. Required Metric Audit Output

Each calculated metric must retain:

- `metric_id` and dictionary version;
- module and metric family;
- current and comparison period identifiers;
- raw source values;
- filing accession numbers and acceptance timestamps;
- source concepts, units, dimensions, and consolidation scope;
- reported versus derived classification;
- standalone-quarter and TTM construction details;
- comparison transformation;
- raw signal and directionally aligned signal;
- normalization method and peer group when introduced;
- original and applied weights when introduced;
- employee quality class where relevant;
- missing reason or quality flags;
- as-filed/restated view; and
- reviewer or automated process identifier.

## 19. Decisions Required Before Coding the Scoring Engine

The period engine may be prototyped only after its existing validation gate is satisfied. Before coding the composite scoring engine, approve:

1. the operating-company minimum metric set;
2. operating income versus EBIT precedence;
3. capex and FCF canonical definitions;
4. employee-count maximum age and decay schedule;
5. ROIC definition and whether it enters Fast APAM v1;
6. materiality and base-effect thresholds;
7. approved sector/industry alternates;
8. minimum factor coverage and reweighting caps;
9. peer-group and normalization rules; and
10. which sector modules enter the first release.

## 20. Recommended Next Development Step

After approval of this dictionary, create `Operating_Company_Metric_to_Factor_Mapping.md`. That document should:

- choose the v0.1 operating-company metric subset;
- prevent double counting within families;
- assign provisional within-factor weights;
- specify fallback alternates;
- define minimum coverage by factor;
- identify required fixture calculations; and
- leave empirical thresholds clearly marked for calibration.

## 21. Revision History

| Version | Date | Change | Status |
|---|---|---|---|
| 0.1 | 2026-09-19 | Initial cross-module metric dictionary | Draft for approval |

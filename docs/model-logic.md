# Model logic

Fast APAM measures recent business direction using filed financial information. Core APAM remains the separate annual-quality model. This guide summarizes the [scoring specification](methodology/Fast_APAM_Scoring_and_Status_Specification.md), [metric mapping](methodology/Operating_Company_Metric_to_Factor_Mapping.md), [metric dictionary](methodology/Fast_APAM_Metric_Dictionary.md), [normalization rules](methodology/Fast_APAM_Provisional_Normalization_and_Thresholds.md), and [decision register](methodology/Decision_Register.md). Those documents and each snapshot's recorded policy remain authoritative.

## Comparable periods

For additive flow metrics, Q1 usually uses the reported quarter. Q2 can be six-month cumulative less Q1; Q3 can be nine-month cumulative less six-month cumulative; Q4 can be annual less nine-month cumulative. TTM combines four validated standalone quarters. Ratios are recalculated from their components. Balance-sheet snapshots are not summed as flows.

Primary changes compare a fiscal quarter with its comparable prior-year quarter, or TTM with comparable prior-year TTM. Raw sequential QoQ changes are diagnostic and receive zero primary weight. Acceleration measures changes in YoY performance rather than raw sequential changes in financial amounts.

FCF is cash from operations less capital expenditures when periods, units, scope and availability are compatible. Percentage growth requires a positive comparison base. Zero or negative bases use only the approved absolute-change fallback when eligible; fallback observations remain separately identified.

## Research factor architecture

| Factor | Initial research weight |
|---|---:|
| TTM productivity and operating improvement | 35% |
| Latest comparable-quarter YoY improvement | 25% |
| Margin and capital or sector-quality confirmation | 20% |
| Acceleration and persistence | 15% |
| Breadth and consistency | 5% |

These are research weights, not finalized production parameters. Missing metrics follow recorded coverage and reweighting rules; they are never replaced with zero or silently redistributed across unrelated factors. Employee and conditional capex signals may be unavailable in a publishable partial result.

## Peers and interpretation

Score measures relative recent strength. Trend status summarizes direction and momentum. Confidence describes input quality separately. A strong relative score may coexist with slowing momentum.

Requested tickers and normalization peers serve different purposes. A small watchlist cannot automatically supply the peer distribution. The tested pilot uses governed dated IT-sector evidence and per-metric coverage gates. Other sectors and arbitrary universes are not established by this pilot.

## Availability and audit trail

The model date determines which information may be used; period end is not filing availability. Preserve acceptance timestamps, the prescribed trading-day buffer, fiscal alignment, restatement views, source parents, units, construction methods, quality/fallback flags and reasons. See the [Data Contract](methodology/Data_Contract.md) and [period rules](methodology/Period_Construction_Rules.md).

Unresolved conflicts, incomparable periods, failed accounting identities, insufficient history or coverage can withhold scores. Weak economics alone does not justify exclusion. The validated snapshots use latest-restated information available at their model dates; reproduction does not establish a historical as-filed backtest.

Fast APAM does not calculate fair value, entry price, expected stock return, or investability status.

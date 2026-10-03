# Microsoft Dated GICS and Peer-Hierarchy Decision

**Decision ID:** `FAST-APAM-GICS-001`  
**Target company:** Microsoft Corporation (`MSFT`; CIK `0000789019`)  
**Model date:** 2026-07-31  
**Prepared:** 2026-09-20  
**Status:** `AWAITING APPROVAL`  
**Recommended decision:** Approve a limited sector-level pilot exception; retain licensed historical GICS as the production requirement.

## 1. Decision required

Fast APAM requires the narrowest dated peer group that satisfies the approved observation hierarchy:

| Peer level | Minimum eligible observations | Extraction target with 10% reserve |
|---|---:|---:|
| GICS sub-industry | 15 | 17 |
| GICS industry | 25 | 28 |
| GICS industry group | 35 | 39 |
| GICS sector | 50 | 55 |

Microsoft's Information Technology sector membership is now supported by dated regulatory evidence. Its July 31 industry group, industry, and sub-industry assignments are not yet supported by a licensed historical GICS delivery.

The decision is whether to:

1. pause the pilot until licensed historical GICS is acquired;
2. approve a limited sector-level normalization pilot using the dated, validated Information Technology basket; or
3. permit an analyst-assigned lower-level proxy.

## 2. Evidence established

The June 30, 2026 SEC N-PORT filing for the State Street Technology Select Sector SPDR ETF identifies:

- series `S000006415`;
- portfolio date June 30, 2026;
- 74 common-equity positions; and
- Microsoft as a portfolio security.

The 74 N-PORT positions reconcile one-for-one with the 74 securities classified as Information Technology in the corrected July 31 S&P 500 candidate. No S&P 500 membership change effective from July 1 through July 31 was identified.

This establishes a dated sector-level Microsoft peer universe without backfilling the September sector labels.

## 3. Classification record

| Level | Proposed value | Evidence status | Allowed use |
|---|---|---|---|
| Sector | Information Technology | `DATED_CONFIRMED` | Standard sector-level pilot comparison |
| Industry group | Software & Services | `UNVERIFIED_CANDIDATE` | Descriptive only; no percentile calculation |
| Industry | Software | `UNVERIFIED_CANDIDATE` | Descriptive only; no percentile calculation |
| Sub-industry | Systems Software | `UNVERIFIED_CANDIDATE` | Descriptive only; no percentile calculation |

The three lower-level labels are plausible analytical candidates based on Microsoft's principal businesses, but they must not be represented as licensed or point-in-time GICS assignments. They are not used to select the approved pilot peer distribution.

## 4. Important correction discovered

The September IVV sponsor file classified AppLovin (`APP`) in Communication Services, while the June 30 XLK SEC N-PORT filing includes AppLovin in the S&P 500 Information Technology sector basket.

For the July 31 snapshot, AppLovin has therefore been restored to Information Technology. This correction demonstrates why later classifications cannot be silently projected backward. The correction is recorded as `DIFF-007` in the difference log.

## 5. Option assessment

| Option | Advantages | Limitations | Recommendation |
|---|---|---|---|
| A. Procure licensed historical GICS before continuing | Highest classification authority; supports narrow peers and production backtests | Delays the Microsoft implementation pilot and may require a paid license | Required before production |
| B. Use the dated 74-security Information Technology sector | Reproducible, point-in-time safe, exceeds the 55-security reserve target, and permits pipeline development | Peers are economically heterogeneous; sector normalization may dilute software-specific effects | **Recommended for the limited pilot** |
| C. Use analyst-assigned Systems Software peers | More economically comparable to Microsoft | Not licensed, not proven point-in-time, vulnerable to judgment and selection bias | Reject for percentile scoring |

## 6. Recommended decision

Approve Option B for the Microsoft development pilot under the following controls:

1. Label every result `PROVISIONAL — SECTOR-NORMALIZED PILOT`.
2. Use all 74 dated Information Technology securities as the initial extraction universe.
3. Do not hand-select software peers before metric extraction.
4. Apply Operating Company routing and metric-specific eligibility rules after raw data are collected.
5. Require at least 50 surviving observations for each standard sector percentile.
6. Record missingness and fallback status separately for each metric.
7. Do not substitute current GICS industry or sub-industry classifications.
8. Do not use the pilot as evidence of production backtest validity.
9. Re-run normalization using licensed dated GICS before production promotion.

This exception advances model engineering without weakening the production data standard.

## 7. Peer-batch capacity

| Item | Count |
|---|---:|
| Dated Information Technology securities | 74 |
| Microsoft target rows | 1 |
| Non-target candidate peers | 73 |
| Required surviving sector observations | 50 |
| Required initial sector batch with 10% reserve | 55 |
| Available cushion above reserve target | 19 |

The 74-security batch can absorb up to 19 exclusions and still retain the approved 55-security initial reserve target. The final standard percentile nevertheless requires at least 50 metric-eligible observations.

## 8. Look-ahead safeguards

- The sector basket comes from a June 30 filing, before the July 31 model date.
- July events are evaluated by effective date, not announcement date.
- The September IVV sector label is used only as later evidence and is not backfilled.
- AppLovin's later Communication Services label is explicitly rejected for the July 31 snapshot.
- Lower-level GICS labels remain unavailable rather than being inferred from current databases.
- Any future licensed delivery must be stored with its effective date and compared against this exception run.

## 9. Files supporting the decision

| File | Purpose |
|---|---|
| `XLK_NPORT_2026-06-30.xml` | Immutable SEC filing evidence |
| `XLK_NPORT_2026-06-30_Equity_Holdings.csv` | Parsed 74-security technology basket |
| `Microsoft_Information_Technology_Peer_Candidate_2026-07-31.csv` | Reconciled Microsoft sector peer batch |
| `SP500_PIT_2026-07-31_R1_candidate.csv` | Corrected full point-in-time universe |
| `SP500_PIT_2026-07-31_Difference_Log.csv` | AppLovin and earlier reconciliation decisions |

## 10. Approval choices

Record exactly one:

- `APPROVE_LIMITED_SECTOR_PILOT` — proceed with the 74-security extraction batch while retaining the production GICS requirement.
- `PAUSE_FOR_LICENSED_GICS` — do not begin peer financial-data extraction.
- `REVISE` — return the decision with specified changes.

Approval does not freeze the full S&P 500 snapshot or authorize production backtesting. It authorizes only the Microsoft sector-normalized development pilot.

## 11. Next step after approval

Freeze the 74-security extraction batch, define its permanent batch identifier, and construct the point-in-time financial-data acquisition manifest for quarterly and trailing-twelve-month Fast APAM metrics.

# Fast APAM Decision Register

**Project:** Fast APAM Model  
**Parent project:** Core APAM Model / Agora Lycos Trading Lab  
**Version:** 0.1  
**Status:** Pre-implementation methodology register  
**Governing document:** `Fast_APAM_Project_Charter_v0.1.md`  
**Last updated:** 2026-09-19

## 1. Purpose

This register records the methodological, accounting, data, scoring, and validation decisions that must be resolved before Fast APAM implementation begins.

Fast APAM is the quarterly and trailing-twelve-month companion to annual Core APAM. It is intended to detect recent acceleration, stabilization, deceleration, or deterioration while Core APAM measures durable quality.

No decision in this register authorizes implementation code by itself. Coding begins only after the required pre-implementation decisions are approved and the period-construction test cases are defined.

## 2. Decision status definitions

| Status | Meaning |
| --- | --- |
| `LOCKED` | Explicit governing requirement; cannot change without revising the charter. |
| `PROPOSED` | Recommended default awaiting formal approval. |
| `APPROVED` | Accepted for the current model version. |
| `RESEARCH_REQUIRED` | Evidence or testing is required before a rule can be selected. |
| `DEFERRED` | Deliberately excluded from the current version. |
| `REJECTED` | Considered and not adopted. |
| `SUPERSEDED` | Replaced by a later decision; original record remains for history. |

## 3. Approval rules

- Decisions marked `LOCKED` preserve explicit project requirements.
- Decisions marked `PROPOSED` must be reviewed before implementation of the affected module.
- Methodological weights and thresholds remain research hypotheses until validated out of sample.
- A changed decision receives a new revision entry; prior reasoning is not deleted.
- Each approved decision must identify its effective model version.
- Period construction, filing availability, and restatement decisions must be approved before composite scoring is developed.

## 4. Decision summary

| ID | Decision | Category | Status | Required before |
| --- | --- | --- | --- | --- |
| FAPAM-001 | Separate Fast APAM from Core APAM | Architecture | `LOCKED` | All work |
| FAPAM-002 | Define primary comparison hierarchy | Methodology | `LOCKED` | Metric design |
| FAPAM-003 | Treat acceleration as a scored contribution | Scoring | `LOCKED` | Scoring design |
| FAPAM-004 | Limit initial universe to point-in-time S&P 500 | Eligibility | `APPROVED` | Data acquisition |
| FAPAM-005 | Use SEC filings as accounting truth layer | Data | `APPROVED` | Data contracts |
| FAPAM-006 | Define filing availability timestamp | Point-in-time | `APPROVED` | Backtesting |
| FAPAM-007 | Reconstruct standalone quarters from cumulative filings | Accounting | `APPROVED` | Period engine |
| FAPAM-008 | Derive Q4 from annual minus nine-month totals | Accounting | `APPROVED` | Period engine |
| FAPAM-009 | Maintain as-filed and latest-restated series | Point-in-time | `APPROVED` | Historical storage |
| FAPAM-010 | Align comparisons by issuer fiscal quarter | Accounting | `APPROVED` | Period engine |
| FAPAM-011 | Establish missing-data and scoreability policy | Eligibility | `PROPOSED` | Scoring |
| FAPAM-012 | Use three sector-methodology families | Sector | `PROPOSED` | Metric design |
| FAPAM-013 | Handle employee denominators by disclosure quality | Methodology | `PROPOSED` | Productivity metrics |
| FAPAM-014 | Separate score, confidence, and status outputs | Reporting | `PROPOSED` | Scoring |
| FAPAM-015 | Preserve Core/Fast disagreement in a state matrix | Architecture | `PROPOSED` | Integration |
| FAPAM-016 | Use filed data for initial production-grade version | Scope | `APPROVED` | Data contracts |
| FAPAM-017 | Validate the period engine before scoring | Development | `APPROVED` | Implementation |
| FAPAM-018 | Predeclare model-promotion criteria | Validation | `PROPOSED` | Backtesting |
| FAPAM-019 | Keep AI attribution outside the accounting score | Scope | `PROPOSED` | Reporting |
| FAPAM-020 | Select a difficult stratified test-company set | Validation | `RESEARCH_REQUIRED` | Period engine |

---

## 5. Detailed decisions

### FAPAM-001 — Separate Fast APAM from Core APAM

**Category:** Architecture  
**Status:** `LOCKED`  
**Effective version:** Fast APAM v0.1 design onward

**Decision**

Fast APAM will be a separate companion to Core APAM. Core APAM measures durable annual quality; Fast APAM measures recent quarterly and TTM change. Fast APAM will not silently replace, rewrite, or become an opaque internal component of the Core score.

**Rationale**

Annual and quarterly data answer different questions. Separating the models preserves interpretability and makes disagreement useful rather than hiding it in a blended number.

**Rejected alternative**

Insert quarterly acceleration directly into Core APAM and publish only one score.

**Affected modules**

Architecture, scoring, reporting, Core/Fast integration, validation.

**Validation requirement**

Compare Core-only, Fast-only, and Core/Fast state combinations without changing historical Core classifications.

---

### FAPAM-002 — Define the primary comparison hierarchy

**Category:** Methodology  
**Status:** `LOCKED`

**Decision**

The primary hierarchy is:

1. TTM versus prior-year TTM.
2. Standalone fiscal quarter versus the comparable prior-year fiscal quarter.
3. Change in the above YoY trends to measure acceleration or deterioration.
4. Sequential QoQ only as a diagnostic field with zero primary factor weight in v1.

**Rationale**

TTM comparisons reduce noise, while comparable-quarter YoY comparisons detect recent inflections. Raw sequential QoQ changes are frequently distorted by seasonality.

**Rejected alternative**

Use current quarter versus immediately preceding quarter as the main acceleration measure.

**Validation requirement**

Test incremental information from TTM, comparable-quarter YoY, and sequential QoQ independently by sector.

---

### FAPAM-003 — Treat acceleration as a scored contribution

**Category:** Scoring  
**Status:** `LOCKED`

**Decision**

Acceleration will generally contribute to FastScore rather than operate as an automatic elimination gate. Only invalid, unavailable, or irreconcilable data can prevent scoring.

**Rationale**

A strong company can remain attractive while growth normalizes, and a weak company can temporarily accelerate from a depressed base. A hard acceleration gate would discard useful information and increase cyclicality.

**Rejected alternative**

Automatically exclude every company whose latest growth rate is not accelerating.

**Validation requirement**

Measure false negatives created by hypothetical acceleration gates and compare them with graded-factor results.

---

### FAPAM-004 — Limit the initial universe to point-in-time S&P 500

**Category:** Eligibility  
**Status:** `APPROVED`

**Proposed decision**

Fast APAM v1 will use the same point-in-time S&P 500 universe as Core APAM. The personal universe file may serve as an operational input, but historical testing must use membership known on each evaluation date.

**Rationale**

This maintains consistency with Core APAM and contains the initial data-engineering scope.

**Alternatives considered**

- Current S&P 500 constituents only.
- All US-listed common stocks.
- S&P 500 plus Nasdaq additions.

**Primary risk**

A current-only personal universe would create survivorship bias in historical tests.

**Approval condition**

Confirm the personal universe schema and identify a source for historical membership dates.

---

### FAPAM-005 — Use SEC filings as the accounting truth layer

**Category:** Data  
**Status:** `APPROVED`

**Proposed decision**

SEC filings and filing documents will be the accounting truth layer. FMP or another structured provider may supply scalable normalized data, but material conflicts must be reconciled against the filed information.

**Source precedence**

1. SEC filing facts and filed financial statements.
2. Company-filed reconciliations and supplemental schedules.
3. Structured vendor fields.
4. Manual review for unresolved material conflicts.

**Rationale**

Vendor normalization is efficient but can conceal taxonomy, period, restatement, or sector-definition differences.

**Approval condition**

Define materiality tolerances and which source supplies each canonical field.

---

### FAPAM-006 — Define filing availability timestamp

**Category:** Point-in-time safeguard  
**Status:** `APPROVED`

**Proposed decision**

A filed fact becomes eligible only after the SEC acceptance timestamp plus a documented processing buffer. Period end dates are never treated as availability dates.

**Proposed default buffer**

One full trading day for the primary backtest, with same-day and two-trading-day sensitivity tests.

**Special rule**

A derived Q4 becomes available at the annual filing timestamp unless an earlier, separately timestamped source is explicitly included in a later model version.

**Primary risk controlled**

Look-ahead bias.

**Approval condition**

Select the production processing buffer and backtest rebalance convention.

---

### FAPAM-007 — Reconstruct standalone quarters from cumulative filings

**Category:** Accounting  
**Status:** `APPROVED`

**Proposed decision**

For flow items:

- Q1 standalone = valid three-month Q1 value.
- Q2 standalone = six-month YTD minus Q1 YTD/standalone, unless a compatible direct Q2 value is filed.
- Q3 standalone = nine-month YTD minus six-month YTD, unless a compatible direct Q3 value is filed.

Direct standalone values take precedence only when concept, duration, unit, dimensions, consolidation scope, and restatement basis are compatible. Every derived value must retain links to its source facts.

**Explicit exclusions**

- Do not subtract instantaneous balance-sheet facts.
- Do not derive ratios or per-share values by subtraction.
- Do not combine facts with inconsistent dimensions or reporting scope.

**Approval condition**

Approve concept-matching, tolerance, and direct-versus-derived precedence rules after hand testing.

---

### FAPAM-008 — Derive Q4 from annual minus nine-month totals

**Category:** Accounting  
**Status:** `APPROVED`

**Proposed decision**

Q4 standalone flow = validated annual FY flow minus validated nine-month YTD flow.

**Required safeguards**

- Same fiscal year and consolidated entity.
- Compatible concepts, units, dimensions, and continuing-operation scope.
- Compatible restatement basis.
- No unresolved fiscal-calendar transition or material taxonomy mismatch.
- Derived result reconciles to the annual total within tolerance.

If any critical condition fails, Q4 becomes `REVIEW_REQUIRED` or `PERIOD_INCOMPARABLE`; it is not forced.

**Approval condition**

Define materiality tolerances and treatment of recast nine-month comparatives in 10-K filings.

---

### FAPAM-009 — Maintain as-filed and latest-restated series

**Category:** Point-in-time safeguard  
**Status:** `APPROVED`

**Proposed decision**

Store two logical views:

- `AS_FILED`: values available at each historical model date.
- `LATEST_RESTATED`: most current comparable history for present-day diagnostics.

An amendment or later restatement becomes available only on its real acceptance date. It must never rewrite an earlier backtest state.

**Rationale**

This supports honest historical testing while retaining the best current accounting view.

**Validation requirement**

Quantify score and backtest differences between the two views.

---

### FAPAM-010 — Align comparisons by issuer fiscal quarter

**Category:** Accounting  
**Status:** `APPROVED`

**Proposed decision**

Compare each issuer’s fiscal quarter with the same issuer’s prior-year fiscal quarter. Do not force all companies into calendar quarters. Peer rankings use each company’s latest eligible filing as of a shared model date and disclose data age.

**52/53-week rule**

Keep reported values primary, flag extra-week effects, and use duration-normalized figures only as sensitivity diagnostics.

**Transition-period rule**

Stub periods and fiscal-year changes are `PERIOD_INCOMPARABLE` until a defensible comparable window exists.

**Approval condition**

Define maximum peer-data staleness and extra-week flag thresholds.

---

### FAPAM-011 — Establish missing-data and scoreability policy

**Category:** Eligibility  
**Status:** `PROPOSED`

**Proposed decision**

- Never convert missing values to zero.
- Never impute company financial-statement values from peers.
- Score partial records only when module-specific minimum coverage is met.
- Rescale available component weights only within documented caps.
- Reduce DataConfidence for missing, stale, carried, derived, vendor-only, or weakly comparable data.
- Publish coverage and exclusion reasons beside the score.

**Proposed data statuses**

`PASS`, `PARTIAL`, `STALE`, `REVIEW_REQUIRED`, `INSUFFICIENT_HISTORY`, `SECTOR_MODULE_UNAVAILABLE`, `PERIOD_INCOMPARABLE`.

**Approval condition**

Define minimum factor coverage and maximum allowable weight rescaling for each sector module.

---

### FAPAM-012 — Use three sector-methodology families

**Category:** Sector methodology  
**Status:** `PROPOSED`

**Proposed decision**

Fast APAM v1 will contain:

1. Operating companies.
2. Financials, divided into appropriate sub-industries.
3. Equity REITs.

Mortgage REITs are excluded until a separate methodology exists.

**Rationale**

Generic revenue, EBIT, FCF, and ROIC do not represent the economics of banks, insurers, and REITs consistently.

**Module principles**

- Operating companies: productivity, operating margins, FCF margins, and capital efficiency.
- Banks: efficiency, operating leverage, asset quality, and capital adequacy.
- Insurers: underwriting and expense efficiency with catastrophe/reserve controls.
- Asset managers/brokers: revenue and cost efficiency with market/AUM context.
- Equity REITs: same-store NOI, FFO/AFFO, occupancy, recurring capex, and leverage.

**Approval condition**

Approve inclusion/exclusion mapping by GICS industry and select minimum required fields for each module.

---

### FAPAM-013 — Handle employee denominators by disclosure quality

**Category:** Methodology  
**Status:** `PROPOSED`

**Proposed decision**

Classify employee-based factors as:

- `OBSERVED_EMPLOYEE`: timely interim employee data is available.
- `CARRIED_EMPLOYEE`: latest annual employee count is carried forward with age and reduced weight/confidence.
- `NO_EMPLOYEE_SIGNAL`: Fast APAM operates without per-employee factors.

**Rationale**

Employee counts are usually annual and can become stale inside a quarterly model. Treating a carried annual count as a fresh quarterly observation would create false precision.

**Approval condition**

Research and approve the carry-forward decay schedule and maximum age.

---

### FAPAM-014 — Separate score, confidence, and status outputs

**Category:** Scoring and reporting  
**Status:** `PROPOSED`

**Proposed decision**

Publish four separate outputs:

1. `FastScore` from 0–100.
2. `DataConfidence` from 0–100.
3. `FastStatus` describing economic direction.
4. `DataStatus` describing eligibility and quality.

**Proposed FastStatus vocabulary**

`ACCELERATING`, `IMPROVING`, `STABLE`, `DECELERATING`, `DETERIORATING`, `MIXED`, `UNSCORED`.

**Initial research weights—not approved production weights**

- 35% TTM productivity/operating improvement.
- 25% latest comparable-quarter YoY improvement.
- 20% margin and capital/sector-quality confirmation.
- 15% acceleration and persistence.
- 5% breadth and consistency.

**Approval condition**

Approve output vocabulary now; leave weights and classification thresholds `RESEARCH_REQUIRED` until validation.

---

### FAPAM-015 — Preserve Core/Fast disagreement in a state matrix

**Category:** Architecture  
**Status:** `PROPOSED`

**Proposed decision**

Core APAM and Fast APAM remain separately visible. Their interaction is interpreted through a state matrix:

| Core | Fast | Interpretation |
| --- | --- | --- |
| Strong | Accelerating/Improving | Durable quality with recent confirmation |
| Strong | Decelerating/Deteriorating | Durable franchise with emerging weakness |
| Weak/Mixed | Accelerating/Improving | Early inflection; durability unproven |
| Weak | Deteriorating | No durable or recent confirmation |
| Any | Mixed/Unscored | Evidence unresolved |

No combined composite score will be released in v1.

**Rationale**

Disagreement is valuable research information and should not be averaged away.

**Approval condition**

Approve the matrix vocabulary and research-priority rules.

---

### FAPAM-016 — Use filed data for the initial production-grade version

**Category:** Scope  
**Status:** `APPROVED`

**Proposed decision**

Fast APAM v1 will score filed financial information. Earnings releases, investor supplements, estimates, guidance, and transcripts may be researched later as separately timestamped early-update or attribution layers.

**Rationale**

Filed data provides the clearest initial provenance and restatement controls. Mixing preliminary and filed data in the first engine would complicate comparability and point-in-time testing.

**Deferred items**

Earnings-release nowcasting, analyst revisions, guidance, transcript language, and alternative data.

---

### FAPAM-017 — Validate the period engine before scoring

**Category:** Development sequence  
**Status:** `APPROVED`

**Proposed decision**

Development gates will be:

1. Approve charter and critical decisions.
2. Freeze data and period contracts.
3. Create hand-calculated test fixtures.
4. Implement and validate standalone-quarter and TTM construction.
5. Add sector metrics.
6. Research scoring and statuses.
7. Integrate with Core APAM.
8. Perform point-in-time backtest and independent audit.

Composite scoring must not begin until the period engine passes its accounting and lineage acceptance tests.

**Rationale**

A sophisticated score built on incorrectly reconstructed quarters would be invalid and difficult to debug.

---

### FAPAM-018 — Predeclare model-promotion criteria

**Category:** Validation  
**Status:** `PROPOSED`

**Proposed decision**

Before backtesting, declare the evaluation metrics, benchmark models, time splits, factor-ablation tests, and acceptable tradeoffs. A factor may enter production only if it improves at least one declared objective without unacceptable degradation elsewhere.

**Required validation dimensions**

- Accounting reconstruction accuracy.
- Point-in-time integrity.
- Coverage and missingness.
- Score stability and turnover.
- Sector and sub-industry behavior.
- Information coefficient and forward-return spreads.
- Drawdown and false-positive control.
- Interpretability and reproducibility.

**Approval condition**

Define exact thresholds after data coverage is measured but before final out-of-sample testing.

---

### FAPAM-019 — Keep AI attribution outside the accounting score

**Category:** Scope and interpretation  
**Status:** `PROPOSED`

**Proposed decision**

Fast APAM will detect measurable operating and productivity change. It will not claim that AI caused the change. AI evidence will remain a separate attribution layer that can be compared with Core and Fast results.

**Rationale**

Financial improvement can result from pricing, layoffs, acquisitions, mix shifts, commodity cycles, restructuring, or other operational changes. Measurable improvement is evidence consistent with the APAM thesis, not proof of causation.

**Approval condition**

Approve separate labels for measured outcome, confounder flags, and AI evidence.

---

### FAPAM-020 — Select a difficult stratified test-company set

**Category:** Validation  
**Status:** `RESEARCH_REQUIRED`

**Decision required**

Select a small set of companies and filings that exercise the difficult cases before general ingestion.

**Required fixture categories**

- Standard operating company with clean quarterly facts.
- Cumulative-only 10-Q presentation.
- Q4 derived from annual minus nine-month totals.
- Amended filing or material restatement.
- 52/53-week fiscal year.
- Fiscal-year-end change or stub period.
- Major acquisition or divestiture.
- Bank.
- Insurer or asset manager/broker.
- Equity REIT.
- Company with missing or stale employee data.
- Company with taxonomy or dimensional changes.

**Expected output**

A test-company register containing issuer, ticker, CIK, sector module, accession numbers, edge case, hand-calculated expected results, reviewer, and approval status.

---

## 6. Decisions requiring immediate approval

The following decisions should be resolved before any implementation work:

| Priority | Decision IDs | Required action |
| --- | --- | --- |
| 1 | FAPAM-004, FAPAM-005, FAPAM-016 | Confirm universe and initial source scope. |
| 2 | FAPAM-006–FAPAM-010 | Approve point-in-time and period-construction rules. |
| 3 | FAPAM-011–FAPAM-013 | Approve minimum coverage and sector methodology boundaries. |
| 4 | FAPAM-014–FAPAM-015 | Approve outputs and Core interaction. |
| 5 | FAPAM-017–FAPAM-020 | Approve development and validation gates; select test companies. |

## 7. Open research questions

| Question ID | Question | Related decisions | Resolution evidence |
| --- | --- | --- | --- |
| RQ-001 | What processing lag is operationally realistic? | FAPAM-006 | Historical ingestion timing and sensitivity tests. |
| RQ-002 | What reconciliation tolerances work across taxonomy changes? | FAPAM-007, FAPAM-008 | Hand-audited filing fixtures. |
| RQ-003 | How stale can peer data be before rank comparability fails? | FAPAM-010 | Coverage and ranking-stability analysis. |
| RQ-004 | What minimum factor coverage permits a reliable partial score? | FAPAM-011 | Missingness and score-stability tests. |
| RQ-005 | How quickly should carried employee data lose weight? | FAPAM-013 | Disclosure-frequency and sensitivity analysis. |
| RQ-006 | Which Financials sub-industries require distinct modules? | FAPAM-012 | Accounting-field coverage and economic comparability. |
| RQ-007 | Which FastStatus thresholds are stable out of sample? | FAPAM-014 | Walk-forward and threshold-sensitivity tests. |
| RQ-008 | Does Fast APAM add value beyond annual Core APAM? | FAPAM-015, FAPAM-018 | Core-only versus Core/Fast ablation tests. |

## 8. Approval record

Use one row for each approved, rejected, deferred, or revised decision.

| Date | Decision ID | Action | Approved rule or change | Effective version | Approver | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| 2026-09-19 | FAPAM-001 | Locked by project requirement | Fast APAM remains separate from Core APAM. | v0.1 design | Douglas Salone | Foundational architecture. |
| 2026-09-19 | FAPAM-002 | Locked by project requirement | TTM and comparable-quarter YoY are primary; sequential QoQ is diagnostic. | v0.1 design | Douglas Salone | Preserves seasonality safeguards. |
| 2026-09-19 | FAPAM-003 | Locked by project requirement | Acceleration contributes to score rather than acting as an automatic gate. | v0.1 design | Douglas Salone | Hard gates reserved for invalid or insufficient data. |
| 2026-09-19 | FAPAM-004 | Approved | Use the point-in-time S&P 500 universe for Fast APAM v1. | v0.1 design | Douglas Salone | Personal universe may be used operationally; historical tests require dated membership. |
| 2026-09-19 | FAPAM-005 | Approved | SEC filings are the accounting truth layer; FMP is the structured convenience layer. | v0.1 design | Douglas Salone | Material conflicts reconcile to filed information. |
| 2026-09-19 | FAPAM-006 | Approved | Use SEC acceptance timestamp plus one full trading day as the primary availability rule. | v0.1 design | Douglas Salone | Same-day and two-day alternatives remain sensitivity tests. |
| 2026-09-19 | FAPAM-007 | Approved | Reconstruct Q2 and Q3 standalone flows from compatible cumulative filing facts when needed. | v0.1 design | Douglas Salone | Derived values retain full lineage. |
| 2026-09-19 | FAPAM-008 | Approved | Derive Q4 flows from compatible annual minus nine-month totals. | v0.1 design | Douglas Salone | Incompatible cases are not forced. |
| 2026-09-19 | FAPAM-009 | Approved | Preserve both as-filed and latest-restated logical histories. | v0.1 design | Douglas Salone | Backtests use as-filed vintages. |
| 2026-09-19 | FAPAM-010 | Approved | Compare companies by issuer fiscal quarter and disclose peer-data age. | v0.1 design | Douglas Salone | Calendar-quarter coercion is prohibited. |
| 2026-09-19 | FAPAM-016 | Approved | Limit the initial production-grade model to filed fundamentals. | v0.1 design | Douglas Salone | Preliminary releases and estimates are deferred layers. |
| 2026-09-19 | FAPAM-017 | Approved | Validate the period engine before developing composite scoring. | v0.1 design | Douglas Salone | Establishes the implementation gate. |

## 9. Revision history

| Register version | Date | Change | Author |
| --- | --- | --- | --- |
| 0.1 | 2026-09-19 | Created initial pre-implementation decision register with 20 decisions and eight research questions. | Agora Lycos / Douglas Salone |
| 0.2 | 2026-09-19 | Recorded approval of FAPAM-004 through FAPAM-010, FAPAM-016, and FAPAM-017. | Agora Lycos / Douglas Salone |

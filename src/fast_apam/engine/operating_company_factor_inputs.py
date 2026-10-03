"""Build auditable Operating Company factor inputs without calculating FastScore."""
from __future__ import annotations
from ..settings import MODEL_DATE, COHORT_SIZE, WAVE_COUNTS
import argparse
import csv
import json
from collections import defaultdict
from decimal import Decimal
from pathlib import Path
NEUTRAL = {'growth': Decimal('0.01'), 'profit': Decimal('0.02'), 'cash': Decimal('0.03'), 'margin': Decimal('0.0025'), 'acceleration': Decimal('0.01')}

def _decimal(value: str) -> Decimal | None:
    return Decimal(value) if value not in (None, '') else None

def _ratio(numerator: Decimal | None, denominator: Decimal | None) -> Decimal | None:
    if numerator is None or denominator in (None, Decimal(0)):
        return None
    return numerator / denominator

def _difference(current: Decimal | None, prior: Decimal | None) -> Decimal | None:
    return current - prior if current is not None and prior is not None else None

def _fmt(value: Decimal | None) -> str:
    return '' if value is None else format(value, 'f')

def _direction(value: Decimal | None, band: Decimal) -> str:
    if value is None:
        return 'INELIGIBLE'
    if value > band:
        return 'SUPPORTIVE'
    if value < -band:
        return 'ADVERSE'
    return 'NEUTRAL'

def _combine_directions(values: list[str]) -> str:
    eligible = [value for value in values if value != 'INELIGIBLE']
    if not eligible:
        return 'INELIGIBLE'
    directional = set(eligible) - {'NEUTRAL'}
    if directional == {'SUPPORTIVE', 'ADVERSE'}:
        return 'CONFLICTED'
    if 'SUPPORTIVE' in directional:
        return 'SUPPORTIVE'
    if 'ADVERSE' in directional:
        return 'ADVERSE'
    return 'NEUTRAL'

def _persistence(values: list[Decimal]) -> str:
    """Qualitative diagnostic only; numerical persistence weights remain unapproved."""
    values = values[-4:]
    if len(values) < 2:
        return 'INSUFFICIENT_HISTORY'
    positive = all((value > 0 for value in values))
    negative = all((value < 0 for value in values))
    improving = all((left <= right for left, right in zip(values, values[1:])))
    deteriorating = all((left >= right for left, right in zip(values, values[1:])))
    if positive and improving:
        return 'CONSISTENTLY_POSITIVE_IMPROVING'
    if positive and deteriorating:
        return 'POSITIVE_BUT_SLOWING'
    if negative and improving:
        return 'NEGATIVE_BUT_RECOVERING'
    if negative and deteriorating:
        return 'CONSISTENTLY_NEGATIVE_DETERIORATING'
    return 'NEUTRAL_OR_ALTERNATING'

def _latest_aligned(rows_by_concept: dict[str, list[dict]]) -> tuple[str, dict[str, dict]]:
    latest_by_concept = {concept: max(rows, key=lambda row: row['quarter_period_end']) for concept, rows in rows_by_concept.items()}
    anchors = [latest_by_concept.get('revenue'), latest_by_concept.get('operating_income')]
    period = max((row['quarter_period_end'] for row in latest_by_concept.values()), default='')
    if all(anchors):
        period = max((row['quarter_period_end'] for row in anchors))
    aligned = {concept: row for concept, row in latest_by_concept.items() if row['quarter_period_end'] == period}
    return (period, aligned)

def _derived_history(rows_by_concept: dict[str, list[dict]]) -> dict[str, list[dict]]:
    by_end = defaultdict(dict)
    for concept, rows in rows_by_concept.items():
        for row in rows:
            by_end[row['quarter_period_end']][concept] = row
    result = defaultdict(list)
    for period_end, concepts in sorted(by_end.items()):
        revenue = concepts.get('revenue')
        if not revenue:
            continue
        revenue_ttm = _decimal(revenue['ttm_value'])
        prior_revenue_ttm = _decimal(revenue['prior_year_ttm_value'])
        for name, concept in (('operating_margin', 'operating_income'), ('cfo_margin', 'cash_from_operations'), ('fcf_margin', 'free_cash_flow'), ('capex_intensity', 'capital_expenditures')):
            source = concepts.get(concept)
            if not source:
                continue
            current = _ratio(_decimal(source['ttm_value']), revenue_ttm)
            prior = _ratio(_decimal(source['prior_year_ttm_value']), prior_revenue_ttm)
            result[name].append({'period_end': period_end, 'current': current, 'prior': prior, 'yoy_pp': _difference(current, prior)})
    for name, values in result.items():
        for index, value in enumerate(values):
            previous = values[index - 1] if index else None
            value['acceleration_pp'] = _difference(value['yoy_pp'], previous['yoy_pp'] if previous else None)
    return result

def _factor_audit(ticker: str, coverage: dict[str, Decimal], evidence: dict) -> list[dict]:
    f1 = evidence['revenue_ttm'] and evidence['profit_ttm'] and evidence['cash_ttm'] and (coverage['F1_TTM'] >= Decimal('0.60'))
    f2 = evidence['revenue_q'] and evidence['profit_q'] and (coverage['F2_QUARTER'] >= Decimal('0.90'))
    f3 = evidence['operating_margin'] and evidence['quality_confirmation'] and (coverage['F3_QUALITY'] >= Decimal('0.50'))
    f4 = evidence['acceleration_family_count'] >= 2 and coverage['F4_ACCELERATION'] >= Decimal('0.40')
    f5 = evidence['breadth_family_count'] >= 3
    checks = {'F1_TTM': (f1, 'Revenue + operating profit + cash; >=60% original weight'), 'F2_QUARTER': (f2, 'Revenue + operating profit; approved gross-profit fallback; >=90%'), 'F3_QUALITY': (f3, 'Operating-margin anchor + independent confirmation; >=50%'), 'F4_ACCELERATION': (f4, 'At least two independent families; >=40%'), 'F5_BREADTH': (f5, 'At least three eligible independent families')}
    return [{'ticker': ticker, 'factor_id': factor, 'original_weight_coverage': _fmt(coverage[factor]), 'floor_status': 'PASS' if passed else 'FAIL', 'floor_rule': rule, 'score_calculated': 'NO', 'score_hold_reason': 'PEER_NORMALIZATION_NOT_STARTED'} for factor, (passed, rule) in checks.items()]

def build(observations_path: Path, source_audit_path: Path, matrix_path: Path, audit_path: Path) -> dict:
    with observations_path.open(newline='', encoding='utf-8-sig') as handle:
        rows = list(csv.DictReader(handle))
    with source_audit_path.open(newline='', encoding='utf-8-sig') as handle:
        source_audit = list(csv.DictReader(handle))
    universe = {row['ticker']: row['cik'] for row in source_audit}
    blockers = defaultdict(list)
    for row in source_audit:
        if not row['current_signal_status'].startswith('PASS_CURRENT_FAST_SIGNAL_INPUTS'):
            blockers[row['ticker']].append(f"{row['canonical_concept']}:{row['current_signal_status']}")
    grouped = defaultdict(lambda: defaultdict(list))
    for row in rows:
        grouped[row['ticker']][row['canonical_concept']].append(row)
    matrix, audit = ([], [])
    for ticker, concepts in sorted(grouped.items()):
        for values in concepts.values():
            values.sort(key=lambda row: row['quarter_period_end'])
        period_end, latest = _latest_aligned(concepts)
        derived = _derived_history(concepts)
        get = lambda concept, field: _decimal(latest.get(concept, {}).get(field, ''))
        latest_derived = {name: next((x for x in reversed(values) if x['period_end'] == period_end), {}) for name, values in derived.items()}
        revenue_ttm = get('revenue', 'ttm_yoy_rate')
        profit_ttm = get('operating_income', 'ttm_yoy_rate')
        cfo_ttm = get('cash_from_operations', 'ttm_yoy_rate')
        fcf_ttm = get('free_cash_flow', 'ttm_yoy_rate')
        revenue_q = get('revenue', 'quarter_yoy_rate')
        profit_q = get('operating_income', 'quarter_yoy_rate')
        op_margin = latest_derived.get('operating_margin', {})
        cfo_margin = latest_derived.get('cfo_margin', {})
        fcf_margin = latest_derived.get('fcf_margin', {})
        capex_intensity = latest_derived.get('capex_intensity', {})
        op_leverage = _difference(profit_ttm, revenue_ttm)
        family = {'EF_GROWTH': _direction(revenue_ttm, NEUTRAL['growth']), 'EF_PROFIT': _direction(profit_ttm, NEUTRAL['profit']), 'EF_CASH': _combine_directions([_direction(cfo_ttm, NEUTRAL['cash']), _direction(fcf_ttm, NEUTRAL['cash'])]), 'EF_MARGIN': _direction(op_margin.get('yoy_pp'), NEUTRAL['margin']), 'EF_PRODUCTIVITY': 'INELIGIBLE', 'EF_CAPITAL': 'INELIGIBLE'}
        eligible_families = sum((value != 'INELIGIBLE' for value in family.values()))
        rev_q_acc = get('revenue', 'quarter_yoy_acceleration')
        rev_ttm_acc = get('revenue', 'ttm_yoy_acceleration')
        profit_q_acc = get('operating_income', 'quarter_yoy_acceleration')
        profit_ttm_acc = get('operating_income', 'ttm_yoy_acceleration')
        cfo_acc = get('cash_from_operations', 'ttm_yoy_acceleration')
        fcf_acc = get('free_cash_flow', 'ttm_yoy_acceleration')
        acceleration_families = sum([rev_q_acc is not None or rev_ttm_acc is not None, profit_q_acc is not None or profit_ttm_acc is not None, cfo_acc is not None or fcf_acc is not None, op_margin.get('acceleration_pp') is not None])
        f1_coverage = sum((weight for present, weight in [(revenue_ttm is not None, Decimal('.20')), (profit_ttm is not None, Decimal('.25')), (cfo_ttm is not None, Decimal('.15')), (fcf_ttm is not None, Decimal('.20'))] if present))
        f2_coverage = Decimal(1) if revenue_q is not None and profit_q is not None else sum((weight for present, weight in [(revenue_q is not None, Decimal('.45')), (profit_q is not None, Decimal('.45'))] if present))
        f3_coverage = sum((weight for present, weight in [(op_margin.get('yoy_pp') is not None, Decimal('.30')), (fcf_margin.get('yoy_pp') is not None, Decimal('.20')), (op_leverage is not None, Decimal('.20'))] if present))
        f4_coverage = sum((weight for present, weight in [(rev_q_acc is not None or rev_ttm_acc is not None, Decimal('.25')), (profit_q_acc is not None or profit_ttm_acc is not None, Decimal('.30')), (cfo_acc is not None or fcf_acc is not None, Decimal('.15')), (op_margin.get('acceleration_pp') is not None, Decimal('.15')), (acceleration_families >= 2, Decimal('.15'))] if present))
        coverage = {'F1_TTM': f1_coverage, 'F2_QUARTER': f2_coverage, 'F3_QUALITY': f3_coverage, 'F4_ACCELERATION': f4_coverage, 'F5_BREADTH': Decimal(eligible_families) / Decimal(6)}
        evidence = {'revenue_ttm': revenue_ttm is not None, 'profit_ttm': profit_ttm is not None, 'cash_ttm': cfo_ttm is not None or fcf_ttm is not None, 'revenue_q': revenue_q is not None, 'profit_q': profit_q is not None, 'operating_margin': op_margin.get('yoy_pp') is not None, 'quality_confirmation': fcf_margin.get('yoy_pp') is not None or cfo_margin.get('yoy_pp') is not None, 'acceleration_family_count': acceleration_families, 'breadth_family_count': eligible_families}
        audit.extend(_factor_audit(ticker, coverage, evidence))
        persistence_json = {}
        for family_name, concept in (('EF_GROWTH', 'revenue'), ('EF_PROFIT', 'operating_income'), ('EF_CASH_CFO', 'cash_from_operations'), ('EF_CASH_FCF', 'free_cash_flow')):
            history = [_decimal(row['quarter_yoy_rate']) for row in concepts.get(concept, [])]
            history = [value for value in history if value is not None][-4:]
            persistence_json[family_name] = {'values': [_fmt(value) for value in history], 'classification': _persistence(history)}
        availability = max((row['signal_model_available_date'] for row in latest.values()), default='')
        matrix.append({'ticker': ticker, 'cik': next(iter(latest.values()))['cik'], 'as_of_period_end': period_end, 'fiscal_quarter': next(iter(latest.values()))['fiscal_quarter'], 'signal_model_available_date': availability, 'revenue_q_yoy': _fmt(revenue_q), 'operating_income_q_yoy': _fmt(profit_q), 'revenue_ttm_yoy': _fmt(revenue_ttm), 'operating_income_ttm_yoy': _fmt(profit_ttm), 'cfo_ttm_yoy': _fmt(cfo_ttm), 'fcf_ttm_yoy': _fmt(fcf_ttm), 'operating_margin_ttm': _fmt(op_margin.get('current')), 'operating_margin_prior_ttm': _fmt(op_margin.get('prior')), 'operating_margin_yoy_pp': _fmt(op_margin.get('yoy_pp')), 'operating_leverage_spread': _fmt(op_leverage), 'cfo_margin_ttm': _fmt(cfo_margin.get('current')), 'cfo_margin_yoy_pp': _fmt(cfo_margin.get('yoy_pp')), 'fcf_margin_ttm': _fmt(fcf_margin.get('current')), 'fcf_margin_yoy_pp': _fmt(fcf_margin.get('yoy_pp')), 'capex_intensity_ttm': _fmt(capex_intensity.get('current')), 'capex_intensity_yoy_pp': _fmt(capex_intensity.get('yoy_pp')), 'capex_interpretation': 'AMBIGUOUS_UNTIL_DETERMINISTIC_RULE_VALIDATED' if capex_intensity else 'INELIGIBLE', 'revenue_q_yoy_acceleration': _fmt(rev_q_acc), 'revenue_ttm_yoy_acceleration': _fmt(rev_ttm_acc), 'operating_income_q_yoy_acceleration': _fmt(profit_q_acc), 'operating_income_ttm_yoy_acceleration': _fmt(profit_ttm_acc), 'cfo_ttm_yoy_acceleration': _fmt(cfo_acc), 'fcf_ttm_yoy_acceleration': _fmt(fcf_acc), 'operating_margin_acceleration_pp': _fmt(op_margin.get('acceleration_pp')), 'persistence_diagnostic_json': json.dumps(persistence_json, separators=(',', ':'), sort_keys=True), 'growth_family_class': family['EF_GROWTH'], 'profit_family_class': family['EF_PROFIT'], 'cash_family_class': family['EF_CASH'], 'margin_family_class': family['EF_MARGIN'], 'productivity_family_class': family['EF_PRODUCTIVITY'], 'capital_family_class': family['EF_CAPITAL'], 'eligible_breadth_families': str(eligible_families), 'f1_original_weight_coverage': _fmt(f1_coverage), 'f2_original_weight_coverage': _fmt(f2_coverage), 'f3_original_weight_coverage': _fmt(f3_coverage), 'f4_original_weight_coverage': _fmt(f4_coverage), 'employee_signal_status': 'NO_EMPLOYEE_SIGNAL', 'raw_sequential_qoq_primary_weight': '0', 'fastscore_calculated': 'NO', 'source_gate_summary': '|'.join(sorted(blockers[ticker]))})
    present = {row['ticker'] for row in matrix}
    template_fields = list(matrix[0])
    for ticker in sorted(set(universe) - present):
        blank = {field: '' for field in template_fields}
        blank.update({'ticker': ticker, 'cik': universe[ticker], 'productivity_family_class': 'INELIGIBLE', 'capital_family_class': 'INELIGIBLE', 'growth_family_class': 'INELIGIBLE', 'profit_family_class': 'INELIGIBLE', 'cash_family_class': 'INELIGIBLE', 'margin_family_class': 'INELIGIBLE', 'eligible_breadth_families': '0', 'f1_original_weight_coverage': '0', 'f2_original_weight_coverage': '0', 'f3_original_weight_coverage': '0', 'f4_original_weight_coverage': '0', 'employee_signal_status': 'NO_EMPLOYEE_SIGNAL', 'raw_sequential_qoq_primary_weight': '0', 'fastscore_calculated': 'NO', 'source_gate_summary': '|'.join(sorted(blockers[ticker]))})
        matrix.append(blank)
        empty_coverage = {factor: Decimal(0) for factor in ('F1_TTM', 'F2_QUARTER', 'F3_QUALITY', 'F4_ACCELERATION', 'F5_BREADTH')}
        empty_evidence = {'revenue_ttm': False, 'profit_ttm': False, 'cash_ttm': False, 'revenue_q': False, 'profit_q': False, 'operating_margin': False, 'quality_confirmation': False, 'acceleration_family_count': 0, 'breadth_family_count': 0}
        audit.extend(_factor_audit(ticker, empty_coverage, empty_evidence))
    matrix.sort(key=lambda row: row['ticker'])
    audit.sort(key=lambda row: (row['ticker'], row['factor_id']))
    for path, output in ((matrix_path, matrix), (audit_path, audit)):
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('w', newline='', encoding='utf-8') as handle:
            writer = csv.DictWriter(handle, fieldnames=list(output[0]))
            writer.writeheader()
            writer.writerows(output)
    return {'companies': len(matrix), 'factor_rows': len(audit), 'factor_floor_passes': sum((row['floor_status'] == 'PASS' for row in audit))}

def main() -> None:
    return None
if __name__ == '__main__':
    main()

"""Construct governed TTM and year-over-year observations from validated quarters."""
from __future__ import annotations
from ..settings import MODEL_DATE, COHORT_SIZE, WAVE_COUNTS
import argparse
import csv
import json
from collections import Counter, defaultdict
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
PASS_PREFIX = 'PASS_'
QUARTER_ORDER = {'Q1': 1, 'Q2': 2, 'Q3': 3, 'Q4': 4}

def _unit_family(unit_ref: str) -> str:
    normalized = unit_ref.strip().lower()
    return 'USD' if 'usd' in normalized else normalized

def _is_valid(row: dict) -> bool:
    return row['quarter_status'].startswith(PASS_PREFIX) and row['standalone_value'] != ''

def _consecutive(prior: dict, current: dict) -> bool:
    prior_number = QUARTER_ORDER.get(prior['fiscal_quarter'])
    current_number = QUARTER_ORDER.get(current['fiscal_quarter'])
    if prior_number is None or current_number is None:
        return False
    expected = 1 if prior_number == 4 else prior_number + 1
    return current_number == expected and date.fromisoformat(current['quarter_period_start']) == date.fromisoformat(prior['quarter_period_end']) + timedelta(days=1)

def _window_is_consecutive(rows: list[dict]) -> bool:
    return len(rows) >= 1 and all((_consecutive(left, right) for left, right in zip(rows, rows[1:])))

def _change(current: Decimal, prior: Decimal) -> tuple[str, str, str]:
    absolute = current - prior
    if prior > 0:
        return (format(current / prior - Decimal(1), 'f'), format(absolute, 'f'), 'PERCENT_CHANGE')
    return ('', format(absolute, 'f'), 'ABSOLUTE_CHANGE_NONPOSITIVE_BASE')

def _quarter_lineage(rows: list[dict]) -> str:
    return json.dumps([{'fiscal_quarter': row['fiscal_quarter'], 'quarter_period_start': row['quarter_period_start'], 'quarter_period_end': row['quarter_period_end'], 'standalone_value': row['standalone_value'], 'quarter_status': row['quarter_status'], 'construction_method': row['construction_method'], 'latest_parent_model_available_date': row['latest_parent_model_available_date'], 'resolution_id': row.get('resolution_id', '')} for row in rows], separators=(',', ':'), sort_keys=True)

def _derive_fcf_quarters(quarters: list[dict], controls: dict) -> tuple[list[dict], dict]:
    """Derive FCF only where both CFO and capex pass quarter governance."""
    derived = []
    tickers = sorted({ticker for ticker, _ in controls})
    for ticker in tickers:
        cfo_control = controls.get((ticker, 'cash_from_operations'))
        capex_control = controls.get((ticker, 'capital_expenditures'))
        if not cfo_control or not capex_control:
            continue
        dependencies_pass = cfo_control['nine_quarter_requirement_status'] == 'PASS_NINE_QUARTERS' and capex_control['nine_quarter_requirement_status'] == 'PASS_NINE_QUARTERS'
        fcf_status = 'PASS_NINE_QUARTERS' if dependencies_pass else 'DERIVED_FCF_DEPENDENCY_BLOCKED'
        controls[ticker, 'free_cash_flow'] = {'ticker': ticker, 'cik': cfo_control['cik'], 'canonical_concept': 'free_cash_flow', 'nine_quarter_requirement_status': fcf_status}
        if not dependencies_pass:
            continue
        cfo = {(row['quarter_period_start'], row['quarter_period_end']): row for row in quarters if row['ticker'] == ticker and row['canonical_concept'] == 'cash_from_operations' and _is_valid(row)}
        capex = {(row['quarter_period_start'], row['quarter_period_end']): row for row in quarters if row['ticker'] == ticker and row['canonical_concept'] == 'capital_expenditures' and _is_valid(row)}
        for period in sorted(set(cfo) & set(capex), key=lambda item: item[1]):
            cfo_row, capex_row = (cfo[period], capex[period])
            if _unit_family(cfo_row['unit_ref']) != _unit_family(capex_row['unit_ref']) or cfo_row['fiscal_quarter'] != capex_row['fiscal_quarter']:
                continue
            row = dict(cfo_row)
            row['canonical_concept'] = 'free_cash_flow'
            row['mapping_rule_id'] = 'FCF-CFO-MINUS-CAPEX-V0.1'
            row['standalone_value'] = format(Decimal(cfo_row['standalone_value']) - Decimal(capex_row['standalone_value']), 'f')
            row['construction_method'] = 'DERIVED_FCF_CFO_MINUS_CAPEX'
            row['quarter_status'] = 'PASS_DERIVED_FCF'
            row['latest_parent_model_available_date'] = max(cfo_row['latest_parent_model_available_date'], capex_row['latest_parent_model_available_date'])
            row['resolution_id'] = '|'.join(filter(None, sorted({cfo_row.get('resolution_id', ''), capex_row.get('resolution_id', '')})))
            row['parent_lineage_json'] = json.dumps([{'canonical_concept': 'cash_from_operations', 'standalone_value': cfo_row['standalone_value'], 'quarter_status': cfo_row['quarter_status'], 'parent_lineage_json': cfo_row['parent_lineage_json']}, {'canonical_concept': 'capital_expenditures', 'standalone_value': capex_row['standalone_value'], 'quarter_status': capex_row['quarter_status'], 'parent_lineage_json': capex_row['parent_lineage_json']}], separators=(',', ':'), sort_keys=True)
            derived.append(row)
    return (derived, controls)

def construct(quarters_path: Path, quarter_audit_path: Path, observations_path: Path, audit_path: Path) -> dict:
    with quarters_path.open(newline='', encoding='utf-8-sig') as handle:
        quarters = list(csv.DictReader(handle))
    with quarter_audit_path.open(newline='', encoding='utf-8-sig') as handle:
        quarter_audit = list(csv.DictReader(handle))
    controls = {(row['ticker'], row['canonical_concept']): row for row in quarter_audit}
    fcf_quarters, controls = _derive_fcf_quarters(quarters, controls)
    quarters.extend(fcf_quarters)
    by_series = defaultdict(list)
    for row in quarters:
        by_series[row['ticker'], row['canonical_concept']].append(row)
    observations = []
    for key, source_rows in sorted(by_series.items()):
        control = controls[key]
        if control['nine_quarter_requirement_status'] != 'PASS_NINE_QUARTERS':
            continue
        rows = sorted([row for row in source_rows if _is_valid(row)], key=lambda row: (row['quarter_period_end'], row['quarter_period_start']))
        for index, current in enumerate(rows):
            current_value = Decimal(current['standalone_value'])
            prior_quarter = rows[index - 1] if index >= 1 and _consecutive(rows[index - 1], current) else None
            lag4 = rows[index - 4] if index >= 4 else None
            same_quarter_prior = lag4 if lag4 and current['fiscal_quarter'] == lag4['fiscal_quarter'] and _window_is_consecutive(rows[index - 4:index + 1]) else None
            quarter_yoy = quarter_yoy_abs = quarter_yoy_method = ''
            if same_quarter_prior:
                quarter_yoy, quarter_yoy_abs, quarter_yoy_method = _change(current_value, Decimal(same_quarter_prior['standalone_value']))
            qoq = qoq_abs = qoq_method = ''
            if prior_quarter:
                qoq, qoq_abs, qoq_method = _change(current_value, Decimal(prior_quarter['standalone_value']))
            window = rows[index - 3:index + 1] if index >= 3 else []
            valid_ttm = len(window) == 4 and _window_is_consecutive(window)
            ttm_value = sum((Decimal(row['standalone_value']) for row in window), Decimal(0)) if valid_ttm else None
            prior_year_window = rows[index - 7:index - 3] if index >= 7 else []
            valid_prior_ttm = len(prior_year_window) == 4 and _window_is_consecutive(prior_year_window) and (prior_year_window[-1]['fiscal_quarter'] == current['fiscal_quarter'])
            prior_ttm = sum((Decimal(row['standalone_value']) for row in prior_year_window), Decimal(0)) if valid_prior_ttm else None
            ttm_yoy = ttm_yoy_abs = ttm_yoy_method = ''
            if ttm_value is not None and prior_ttm is not None:
                ttm_yoy, ttm_yoy_abs, ttm_yoy_method = _change(ttm_value, prior_ttm)
            previous_observation = observations[-1] if observations and observations[-1]['ticker'] == current['ticker'] and (observations[-1]['canonical_concept'] == current['canonical_concept']) and prior_quarter and (observations[-1]['quarter_period_end'] == prior_quarter['quarter_period_end']) else None
            quarter_acceleration = ''
            quarter_acceleration_absolute = ''
            quarter_acceleration_method = ''
            if quarter_yoy and previous_observation and previous_observation['quarter_yoy_rate']:
                quarter_acceleration = format(Decimal(quarter_yoy) - Decimal(previous_observation['quarter_yoy_rate']), 'f')
                quarter_acceleration_method = 'YOY_RATE_DELTA'
            elif quarter_yoy_abs and previous_observation and previous_observation['quarter_yoy_absolute_change']:
                quarter_acceleration_absolute = format(Decimal(quarter_yoy_abs) - Decimal(previous_observation['quarter_yoy_absolute_change']), 'f')
                quarter_acceleration_method = 'YOY_ABSOLUTE_CHANGE_DELTA_NONPOSITIVE_BASE'
            ttm_acceleration = ''
            ttm_acceleration_absolute = ''
            ttm_acceleration_method = ''
            if ttm_yoy and previous_observation and previous_observation['ttm_yoy_rate']:
                ttm_acceleration = format(Decimal(ttm_yoy) - Decimal(previous_observation['ttm_yoy_rate']), 'f')
                ttm_acceleration_method = 'YOY_RATE_DELTA'
            elif ttm_yoy_abs and previous_observation and previous_observation['ttm_yoy_absolute_change']:
                ttm_acceleration_absolute = format(Decimal(ttm_yoy_abs) - Decimal(previous_observation['ttm_yoy_absolute_change']), 'f')
                ttm_acceleration_method = 'YOY_ABSOLUTE_CHANGE_DELTA_NONPOSITIVE_BASE'
            rollforward_status = 'NOT_APPLICABLE'
            rollforward_difference = ''
            if ttm_value is not None and previous_observation and previous_observation['ttm_value'] and lag4:
                rolled = Decimal(previous_observation['ttm_value']) + current_value - Decimal(lag4['standalone_value'])
                difference = ttm_value - rolled
                rollforward_difference = format(difference, 'f')
                rollforward_status = 'PASS' if difference == 0 else 'FAIL'
            required = [current]
            if same_quarter_prior:
                required.append(same_quarter_prior)
            if valid_ttm:
                required.extend(window)
            if valid_prior_ttm:
                required.extend(prior_year_window)
            available = max((row['latest_parent_model_available_date'] for row in required), default='')
            observations.append({'batch_id': current['batch_id'], 'model_date': current['model_date'], 'ticker': current['ticker'], 'cik': current['cik'], 'canonical_concept': current['canonical_concept'], 'history_view': current['history_view'], 'fiscal_quarter': current['fiscal_quarter'], 'quarter_period_start': current['quarter_period_start'], 'quarter_period_end': current['quarter_period_end'], 'quarter_value': current['standalone_value'], 'unit_ref': current['unit_ref'], 'quarter_yoy_prior_end': same_quarter_prior['quarter_period_end'] if same_quarter_prior else '', 'quarter_yoy_prior_value': same_quarter_prior['standalone_value'] if same_quarter_prior else '', 'quarter_yoy_rate': quarter_yoy, 'quarter_yoy_absolute_change': quarter_yoy_abs, 'quarter_yoy_method': quarter_yoy_method, 'previous_quarter_yoy_rate': previous_observation['quarter_yoy_rate'] if previous_observation else '', 'previous_quarter_yoy_absolute_change': previous_observation['quarter_yoy_absolute_change'] if previous_observation else '', 'quarter_yoy_acceleration': quarter_acceleration, 'quarter_yoy_acceleration_absolute_change': quarter_acceleration_absolute, 'quarter_yoy_acceleration_method': quarter_acceleration_method, 'ttm_value': '' if ttm_value is None else format(ttm_value, 'f'), 'prior_year_ttm_value': '' if prior_ttm is None else format(prior_ttm, 'f'), 'ttm_yoy_rate': ttm_yoy, 'ttm_yoy_absolute_change': ttm_yoy_abs, 'ttm_yoy_method': ttm_yoy_method, 'previous_ttm_yoy_rate': previous_observation['ttm_yoy_rate'] if previous_observation else '', 'previous_ttm_yoy_absolute_change': previous_observation['ttm_yoy_absolute_change'] if previous_observation else '', 'ttm_yoy_acceleration': ttm_acceleration, 'ttm_yoy_acceleration_absolute_change': ttm_acceleration_absolute, 'ttm_yoy_acceleration_method': ttm_acceleration_method, 'sequential_qoq_rate_diagnostic_only': qoq, 'sequential_qoq_absolute_change_diagnostic_only': qoq_abs, 'sequential_qoq_method_diagnostic_only': qoq_method, 'ttm_rollforward_status': rollforward_status, 'ttm_rollforward_difference': rollforward_difference, 'signal_model_available_date': available, 'quarter_source_status': current['quarter_status'], 'quarter_source_resolution_id': current.get('resolution_id', ''), 'quarter_metric_lineage_json': current.get('parent_lineage_json', ''), 'ttm_quarter_lineage_json': _quarter_lineage(window) if valid_ttm else ''})
    with observations_path.open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(observations[0]))
        writer.writeheader()
        writer.writerows(observations)
    audit = []
    for key, control in sorted(controls.items()):
        ticker, canonical = key
        rows = [row for row in observations if row['ticker'] == ticker and row['canonical_concept'] == canonical]
        latest = rows[-1] if rows else None
        rollforward_failures = sum((row['ttm_rollforward_status'] == 'FAIL' for row in rows))
        governance = control['nine_quarter_requirement_status']
        if governance != 'PASS_NINE_QUARTERS':
            status = governance
        elif not rows:
            status = 'NO_ELIGIBLE_OBSERVATIONS'
        elif rollforward_failures:
            status = 'FAIL_TTM_ROLLFORWARD'
        elif not latest['quarter_yoy_method'] or not latest['ttm_yoy_method'] or (not latest['quarter_yoy_acceleration_method']) or (not latest['ttm_yoy_acceleration_method']):
            status = 'INSUFFICIENT_CURRENT_SIGNAL_HISTORY'
        elif 'NONPOSITIVE_BASE' in latest['quarter_yoy_method'] or 'NONPOSITIVE_BASE' in latest['ttm_yoy_method'] or 'NONPOSITIVE_BASE' in latest['quarter_yoy_acceleration_method'] or ('NONPOSITIVE_BASE' in latest['ttm_yoy_acceleration_method']):
            status = 'PASS_CURRENT_FAST_SIGNAL_INPUTS_WITH_ABSOLUTE_CHANGE_FALLBACK'
        else:
            status = 'PASS_CURRENT_FAST_SIGNAL_INPUTS'
        audit.append({'ticker': ticker, 'cik': control['cik'], 'canonical_concept': canonical, 'quarter_governance_status': governance, 'observation_rows': str(len(rows)), 'ttm_observation_count': str(sum((bool(row['ttm_value']) for row in rows))), 'quarter_yoy_count': str(sum((bool(row['quarter_yoy_method']) for row in rows))), 'ttm_yoy_count': str(sum((bool(row['ttm_yoy_method']) for row in rows))), 'quarter_acceleration_count': str(sum((bool(row['quarter_yoy_acceleration_method']) for row in rows))), 'ttm_acceleration_count': str(sum((bool(row['ttm_yoy_acceleration_method']) for row in rows))), 'rollforward_failure_count': str(rollforward_failures), 'latest_quarter_end': latest['quarter_period_end'] if latest else '', 'latest_signal_available_date': latest['signal_model_available_date'] if latest else '', 'current_signal_status': status})
    with audit_path.open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(audit[0]))
        writer.writeheader()
        writer.writerows(audit)
    return {'observation_rows': len(observations), 'ttm_observations': sum((bool(row['ttm_value']) for row in observations)), 'quarter_yoy_observations': sum((bool(row['quarter_yoy_method']) for row in observations)), 'ttm_yoy_observations': sum((bool(row['ttm_yoy_method']) for row in observations)), 'derived_fcf_quarters': len(fcf_quarters), 'rollforward_failures': sum((row['ttm_rollforward_status'] == 'FAIL' for row in observations)), 'audit_statuses': dict(Counter((row['current_signal_status'] for row in audit)))}

def main():
    return None
if __name__ == '__main__':
    main()

"""Construct auditable standalone fiscal quarters from canonical parent periods."""
from __future__ import annotations
import argparse
import csv
import json
from collections import Counter, defaultdict
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

def _compatible(*rows: dict | None) -> bool:
    present = [row for row in rows if row]
    return bool(present) and len({row['canonical_concept'] for row in present}) == 1 and (len({row['mapping_rule_id'] for row in present}) == 1) and (len({row['unit_ref'].lower() for row in present}) == 1)

def _lineage(rows: list[dict]) -> str:
    return json.dumps([{'accession_number': row['accession_number'], 'context_ids': row['context_ids'], 'period_start': row['period_start'], 'period_end': row['period_end'], 'duration_class': row['duration_class'], 'value': row['value'], 'xbrl_decimals': row.get('xbrl_decimals', ''), 'rounding_error_bound': row.get('rounding_error_bound', ''), 'mapping_rule_id': row['mapping_rule_id'], 'source_documents': row['source_documents']} for row in rows], separators=(',', ':'), sort_keys=True)

def _tolerance(rows: list[dict], *values: Decimal) -> Decimal:
    """Allow the combined XBRL rounding bounds plus a tiny numeric floor."""
    largest = max([abs(value) for value in values] + [Decimal(1)])
    precision_bound = sum((Decimal(row.get('rounding_error_bound') or '0') for row in rows), Decimal(0))
    return max(Decimal(1), largest * Decimal('0.000000001'), precision_bound)

def _quarter_row(base: dict, fy_start: str, fy_end: str, quarter: int, period_start: str, period_end: str, value: Decimal | None, method: str, status: str, parents: list[dict], direct: dict | None=None, derived: Decimal | None=None, reconciliation_tolerance: Decimal | None=None, failure_reason: str='') -> dict:
    delta = ''
    if direct is not None and derived is not None:
        delta = format(Decimal(direct['value']) - derived, 'f')
    return {'batch_id': base['batch_id'], 'model_date': base['model_date'], 'ticker': base['ticker'], 'cik': base['cik'], 'canonical_concept': base['canonical_concept'], 'history_view': 'LATEST_RESTATED_AS_OF_MODEL_DATE', 'mapping_rule_id': base['mapping_rule_id'], 'fiscal_year_start': fy_start, 'fiscal_year_end': fy_end, 'fiscal_quarter': f'Q{quarter}', 'quarter_period_start': period_start, 'quarter_period_end': period_end, 'standalone_value': '' if value is None else format(value, 'f'), 'unit_ref': base['unit_ref'], 'construction_method': method, 'quarter_status': status, 'failure_reason': failure_reason, 'direct_minus_derived': delta, 'reconciliation_tolerance': '' if reconciliation_tolerance is None else format(reconciliation_tolerance, 'f'), 'parent_count': str(len(parents)), 'parent_lineage_json': _lineage(parents), 'latest_parent_model_available_date': max((row['model_available_date'] for row in parents), default='')}

def construct(matrix_path: Path, coverage_path: Path, quarters_path: Path, audit_path: Path) -> dict:
    with matrix_path.open(newline='', encoding='utf-8-sig') as handle:
        matrix = list(csv.DictReader(handle))
    with coverage_path.open(newline='', encoding='utf-8-sig') as handle:
        coverage = list(csv.DictReader(handle))
    if any((row['model_available_date'] > row['model_date'] for row in matrix)):
        raise ValueError('Parent matrix contains a filing unavailable on the model date')
    by_series = defaultdict(list)
    for row in matrix:
        by_series[row['ticker'], row['canonical_concept']].append(row)
    quarters = []
    audit = []
    for (ticker, canonical), rows in sorted(by_series.items()):
        direct_by_end = defaultdict(list)
        long_by_start = defaultdict(dict)
        for row in rows:
            if row['duration_class'] == 'QUARTER':
                direct_by_end[row['period_end']].append(row)
            elif row['duration_class'] in {'HALF_YEAR_YTD', 'NINE_MONTH_YTD', 'FISCAL_YEAR'}:
                long_by_start[row['period_start']][row['duration_class']] = row
        for fy_start, parents_by_class in sorted(long_by_start.items()):
            h1 = parents_by_class.get('HALF_YEAR_YTD')
            m9 = parents_by_class.get('NINE_MONTH_YTD')
            fy = parents_by_class.get('FISCAL_YEAR')
            fy_end = fy['period_end'] if fy else ''
            boundary_ends = [row['period_end'] for row in (h1, m9, fy) if row]
            q1_candidates = [row for row in rows if row['duration_class'] == 'QUARTER' and row['period_start'] == fy_start and (row['period_end'] < min(boundary_ends))]
            q1 = min(q1_candidates, key=lambda r: r['period_end']) if q1_candidates else None
            quarter_specs = []
            if q1:
                quarter_specs.append((1, q1['period_start'], q1['period_end'], q1, None, [q1]))
            if h1:
                direct = min(direct_by_end.get(h1['period_end'], []), key=lambda r: r['period_start'], default=None)
                derived = Decimal(h1['value']) - Decimal(q1['value']) if q1 and _compatible(h1, q1) else None
                start = direct['period_start'] if direct else (date.fromisoformat(q1['period_end']) + timedelta(days=1)).isoformat() if q1 else ''
                quarter_specs.append((2, start, h1['period_end'], direct, derived, [r for r in (h1, q1) if r]))
            if m9:
                direct = min(direct_by_end.get(m9['period_end'], []), key=lambda r: r['period_start'], default=None)
                derived = Decimal(m9['value']) - Decimal(h1['value']) if h1 and _compatible(m9, h1) else None
                start = direct['period_start'] if direct else (date.fromisoformat(h1['period_end']) + timedelta(days=1)).isoformat() if h1 else ''
                quarter_specs.append((3, start, m9['period_end'], direct, derived, [r for r in (m9, h1) if r]))
            if fy:
                direct = min(direct_by_end.get(fy['period_end'], []), key=lambda r: r['period_start'], default=None)
                derived = Decimal(fy['value']) - Decimal(m9['value']) if m9 and _compatible(fy, m9) else None
                start = direct['period_start'] if direct else (date.fromisoformat(m9['period_end']) + timedelta(days=1)).isoformat() if m9 else ''
                quarter_specs.append((4, start, fy['period_end'], direct, derived, [r for r in (fy, m9) if r]))
            for quarter, start, end, direct, derived, parents in quarter_specs:
                base = direct or (parents[0] if parents else None)
                if not base:
                    continue
                reconciliation_tolerance = None
                failure_reason = ''
                if quarter == 1:
                    value = Decimal(direct['value'])
                    method = 'DIRECT'
                    status = 'PASS_DIRECT'
                elif direct is not None and derived is not None:
                    direct_value = Decimal(direct['value'])
                    delta = abs(direct_value - derived)
                    reconciliation_tolerance = _tolerance([direct] + parents, direct_value, derived)
                    if delta <= reconciliation_tolerance:
                        value = direct_value
                        method = 'DIRECT_CONFIRMED_BY_DERIVATION'
                        status = 'PASS_DIRECT_DERIVED_RECONCILED'
                    else:
                        value = None
                        method = 'DIRECT_DERIVED_CONFLICT'
                        status = 'REVIEW_DIRECT_DERIVED_MISMATCH'
                        failure_reason = 'DIRECT_DERIVED_OUTSIDE_TOLERANCE'
                    parents = [direct] + parents
                elif direct is not None:
                    value = Decimal(direct['value'])
                    method = 'DIRECT'
                    status = 'PASS_DIRECT'
                    parents = [direct]
                elif derived is not None:
                    value = derived
                    method = f'DERIVED_Q{quarter}'
                    status = 'PASS_DERIVED'
                else:
                    value = None
                    method = 'UNCONSTRUCTED'
                    status = 'MISSING_COMPATIBLE_PARENTS'
                    if len(parents) >= 2:
                        failure_reason = 'INCOMPATIBLE_PARENT_BASIS'
                    else:
                        failure_reason = {2: 'MISSING_Q1_PARENT', 3: 'MISSING_HALF_YEAR_PARENT', 4: 'MISSING_NINE_MONTH_PARENT'}[quarter]
                quarters.append(_quarter_row(base, fy_start, fy_end, quarter, start, end, value, method, status, parents, direct=direct, derived=derived, reconciliation_tolerance=reconciliation_tolerance, failure_reason=failure_reason))
    deduped = {}
    for row in quarters:
        key = (row['ticker'], row['canonical_concept'], row['quarter_period_start'], row['quarter_period_end'])
        prior = deduped.get(key)
        if prior is None or row['latest_parent_model_available_date'] > prior['latest_parent_model_available_date']:
            deduped[key] = row
    quarters = sorted(deduped.values(), key=lambda r: (r['ticker'], r['canonical_concept'], r['quarter_period_end'], r['fiscal_quarter']))
    with quarters_path.open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(quarters[0]))
        writer.writeheader()
        writer.writerows(quarters)
    for control in coverage:
        ticker, canonical = (control['ticker'], control['canonical_concept'])
        source_rows = by_series.get((ticker, canonical), [])
        qrows = [row for row in quarters if row['ticker'] == ticker and row['canonical_concept'] == canonical]
        statuses = Counter((row['quarter_status'] for row in qrows))
        validated = [row for row in qrows if row['quarter_status'].startswith('PASS_') and row['standalone_value'] != '']
        ends = sorted({row['quarter_period_end'] for row in validated})
        parent_status = control['parent_coverage_status']
        if parent_status == 'APPROVED_UNAVAILABLE_V0_1':
            requirement_status = 'APPROVED_UNAVAILABLE_V0_1'
        elif parent_status == 'INSUFFICIENT_HISTORY':
            requirement_status = 'INSUFFICIENT_HISTORY_GOVERNANCE'
        else:
            requirement_status = 'PASS_NINE_QUARTERS' if len(validated) >= 9 else 'INSUFFICIENT_VALIDATED_QUARTERS'
        audit.append({'ticker': ticker, 'cik': control['cik'], 'canonical_concept': canonical, 'parent_coverage_status': parent_status, 'governance_rule_id': control['mapping_rule_id'], 'constructed_quarter_rows': str(len(qrows)), 'validated_quarter_count': str(len(validated)), 'earliest_validated_quarter_end': ends[0] if ends else '', 'latest_validated_quarter_end': ends[-1] if ends else '', 'pass_direct_count': str(statuses['PASS_DIRECT']), 'pass_reconciled_count': str(statuses['PASS_DIRECT_DERIVED_RECONCILED']), 'pass_derived_count': str(statuses['PASS_DERIVED']), 'review_mismatch_count': str(statuses['REVIEW_DIRECT_DERIVED_MISMATCH']), 'missing_parent_count': str(statuses['MISSING_COMPATIBLE_PARENTS']), 'nine_quarter_requirement_status': requirement_status})
    with audit_path.open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(audit[0]))
        writer.writeheader()
        writer.writerows(audit)
    return {'quarter_rows': len(quarters), 'validated_quarters': sum((r['quarter_status'].startswith('PASS_') for r in quarters)), 'quarter_statuses': dict(Counter((r['quarter_status'] for r in quarters))), 'audit_cells': len(audit), 'nine_quarter_pass_cells': sum((r['nine_quarter_requirement_status'] == 'PASS_NINE_QUARTERS' for r in audit))}

def main():
    return None
if __name__ == '__main__':
    main()

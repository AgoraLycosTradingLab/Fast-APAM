"""Construct candidate quarters and YoY/TTM signals from reviewed SEC parents.

The source rows remain unapproved for scoring until dated peer evidence and
combined-cohort coverage checks pass.
"""
import csv
import json
from collections import defaultdict
from pathlib import Path

from .canonical_preparation import _rows, _write, PARENT_FIELDS
from .engine.standalone_quarter_construction import construct as construct_quarters
from .engine.ttm_yoy_construction import construct as construct_ttm, _window_is_consecutive


def construct_signals(preparation_folder):
    folder = Path(preparation_folder)
    manifest = json.loads((folder / 'preparation.json').read_text(encoding='utf-8'))
    day = manifest['model_date']
    canonical_rows = _rows(folder / 'canonical_facts.csv')
    targets = _rows(folder / 'filing_targets.csv')
    latest_target = {}
    for row in targets:
        if row['model_available_date'] > day:
            raise ValueError('Filing target violates model-date cutoff')
        latest_target[row['ticker']] = max(latest_target.get(row['ticker'], ''), row['report_period'])
    grouped = defaultdict(list)
    for row in canonical_rows:
        if row['model_date'] != day or row['model_available_date'] > day or row['selection_status'] != 'SELECTED_CONTEXT_VERIFIED_CANDIDATE':
            raise ValueError('Canonical parent is not eligible for candidate construction')
        grouped[row['ticker'], row['canonical_concept'], row['period_start'], row['period_end']].append(row)
    parents, conflicts = [], []
    for key, versions in sorted(grouped.items()):
        latest = max(row['model_available_date'] for row in versions)
        available = [row for row in versions if row['model_available_date'] == latest]
        if len({(row['value'], row['mapping_rule_id'], row['unit_ref']) for row in available}) != 1:
            conflicts.append({'ticker': key[0], 'canonical_concept': key[1],
                              'period_start': key[2], 'period_end': key[3],
                              'reason': 'CONFLICTING_LATEST_PARENT_VINTAGE'})
            continue
        parents.append(max(available, key=lambda row: (row['accepted_timestamp_utc'], row['accession_number'])))
    _write(folder / 'parent_matrix.csv', parents, PARENT_FIELDS)
    _write(folder / 'parent_selection_audit.csv', conflicts,
           ['ticker', 'canonical_concept', 'period_start', 'period_end', 'reason'])
    by_series = defaultdict(list)
    for row in parents:
        by_series[row['ticker'], row['canonical_concept']].append(row)
    ticker_cik = {row['ticker']: row['cik'] for row in targets}
    coverage = []
    for ticker, cik in sorted(ticker_cik.items()):
        for canonical in ('revenue', 'operating_income', 'cash_from_operations', 'capital_expenditures'):
            rows = by_series[ticker, canonical]
            coverage.append({'ticker': ticker, 'cik': cik, 'canonical_concept': canonical,
                             'parent_coverage_status': 'CANDIDATE_CONTEXT_VERIFIED' if rows else 'INSUFFICIENT_HISTORY',
                             'mapping_rule_id': rows[-1]['mapping_rule_id'] if rows else '',
                             'parent_count': str(len(rows))})
    _write(folder / 'parent_coverage.csv', coverage,
           ['ticker', 'cik', 'canonical_concept', 'parent_coverage_status', 'mapping_rule_id', 'parent_count'])
    summary = {'model_date': day, 'canonical_parent_count': len(canonical_rows),
               'selected_parent_count': len(parents), 'parent_conflict_count': len(conflicts),
               'quarter_count': 0, 'ttm_yoy_observation_count': 0, 'rollforward_failures': 0,
               'ready_to_score': False}
    if not any(row['duration_class'] in {'HALF_YEAR_YTD', 'NINE_MONTH_YTD', 'FISCAL_YEAR'} for row in parents):
        _write(folder / 'standalone_quarters.csv', [], ['model_date', 'ticker', 'canonical_concept', 'quarter_status'])
        _write(folder / 'quarter_audit.csv', [], ['ticker', 'canonical_concept', 'nine_quarter_requirement_status'])
        _write(folder / 'ttm_yoy_observations.csv', [], ['model_date', 'ticker', 'canonical_concept', 'current_signal_status'])
        _write(folder / 'ttm_yoy_audit.csv', [], ['ticker', 'canonical_concept', 'current_signal_status'])
    else:
        construct_quarters(folder / 'parent_matrix.csv', folder / 'parent_coverage.csv',
                           folder / 'standalone_quarters.csv', folder / 'quarter_audit.csv')
        quarters = _rows(folder / 'standalone_quarters.csv')
        summary['quarter_count'] = len(quarters)
        audit = _rows(folder / 'quarter_audit.csv')
        for control in audit:
            if control['parent_coverage_status'] == 'INSUFFICIENT_HISTORY':
                continue
            rows = sorted((row for row in quarters if row['ticker'] == control['ticker'] and
                           row['canonical_concept'] == control['canonical_concept'] and
                           row['quarter_status'].startswith('PASS_') and row['standalone_value']),
                          key=lambda row: row['quarter_period_end'])
            window = rows[-9:]
            if (len(window) != 9 or not _window_is_consecutive(window) or
                    window[-1]['quarter_period_end'] != latest_target.get(control['ticker'])):
                control['nine_quarter_requirement_status'] = 'INSUFFICIENT_VALIDATED_CURRENT_QUARTERS'
        _write(folder / 'quarter_audit.csv', audit, list(audit[0]))
        if any(row['nine_quarter_requirement_status'] == 'PASS_NINE_QUARTERS' for row in audit):
            result = construct_ttm(folder / 'standalone_quarters.csv', folder / 'quarter_audit.csv',
                                   folder / 'ttm_yoy_observations.csv', folder / 'ttm_yoy_audit.csv')
            summary['ttm_yoy_observation_count'] = result['observation_rows']
            summary['rollforward_failures'] = result['rollforward_failures']
        else:
            _write(folder / 'ttm_yoy_observations.csv', [], ['model_date', 'ticker', 'canonical_concept', 'current_signal_status'])
            _write(folder / 'ttm_yoy_audit.csv',
                   [{'ticker': row['ticker'], 'canonical_concept': row['canonical_concept'],
                     'current_signal_status': row['nine_quarter_requirement_status']} for row in audit],
                   ['ticker', 'canonical_concept', 'current_signal_status'])
    (folder / 'signal_preparation.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
    return summary

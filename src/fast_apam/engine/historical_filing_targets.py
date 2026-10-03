"""Build the point-in-time historical filing target set for quarter construction."""
from __future__ import annotations
from ..settings import MODEL_DATE, COHORT_SIZE, WAVE_COUNTS
import argparse
import csv
import json
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
PERIOD_WINDOW = 12
MINIMUM_STANDALONE_QUARTERS = 9

def _latest_vintage(rows: list[dict]) -> dict:
    return max(rows, key=lambda r: (r['model_available_date'], r['accepted_timestamp_utc'], r['accession_number']))

def build_targets(index_path: Path, targets_path: Path, audit_path: Path):
    with index_path.open(newline='', encoding='utf-8-sig') as handle:
        rows = list(csv.DictReader(handle))
    eligible = [row for row in rows if row['eligible_on_model_date'] == 'Y' and row['index_status'] == 'ELIGIBLE' and (row['form_type'] in {'10-Q', '10-K', '10-Q/A', '10-K/A'}) and (row['is_inline_xbrl'] == '1')]
    grouped: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for row in eligible:
        grouped[row['ticker'], row['report_period']].append(row)
    selected = []
    vintage_superseded = 0
    by_ticker_periods: dict[str, list[tuple[str, dict]]] = defaultdict(list)
    for (ticker, report_period), candidates in grouped.items():
        chosen = _latest_vintage(candidates)
        vintage_superseded += len(candidates) - 1
        by_ticker_periods[ticker].append((report_period, chosen))
    audit = []
    for ticker, periods in sorted(by_ticker_periods.items()):
        periods.sort(key=lambda item: item[0], reverse=True)
        window = periods[:PERIOD_WINDOW]
        window.reverse()
        forms = Counter((row['form_type'].replace('/A', '') for _, row in window))
        report_periods = [period for period, _ in window]
        dates = [date.fromisoformat(period) for period in report_periods]
        span_days = (max(dates) - min(dates)).days if dates else 0
        q_count = forms['10-Q']
        k_count = forms['10-K']
        sequence_status = 'PASS_TARGET_HISTORY' if len(window) == PERIOD_WINDOW and q_count >= 8 and (k_count >= 2) and (span_days >= 900) else 'REVIEW_HISTORY_GAP'
        for sequence_number, (report_period, row) in enumerate(window, start=1):
            out = dict(row)
            out.update({'historical_window_periods': str(PERIOD_WINDOW), 'history_sequence_number': str(sequence_number), 'history_sequence_status': sequence_status, 'selected_vintage_rule': 'LATEST_ELIGIBLE_VINTAGE_PER_REPORT_PERIOD'})
            selected.append(out)
        audit.append({'batch_id': window[-1][1]['batch_id'] if window else '', 'model_date': window[-1][1]['model_date'] if window else '', 'ticker': ticker, 'cik': window[-1][1]['cik'] if window else '', 'company_name': window[-1][1]['company_name'] if window else '', 'selected_report_periods': str(len(window)), 'ten_q_count': str(q_count), 'ten_k_count': str(k_count), 'earliest_report_period': report_periods[0] if report_periods else '', 'latest_report_period': report_periods[-1] if report_periods else '', 'history_span_days': str(span_days), 'minimum_standalone_quarter_target': str(MINIMUM_STANDALONE_QUARTERS), 'target_history_status': sequence_status, 'review_note': '' if sequence_status == 'PASS_TARGET_HISTORY' else 'Inspect issuer history, form sequence, or corporate-history boundary before retrieval'})
    selected.sort(key=lambda r: (r['ticker'], r['report_period'], r['model_available_date'], r['accession_number']))
    if not selected:
        raise ValueError('No eligible inline periodic filings were selected')
    with targets_path.open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(selected[0]))
        writer.writeheader()
        writer.writerows(selected)
    with audit_path.open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(audit[0]))
        writer.writeheader()
        writer.writerows(audit)
    return {'issuer_count': len(audit), 'selected_filing_count': len(selected), 'superseded_vintages_excluded': vintage_superseded, 'status_counts': dict(Counter((row['target_history_status'] for row in audit))), 'form_counts': dict(Counter((row['form_type'] for row in selected)))}

def main():
    return None
if __name__ == '__main__':
    main()

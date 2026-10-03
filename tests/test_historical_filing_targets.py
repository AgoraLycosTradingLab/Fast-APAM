import os
from pathlib import Path
os.environ.setdefault("FAST_APAM_RUN_CONFIG", str(Path(__file__).with_name("unit-config.json")))
import csv
import tempfile
import unittest
from pathlib import Path
from fast_apam.engine.historical_filing_targets import build_targets
FIELDS = ['batch_id', 'model_date', 'ticker', 'company_name', 'cik', 'report_period', 'model_available_date', 'accepted_timestamp_utc', 'accession_number', 'form_type', 'eligible_on_model_date', 'index_status', 'is_inline_xbrl']

def _row(period, form, accession, available=None):
    return {'batch_id': 'B', 'model_date': '2026-07-31', 'ticker': 'ABC', 'company_name': 'ABC Inc', 'cik': '0000000001', 'report_period': period, 'model_available_date': available or period, 'accepted_timestamp_utc': (available or period) + 'T12:00:00+00:00', 'accession_number': accession, 'form_type': form, 'eligible_on_model_date': 'Y', 'index_status': 'ELIGIBLE', 'is_inline_xbrl': '1'}

class HistoricalFilingTargetTests(unittest.TestCase):

    def test_selects_latest_vintage_and_twelve_period_window(self):
        periods = [('2023-06-30', '10-Q'), ('2023-09-30', '10-Q'), ('2023-12-31', '10-K'), ('2024-03-31', '10-Q'), ('2024-06-30', '10-Q'), ('2024-09-30', '10-Q'), ('2024-12-31', '10-K'), ('2025-03-31', '10-Q'), ('2025-06-30', '10-Q'), ('2025-09-30', '10-Q'), ('2025-12-31', '10-K'), ('2026-03-31', '10-Q'), ('2026-06-30', '10-Q')]
        rows = [_row(p, f, f'A{i:02d}') for i, (p, f) in enumerate(periods)]
        rows.append(_row('2025-12-31', '10-K/A', 'AMENDED', '2026-03-01'))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, targets, audit = (root / 'index.csv', root / 'targets.csv', root / 'audit.csv')
            with source.open('w', newline='') as handle:
                writer = csv.DictWriter(handle, fieldnames=FIELDS)
                writer.writeheader()
                writer.writerows(rows)
            result = build_targets(source, targets, audit)
            with targets.open(newline='') as handle:
                selected = list(csv.DictReader(handle))
        self.assertEqual(result['selected_filing_count'], 12)
        self.assertEqual(result['superseded_vintages_excluded'], 1)
        self.assertEqual(selected[0]['report_period'], '2023-09-30')
        self.assertEqual(next((r for r in selected if r['report_period'] == '2025-12-31'))['accession_number'], 'AMENDED')
        self.assertEqual(result['status_counts'], {'PASS_TARGET_HISTORY': 1})

    def test_short_history_is_visible_review_not_silent_pass(self):
        rows = [_row('2025-03-31', '10-Q', 'A1'), _row('2025-06-30', '10-Q', 'A2')]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, targets, audit = (root / 'index.csv', root / 'targets.csv', root / 'audit.csv')
            with source.open('w', newline='') as handle:
                writer = csv.DictWriter(handle, fieldnames=FIELDS)
                writer.writeheader()
                writer.writerows(rows)
            result = build_targets(source, targets, audit)
            with audit.open(newline='') as handle:
                review_note = list(csv.DictReader(handle))[0]['review_note']
        self.assertEqual(result['status_counts'], {'REVIEW_HISTORY_GAP': 1})
        self.assertTrue(review_note)
if __name__ == '__main__':
    unittest.main()

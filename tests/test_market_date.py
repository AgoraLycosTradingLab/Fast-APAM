import contextlib
import io
import json
from datetime import datetime, timezone
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from fast_apam.market_date import EASTERN, resolve_model_date
from fast_apam.cli import main
from fast_apam.runner import publish, PREFIX


class MarketDateTests(unittest.TestCase):
    def resolve(self, requested, clock='2026-10-04T12:00:00-04:00'):
        return resolve_model_date(requested, now=datetime.fromisoformat(clock))

    def test_weekend_returns_friday_and_records_requested_date(self):
        for requested in ['2026-09-26', '2026-09-27']:
            result = self.resolve(requested)
            self.assertEqual(result['effective_model_date'], '2026-09-25')
            self.assertEqual(result['requested_date'], requested)
            self.assertEqual(result['adjustment_reason'], 'WEEKEND')

    def test_holiday_weekend_skips_observed_holiday(self):
        for requested in ['2026-07-03', '2026-07-04', '2026-07-05']:
            self.assertEqual(self.resolve(requested)['effective_model_date'], '2026-07-02')

    def test_good_friday_and_labor_day(self):
        for requested, expected in [('2026-04-03', '2026-04-02'), ('2026-09-07', '2026-09-04')]:
            self.assertEqual(self.resolve(requested)['effective_model_date'], expected)

    def test_special_2025_closure(self):
        self.assertEqual(self.resolve('2025-01-09')['effective_model_date'], '2025-01-08')

    def test_valid_historical_date_unchanged(self):
        result = self.resolve('2026-09-25')
        self.assertEqual(result['effective_model_date'], '2026-09-25')
        self.assertFalse(result['adjusted'])

    def test_today_before_close(self):
        result = self.resolve('2026-10-02', '2026-10-02T15:59:59-04:00')
        self.assertEqual(result['effective_model_date'], '2026-10-01')
        self.assertEqual(result['adjustment_reason'], 'SESSION_NOT_CLOSED')

    def test_exact_regular_close(self):
        self.assertEqual(self.resolve('latest', '2026-10-02T16:00:00-04:00')['effective_model_date'], '2026-10-02')

    def test_latest_on_weekend(self):
        self.assertEqual(self.resolve('latest')['effective_model_date'], '2026-10-02')

    def test_early_close_boundary(self):
        for clock, expected in [('2025-11-28T12:59:59-05:00', '2025-11-26'),
                                ('2025-11-28T13:00:00-05:00', '2025-11-28')]:
            result = self.resolve('latest', clock)
            self.assertEqual(result['effective_model_date'], expected)

    def test_july_and_christmas_early_closes(self):
        for day in ['2023-07-03', '2024-07-03', '2024-12-24', '2025-07-03', '2026-12-24', '2028-07-03']:
            result = self.resolve(day, day + 'T14:00:00-04:00')
            # December 14:00 EDT is 13:00 EST, the completed early close.
            self.assertEqual(result['effective_model_date'], day)
            self.assertIn('T13:00:00', result['session_close_eastern'])

    def test_new_year_weekend_has_no_friday_holiday_in_2027(self):
        self.assertEqual(self.resolve('2028-01-01', '2028-01-02T12:00:00-05:00')['effective_model_date'], '2027-12-31')

    def test_timezone_conversion_across_utc_midnight(self):
        self.assertEqual(self.resolve('latest', '2026-10-03T01:00:00+00:00')['effective_model_date'], '2026-10-02')

    def test_dst_offset_changes(self):
        self.assertTrue(self.resolve('2026-03-06')['session_close_eastern'].endswith('-05:00'))
        self.assertTrue(self.resolve('2026-03-09')['session_close_eastern'].endswith('-04:00'))

    def test_future_date_rejected(self):
        with self.assertRaisesRegex(ValueError, 'future'):
            self.resolve('2026-10-05')

    def test_invalid_and_unsupported_dates(self):
        for value in ['09/25/2026', '20260925', '2026-02-30', '2022-12-30']:
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.resolve(value)
        with self.assertRaisesRegex(ValueError, 'calendar'):
            self.resolve('latest', '2029-01-05T17:00:00-05:00')

    def test_naive_clock_rejected(self):
        with self.assertRaisesRegex(ValueError, 'timezone'):
            resolve_model_date('latest', now=datetime(2026, 10, 4))

    def test_cli_resolve_does_not_open_store(self):
        output = io.StringIO()
        with patch('sys.argv', ['fast-apam', 'resolve-date', '--date', '2026-09-27']), \
             patch('fast_apam.cli.Store') as store, contextlib.redirect_stdout(output):
            self.assertEqual(main(), 0)
            store.assert_not_called()
        self.assertEqual(json.loads(output.getvalue())['effective_model_date'], '2026-09-25')

    def test_cli_run_uses_effective_date_for_source_and_scoring(self):
        with patch('sys.argv', ['fast-apam', 'run', '--date', '2026-09-27', '--source', 'source', '--output', 'output']), \
             patch('fast_apam.cli.Store') as store, patch('fast_apam.cli.import_source') as load, \
             patch('fast_apam.cli.publish', return_value={}) as run, \
             contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(main(), 0)
            self.assertEqual(load.call_args.args[1], '2026-09-25')
            self.assertEqual(run.call_args.args[1], '2026-09-25')
            self.assertEqual(run.call_args.kwargs['date_resolution']['requested_date'], '2026-09-27')

    def test_result_metadata_records_adjustment_without_changing_results(self):
        resolution = self.resolve('2026-09-27')
        data = b'ticker,score_published\nTEST,YES\n'
        outputs = {PREFIX + 'Research_Pilot_Output_2026-09-25_R1.csv': data}
        with tempfile.TemporaryDirectory() as temporary, \
             patch('fast_apam.runner.calculate', return_value=('id', {}, outputs)):
            folder = Path(temporary) / 'output'
            publish(None, '2026-09-25', folder, date_resolution=resolution)
            self.assertEqual((folder / 'results.csv').read_bytes(), data)
            self.assertEqual(json.loads((folder / 'run.json').read_text())['date_resolution'], resolution)

    def test_mismatched_resolution_rejected_before_calculation(self):
        with patch('fast_apam.runner.calculate') as calculate, self.assertRaises(ValueError):
            publish(None, '2026-09-24', 'unused', date_resolution=self.resolve('2026-09-27'))
        calculate.assert_not_called()

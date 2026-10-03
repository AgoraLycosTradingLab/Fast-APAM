import os
from pathlib import Path
os.environ.setdefault("FAST_APAM_RUN_CONFIG", str(Path(__file__).with_name("unit-config.json")))
import unittest
from datetime import date, datetime, timezone
from fast_apam.engine.sec_filing_index import calculate_availability, is_nyse_trading_day

class FilingAvailabilityTests(unittest.TestCase):

    def test_msft_q4_after_close_fixture(self):
        accepted = datetime(2026, 7, 29, 20, 8, 1, tzinfo=timezone.utc)
        result = calculate_availability(accepted)
        self.assertEqual(result.buffer_trading_day, date(2026, 7, 30))
        self.assertEqual(result.model_available_date, date(2026, 7, 31))

    def test_broadridge_mid_session_fixture(self):
        accepted = datetime(2026, 4, 30, 15, 40, 35, tzinfo=timezone.utc)
        result = calculate_availability(accepted)
        self.assertEqual(result.buffer_trading_day, date(2026, 5, 1))
        self.assertEqual(result.model_available_date, date(2026, 5, 4))

    def test_preopen_acceptance_uses_same_session_as_buffer(self):
        accepted = datetime(2026, 7, 29, 12, 0, 0, tzinfo=timezone.utc)
        result = calculate_availability(accepted)
        self.assertEqual(result.buffer_trading_day, date(2026, 7, 29))
        self.assertEqual(result.model_available_date, date(2026, 7, 30))

    def test_good_friday_is_closed(self):
        self.assertFalse(is_nyse_trading_day(date(2026, 4, 3)))

    def test_juneteenth_is_closed(self):
        self.assertFalse(is_nyse_trading_day(date(2026, 6, 19)))
if __name__ == '__main__':
    unittest.main()

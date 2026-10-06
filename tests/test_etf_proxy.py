import csv
import tempfile
import unittest
from pathlib import Path

from fast_apam.etf_proxy import build_proxy, parse_holdings
from fast_apam.cohort_preparation import prepare_cohort_batch


def sample(as_of='Sep 17, 2026', *, duplicate=False, unknown=False):
    rows = [
        'iShares Core S&P 500 ETF',
        f'Fund Holdings as of,"{as_of}"',
        'Ticker,Name,Sector,Asset Class',
        'MSFT,Microsoft,Information Technology,Equity',
        'JPM,JPMorgan,Financials,Equity',
        'USD,US Dollar,Cash and/or Derivatives,Cash',
    ]
    if duplicate:
        rows.append('MSFT,Microsoft second,Information Technology,Equity')
    if unknown:
        rows.append('ODD,Odd Corp,Future Sector,Equity')
    return ('\n'.join(rows) + '\n').encode()


class EtfProxyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'universe.csv').write_text('ticker\nMSFT\nNOTHERE\n', encoding='utf-8')

    def run_proxy(self, payload=None, day='2026-09-17', **kwargs):
        path = self.root / 'holdings.csv'
        path.write_bytes(payload or sample())
        return build_proxy(self.root / 'universe.csv', day, self.root / 'output',
                           holdings_file=path, min_equity_holdings=1, **kwargs)

    def test_parses_and_audits_missing_requested_and_cash(self):
        result = self.run_proxy()
        self.assertEqual(result['cohort_size'], 2)
        self.assertEqual(result['requested_in_proxy_count'], 1)
        self.assertFalse(result['ready_to_score'])
        with (self.root / 'output' / 'etf_proxy_audit.csv').open(newline='') as handle:
            statuses = {row['status'] for row in csv.DictReader(handle)}
        self.assertIn('EXCLUDED_NON_EQUITY', statuses)
        self.assertIn('REQUESTED_NOT_IN_PROXY', statuses)

    def test_future_and_stale_source_blocked(self):
        with self.assertRaisesRegex(ValueError, 'look-ahead'):
            self.run_proxy(day='2026-09-16')
        with self.assertRaisesRegex(ValueError, 'days old'):
            self.run_proxy(day='2026-10-05')
        self.assertFalse((self.root / 'output').exists())

    def test_duplicate_and_unknown_sector_are_excluded(self):
        result = self.run_proxy(sample(duplicate=True, unknown=True))
        self.assertEqual(result['cohort_size'], 1)
        with (self.root / 'output' / 'etf_proxy_audit.csv').open(newline='') as handle:
            statuses = [row['status'] for row in csv.DictReader(handle)]
        self.assertEqual(statuses.count('REVIEW_DUPLICATE_TICKER'), 2)
        self.assertIn('REVIEW_UNKNOWN_SECTOR', statuses)

    def test_historical_archive_does_not_download_current_file(self):
        cache = self.root / 'cache'
        cache.mkdir()
        payload = sample()
        import hashlib
        digest = hashlib.sha256(payload).hexdigest()
        (cache / f'IVV_2026-09-17_{digest}.csv').write_bytes(payload)
        def no_download(_):
            raise AssertionError('historical archive must be used')
        result = build_proxy(self.root / 'universe.csv', '2026-09-17',
                             self.root / 'output', cache_dir=cache,
                             transport=no_download, min_equity_holdings=1)
        self.assertEqual(result['source_sha256'], digest)

    def test_bad_fund_and_repeat_output_fail(self):
        with self.assertRaisesRegex(ValueError, 'expected IVV'):
            parse_holdings(sample().replace(b'iShares Core', b'Other Fund'))
        self.run_proxy()
        with self.assertRaisesRegex(ValueError, 'new or empty'):
            self.run_proxy()

    def test_batch_selects_audited_sector_and_reuses_sec_acquisition(self):
        self.run_proxy(sample().replace(
            b'JPM,JPMorgan,Financials,Equity',
            b'AAPL,Apple,Information Technology,Equity\nJPM,JPMorgan,Financials,Equity'))
        seen = []
        def acquire(universe, model_date, output, history_start=None, progress=None):
            seen.append((Path(universe).read_text(), model_date, str(output)))
            return {'status': 'CANDIDATES_ACQUIRED_NOT_SCORE_READY',
                    'issuer_candidate_count': 1, 'candidate_fact_count': 10}
        result = prepare_cohort_batch(self.root / 'output', self.root / 'batch',
            'Information Technology', batch_number=2, batch_size=1, acquisition=acquire)
        self.assertEqual(result['selected_tickers'], ['AAPL'])
        self.assertEqual(result['status'], 'SEC_CANDIDATES_ACQUIRED_NOT_SCORE_READY')
        self.assertEqual(seen[0][0], 'ticker\nAAPL\n')
        self.assertEqual(seen[0][1], '2026-09-17')
        self.assertFalse(result['ready_to_score'])

    def test_batch_checksum_and_nonempty_output_protection(self):
        self.run_proxy()
        cohort = self.root / 'output' / 'etf_proxy_cohort.csv'
        cohort.write_text(cohort.read_text() + 'TAMPER\n')
        with self.assertRaisesRegex(ValueError, 'checksum mismatch'):
            prepare_cohort_batch(self.root / 'output', self.root / 'batch',
                                 'Information Technology', plan_only=True)
        self.assertFalse((self.root / 'batch').exists())

    def test_plan_only_and_out_of_range_batch(self):
        self.run_proxy()
        with self.assertRaisesRegex(ValueError, 'Batch number'):
            prepare_cohort_batch(self.root / 'output', self.root / 'batch',
                                 'Information Technology', batch_number=2,
                                 batch_size=1, plan_only=True)
        result = prepare_cohort_batch(self.root / 'output', self.root / 'batch',
            'Financials', plan_only=True)
        self.assertEqual(result['selected_tickers'], ['JPM'])
        self.assertEqual(result['status'], 'BATCH_PLANNED')
        with self.assertRaisesRegex(ValueError, 'new or empty'):
            prepare_cohort_batch(self.root / 'output', self.root / 'batch',
                                 'Financials', plan_only=True)


if __name__ == '__main__':
    unittest.main()

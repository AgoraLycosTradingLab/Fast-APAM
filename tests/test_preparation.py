import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from fast_apam.preparation import prepare, TICKERS_URL, SecSession
from fast_apam.cli import main


class PreparationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.universe = self.root / 'universe.csv'
        self.universe.write_text('ticker\nTEST\n', encoding='utf-8')
        self.output = self.root / 'output'
        self.calls = []
        self.acc = '0000000001-26-000001'
        self.future_acc = '0000000001-26-000002'
        self.filing = dict(accessionNumber=self.acc, form='10-Q',
            filingDate='2026-07-29', reportDate='2026-06-30',
            acceptanceDateTime='2026-07-29T20:08:01Z', primaryDocument='report.htm',
            isXBRL=1, isInlineXBRL=1)
        self.submission = {'cik': 1, 'name': 'Synthetic Co', 'fiscalYearEnd': '1231',
            'filings': {'recent': {k: [v] for k, v in self.filing.items()}, 'files': []}}
        self.facts = {'cik': 1, 'facts': {'us-gaap': {'Revenues': {'units': {'USD': [
            {'accn': self.acc, 'start': '2026-01-01', 'end': '2026-06-30', 'val': 120},
            {'accn': self.future_acc, 'start': '2026-01-01', 'end': '2026-06-30', 'val': 900},
        ]}}}}}
        self.tickers = {'0': {'ticker': 'TEST', 'cik_str': 1, 'title': 'Synthetic Co'}}
        credential = patch('fast_apam.preparation.sec_user_agent', return_value='PRIVATE_TEST_IDENTIFIER')
        credential.start()
        self.addCleanup(credential.stop)
        sleep = patch('fast_apam.preparation.time.sleep')
        sleep.start()
        self.addCleanup(sleep.stop)

    def transport(self, url, identity):
        self.assertEqual(identity, 'PRIVATE_TEST_IDENTIFIER')
        self.calls.append(url)
        if url == TICKERS_URL:
            value = self.tickers
        elif 'companyfacts' in url:
            value = self.facts
        elif '-submissions-' in url:
            value = {k: [v] for k, v in self.filing.items()}
        else:
            value = self.submission
        return json.dumps(value).encode()

    def run_prepare(self):
        return prepare(self.universe, '2026-07-31', self.output, transport=self.transport)

    def test_candidates_preserve_lineage_and_never_approve_scoring(self):
        result = self.run_prepare()
        self.assertEqual(result['status'], 'CANDIDATES_ACQUIRED_NOT_SCORE_READY')
        self.assertEqual(result['candidate_fact_count'], 1)
        self.assertEqual(result['eligible_filing_count'], 1)
        self.assertFalse(result['ready_to_score'])
        self.assertEqual(len(result['sources']), 3)
        text = (self.output / 'candidate_facts.csv').read_text()
        self.assertIn('ACQUIRED_UNVALIDATED_CONTEXT', text)
        self.assertIn(self.acc, text)
        self.assertNotIn(self.future_acc, text)
        for path in self.output.rglob('*'):
            if path.is_file():
                self.assertNotIn('PRIVATE_TEST_IDENTIFIER', path.read_text())

    def test_filing_after_cutoff_cannot_supply_candidate_facts(self):
        future = dict(self.filing, accessionNumber=self.future_acc,
            filingDate='2026-07-31', acceptanceDateTime='2026-07-31T20:00:00Z')
        for key, value in future.items():
            self.submission['filings']['recent'][key].append(value)
        result = self.run_prepare()
        self.assertEqual(result['filing_count'], 2)
        self.assertEqual(result['eligible_filing_count'], 1)
        self.assertEqual(result['candidate_fact_count'], 1)
        self.assertIn('EXCLUDED_LOOKAHEAD', (self.output / 'filing_index.csv').read_text())

    def test_older_submission_pages_are_retrieved(self):
        self.submission['filings']['recent'] = {}
        self.submission['filings']['files'] = [{'name': 'CIK0000000001-submissions-001.json',
            'filingFrom': '2024-01-01', 'filingTo': '2026-07-31'}]
        self.assertEqual(self.run_prepare()['eligible_filing_count'], 1)
        self.assertTrue(any('-submissions-001.json' in url for url in self.calls))

    def test_exact_duplicate_archive_filing_is_deduplicated(self):
        self.submission['filings']['files'] = [{'name': 'CIK0000000001-submissions-001.json',
            'filingFrom': '2024-01-01', 'filingTo': '2026-07-31'}]
        self.assertEqual(self.run_prepare()['filing_count'], 1)

    def test_unknown_ticker_is_audited_without_alias_guessing(self):
        self.universe.write_text('ticker\nTEST.A\n')
        result = self.run_prepare()
        self.assertEqual(result['issuer_candidate_count'], 0)
        self.assertIn('UNKNOWN_TICKER', (self.output / 'preparation_exceptions.csv').read_text())
        self.assertEqual(len(self.calls), 1)

    def test_ambiguous_ticker_does_not_select_an_issuer(self):
        self.tickers['1'] = {'ticker': 'TEST', 'cik_str': 2, 'title': 'Other issuer'}
        self.assertEqual(self.run_prepare()['issuer_candidate_count'], 0)
        self.assertIn('AMBIGUOUS_TICKER', (self.output / 'preparation_exceptions.csv').read_text())

    def test_identity_mismatch_blocks_facts(self):
        self.submission['cik'] = 2
        result = self.run_prepare()
        self.assertEqual(result['status'], 'INCOMPLETE')
        self.assertEqual(result['candidate_fact_count'], 0)

    def test_missing_acceptance_is_audited(self):
        self.submission['filings']['recent']['acceptanceDateTime'] = ['']
        result = self.run_prepare()
        self.assertEqual(result['status'], 'INCOMPLETE')
        self.assertEqual(result['eligible_filing_count'], 0)

    def test_invalid_period_is_not_a_candidate(self):
        self.facts['facts']['us-gaap']['Revenues']['units']['USD'][0]['end'] = '2027-01-01'
        self.assertEqual(self.run_prepare()['candidate_fact_count'], 0)
        self.assertIn('INVALID_OR_FUTURE_FACT_PERIOD', (self.output / 'preparation_exceptions.csv').read_text())

    def test_nonpositive_value_remains_unmodified_for_later_fallback(self):
        self.facts['facts']['us-gaap']['Revenues']['units']['USD'][0]['val'] = -100
        self.assertEqual(self.run_prepare()['candidate_fact_count'], 1)
        self.assertIn('-100', (self.output / 'candidate_facts.csv').read_text())

    def test_request_failures_are_redacted_and_reported(self):
        def fail(url, identity):
            raise RuntimeError(identity)
        result = prepare(self.universe, '2026-07-31', self.output, transport=fail)
        self.assertEqual(result['status'], 'INCOMPLETE')
        self.assertEqual(result['acquisition_failures'], 1)
        self.assertNotIn('PRIVATE_TEST_IDENTIFIER', (self.output / 'preparation_exceptions.csv').read_text())

    def test_existing_output_is_not_overwritten(self):
        self.run_prepare()
        with self.assertRaisesRegex(ValueError, 'new or empty'):
            self.run_prepare()

    def test_weekend_cutoff_flows_into_prepared_inputs_and_audit(self):
        result = prepare(self.universe, '2026-08-02', self.output, transport=self.transport)
        self.assertEqual(result['model_date'], '2026-07-31')
        self.assertEqual(result['date_resolution']['requested_date'], '2026-08-02')
        self.assertEqual(result['candidate_fact_count'], 1)
        self.assertIn('2026-07-31', (self.output / 'candidate_facts.csv').read_text())
        self.assertNotIn('2026-08-02', (self.output / 'candidate_facts.csv').read_text())

    def test_future_model_date_rejected_before_network(self):
        with self.assertRaisesRegex(ValueError, 'future'):
            prepare(self.universe, '2099-01-01', self.output, transport=self.transport)
        self.assertFalse(self.calls)

    def test_untrusted_archive_path_rejected(self):
        self.submission['filings']['files'] = [{'name': '../../secret.json',
            'filingFrom': '2024-01-01', 'filingTo': '2026-07-31'}]
        self.assertEqual(self.run_prepare()['status'], 'INCOMPLETE')
        self.assertEqual(len(self.calls), 2)

    def test_external_endpoint_rejected(self):
        session = SecSession(self.output, self.transport)
        with self.assertRaises(ValueError):
            session.get('https://example.com/submissions/CIK0000000001.json')
        self.assertFalse(self.calls)

    def test_cli_returns_failure_without_opening_scoring_store(self):
        with patch('sys.argv', ['fast-apam', 'prepare-data', '--date', '2026-07-31',
                '--universe', str(self.universe), '--output', str(self.output)]), \
             patch('fast_apam.preparation.prepare', return_value={'status': 'INCOMPLETE'}) as call, \
             patch('fast_apam.cli.Store') as store, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(), 1)
            store.assert_not_called()
            call.assert_called_once()

    def test_preparation_import_needs_no_private_run_config(self):
        environment = dict(os.environ)
        environment.pop('FAST_APAM_RUN_CONFIG', None)
        environment['PYTHONPATH'] = str(Path(__file__).resolve().parents[1] / 'src')
        result = subprocess.run([sys.executable, '-c', 'import fast_apam.preparation'],
                                env=environment, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == '__main__':
    unittest.main()

import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from fast_apam.customer_setup import check_setup
from fast_apam.cli import main


class CustomerSetupTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.path = Path(temporary.name) / 'universe.csv'

    def write(self, content):
        self.path.write_text(content, encoding='utf-8')

    def test_normalizes_symbols_without_approving_eligibility(self):
        self.write('\ufeffticker\n msft \nBRK.B\nBRK-B\n')
        result = check_setup(self.path, '2026-09-25')
        self.assertEqual(result['requested_tickers'], ['MSFT', 'BRK.B', 'BRK-B'])
        for key in ['ready_to_score', 'issuer_identity_verified', 'dated_universe_eligibility_verified', 'peer_coverage_validated']:
            self.assertFalse(result[key])

    def test_duplicate_ticker_is_rejected(self):
        self.write('ticker\nMSFT\n msft \n')
        with self.assertRaisesRegex(ValueError, 'duplicates'): check_setup(self.path, '2026-09-25')

    def test_missing_empty_or_wrong_header(self):
        for content in ['', 'ticker\n', 'symbol\nMSFT\n', 'ticker,api_key\nMSFT,example\n', 'ticker,ticker\nMSFT,AAPL\n']:
            with self.subTest(content=content):
                self.write(content)
                with self.assertRaises(ValueError): check_setup(self.path, '2026-09-25')

    def test_invalid_or_extra_fields(self):
        for content in ['ticker\n""\n', 'ticker\n=SUM(A1)\n', 'ticker\nMSFT,extra\n', 'ticker\nA/B\n']:
            with self.subTest(content=content):
                self.write(content)
                with self.assertRaises(ValueError): check_setup(self.path, '2026-09-25')

    def test_date_is_explicit_and_valid(self):
        self.write('ticker\nMSFT\n')
        for value in ['20260925', '09/25/2026', '2026-02-30']:
            with self.subTest(value=value), self.assertRaises(ValueError): check_setup(self.path, value)

    def test_missing_file(self):
        with self.assertRaises(FileNotFoundError): check_setup(self.path, '2026-09-25')

    def test_cli_does_not_create_database_or_prompt_for_credentials(self):
        self.write('ticker\nMSFT\n')
        output = io.StringIO()
        with patch('sys.argv', ['fast-apam', 'check-setup', '--date', '2026-09-25', '--universe', str(self.path)]), patch('fast_apam.cli.Store') as store, patch('getpass.getpass') as prompt, contextlib.redirect_stdout(output):
            self.assertEqual(main(), 0)
            store.assert_not_called()
            prompt.assert_not_called()
        self.assertEqual(json.loads(output.getvalue())['requested_ticker_count'], 1)

    def test_cli_invalid_input_returns_failure(self):
        self.write('ticker\n')
        with patch('sys.argv', ['fast-apam', 'check-setup', '--date', '2026-09-25', '--universe', str(self.path)]), contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
            main()
        self.assertEqual(error.exception.code, 1)

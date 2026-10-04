import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from fast_apam.universe import read_universe, select_results
from fast_apam.runner import publish, csv_bytes, PREFIX
from fast_apam.snapshots import rows
from fast_apam.cli import main


class UniverseTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.path = self.root / 'my stocks.csv'
        self.path.write_text('ticker\nMSFT\nAMD\nUNKNOWN\n')
        base = {'ticker':'MSFT', 'model_date':'2026-09-25', 'company_name':'Microsoft',
                'PROVISIONAL_FAST_SCORE':'72.123456789', 'PROVISIONAL_FAST_STATUS':'MIXED',
                'PROVISIONAL_DATA_STATUS':'PARTIAL', 'score_published':'YES',
                'gate_reason':'', 'underlying_candidate_hold_reason':'',
                'signal_model_available_date':'2026-08-01', 'production_approved':'NO'}
        self.cohort = [base, dict(base,ticker='AAPL',company_name='Apple'),
            dict(base,ticker='AMD',company_name='AMD',PROVISIONAL_FAST_SCORE='',
                 PROVISIONAL_FAST_STATUS='UNSCORED', PROVISIONAL_DATA_STATUS='INSUFFICIENT_HISTORY',
                 score_published='NO',gate_reason='INSUFFICIENT_HISTORY')]
        self.outputs = {PREFIX+'Research_Pilot_Output_2026-09-25_R1.csv':csv_bytes(self.cohort)}
        self.summary = {'cohort_companies':3,'research_scores_published':2,'cache_hit':True}

    def test_matches_keep_every_original_score_and_lineage_field(self):
        selected, summary = select_results(self.cohort,read_universe(self.path),'2026-09-25')
        self.assertEqual(selected[0],self.cohort[0])
        self.assertEqual(selected[1],self.cohort[2])
        self.assertEqual(summary['normalization_cohort_count'],3)
        self.assertFalse(summary['selection_changes_scores'])

    def test_missing_stock_is_explicitly_unscored_with_no_invented_data(self):
        selected, summary = select_results(self.cohort,read_universe(self.path),'2026-09-25')
        missing = selected[2]
        self.assertEqual(missing['score_published'],'NO')
        self.assertEqual(missing['PROVISIONAL_DATA_STATUS'],'NOT_IN_PREPARED_COHORT')
        for field in ['company_name','PROVISIONAL_FAST_SCORE','signal_model_available_date']:
            self.assertEqual(missing[field],'')
        self.assertEqual(summary['not_in_prepared_cohort'],['UNKNOWN'])
        self.assertEqual(summary['scored_count'],1)
        self.assertEqual(summary['unscored_count'],2)

    def test_requested_order_is_preserved(self):
        self.path.write_text('ticker\nAMD\nMSFT\n')
        selected, _ = select_results(self.cohort,read_universe(self.path),'2026-09-25')
        self.assertEqual([row['ticker'] for row in selected],['AMD','MSFT'])

    def test_changed_request_does_not_change_scores(self):
        first, _ = select_results(self.cohort,read_universe(self.path),'2026-09-25')
        self.path.write_text('ticker\nAAPL\nMSFT\n')
        second, _ = select_results(self.cohort,read_universe(self.path),'2026-09-25')
        self.assertEqual(first[0],second[1])

    def test_sha_covers_exact_file_bytes_and_no_file_is_rewritten(self):
        self.path.write_bytes(b'\xef\xbb\xbfticker\r\n msft \r\n')
        before = self.path.read_bytes()
        request = read_universe(self.path)
        self.assertEqual(request['requested_tickers'],['MSFT'])
        self.assertEqual(request['input_sha256'],hashlib.sha256(before).hexdigest())
        self.assertEqual(self.path.read_bytes(),before)

    def test_duplicate_cohort_rows_fail_closed(self):
        with self.assertRaisesRegex(ValueError,'duplicate'):
            select_results(self.cohort+self.cohort,read_universe(self.path),'2026-09-25')

    def test_mismatched_model_date_is_rejected(self):
        with self.assertRaisesRegex(ValueError,'effective model date'):
            select_results(self.cohort,read_universe(self.path),'2026-09-24')

    def test_all_unknown_requests_are_retained(self):
        self.path.write_text('ticker\nUNKNOWN\nOTHER\n')
        selected, summary = select_results(self.cohort,read_universe(self.path),'2026-09-25')
        self.assertEqual(len(selected),2)
        self.assertEqual(summary['matched_count'],0)
        self.assertEqual(summary['scored_count'],0)

    def test_publish_separates_customer_counts_from_full_cohort_counts(self):
        with patch('fast_apam.runner.calculate',return_value=('same-cohort-id',self.summary,self.outputs)) as calc:
            target = self.root/'output'
            result = publish(None,'2026-09-25',target,universe=self.path)
            calc.assert_called_once_with(None,'2026-09-25',False)
        self.assertEqual(result['run_id'],'same-cohort-id')
        self.assertEqual(result['research_scores_published'],1)
        self.assertEqual(result['cohort_summary']['research_scores_published'],2)
        self.assertEqual(result['status'],'COMPLETE_WITH_EXCEPTIONS')
        self.assertEqual(result['universe_selection']['requested_count'],3)
        self.assertEqual([row['ticker'] for row in rows((target/'exceptions.csv').read_bytes())],['AMD','UNKNOWN'])
        self.assertEqual(set(path.name for path in target.iterdir()),{'results.csv','exceptions.csv','run.json'})
        manifest = json.loads((target/'run.json').read_text())
        self.assertEqual(manifest['output_sha256']['results.csv'],hashlib.sha256((target/'results.csv').read_bytes()).hexdigest())
        self.assertNotIn(str(self.path),json.dumps(manifest))

    def test_no_universe_preserves_original_result_bytes(self):
        with patch('fast_apam.runner.calculate',return_value=('id',self.summary,self.outputs)):
            target = self.root/'full'
            result = publish(None,'2026-09-25',target)
        self.assertEqual((target/'results.csv').read_bytes(),next(iter(self.outputs.values())))
        self.assertNotIn('universe_selection',result)

    def test_invalid_universe_fails_before_calculation(self):
        self.path.write_text('ticker\nMSFT\nmsft\n')
        with patch('fast_apam.runner.calculate') as calc, self.assertRaisesRegex(ValueError,'duplicates'):
            publish(None,'2026-09-25',self.root/'output',universe=self.path)
        calc.assert_not_called()
        self.assertFalse((self.root/'output').exists())

    def test_cli_forwards_universe_to_publish(self):
        with patch('sys.argv',['fast-apam','run','--date','2026-09-25','--universe',str(self.path),'--output','unused']), \
             patch('fast_apam.cli.Store'),patch('fast_apam.cli.publish',return_value={}) as run, \
             contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(main(),0)
        self.assertEqual(run.call_args.kwargs['universe'],str(self.path))


class LauncherUniverseTests(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.spec_from_file_location('apam_launcher',Path(__file__).resolve().parents[1]/'tools'/'start_fast_apam.py')
        self.launcher = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.launcher)

    def test_pasted_quoted_path_with_spaces(self):
        with patch('builtins.input',return_value='"C:\\My Lists\\stocks.csv"'):
            self.assertEqual(self.launcher.choose_universe(),'C:\\My Lists\\stocks.csv')

    def test_no_tkinter_falls_back_to_typed_path(self):
        with patch('builtins.input',side_effect=['','universe.csv']),patch.dict('sys.modules',{'tkinter':None}),contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(self.launcher.choose_universe(),'universe.csv')

    def test_no_tkinter_cancel_returns_empty(self):
        with patch('builtins.input',side_effect=['','']),patch.dict('sys.modules',{'tkinter':None}),contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(self.launcher.choose_universe(),'')

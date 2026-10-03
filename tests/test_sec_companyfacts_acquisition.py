import os
from pathlib import Path
os.environ.setdefault("FAST_APAM_RUN_CONFIG", str(Path(__file__).with_name("unit-config.json")))
import unittest
from fast_apam.engine.sec_companyfacts_acquisition import _candidate_facts

class CompanyFactsAcquisitionTests(unittest.TestCase):

    def setUp(self):
        self.filing = {'batch_id': 'B1', 'snapshot_id': 'S1', 'model_date': '2026-07-31', 'ticker': 'TEST', 'company_name': 'TEST CO', 'cik': '0000000001', 'target_flag': 'N', 'form_type': '10-Q', 'filed_date': '2026-05-01', 'report_period': '2026-03-31', 'accepted_timestamp_utc': '2026-05-01T20:00:00+00:00', 'model_available_date': '2026-05-05', 'source_url': 'https://example.test/filing'}

    def test_keeps_only_eligible_accession_and_supported_unit(self):
        payload = {'facts': {'us-gaap': {'OperatingIncomeLoss': {'label': 'Operating income', 'description': '', 'units': {'USD': [{'start': '2026-01-01', 'end': '2026-03-31', 'val': 10, 'accn': 'A1', 'fy': 2026, 'fp': 'Q1', 'form': '10-Q', 'filed': '2026-05-01'}, {'start': '2026-01-01', 'end': '2026-03-31', 'val': 11, 'accn': 'LATE', 'fy': 2026, 'fp': 'Q1', 'form': '10-Q', 'filed': '2026-05-02'}], 'USD/shares': [{'end': '2026-03-31', 'val': 1, 'accn': 'A1'}]}}}}}
        rows = list(_candidate_facts(payload, {'A1': self.filing}))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['value'], 10)
        self.assertEqual(rows[0]['candidate_status'], 'ACQUIRED_UNVALIDATED_CONTEXT')

    def test_preserves_comparative_facts_from_same_accession(self):
        payload = {'facts': {'us-gaap': {'Revenues': {'label': 'Revenue', 'description': '', 'units': {'USD': [{'start': '2025-01-01', 'end': '2025-03-31', 'val': 8, 'accn': 'A1'}, {'start': '2026-01-01', 'end': '2026-03-31', 'val': 10, 'accn': 'A1'}]}}}}}
        rows = list(_candidate_facts(payload, {'A1': self.filing}))
        self.assertEqual(len(rows), 2)
        self.assertEqual({r['period_end'] for r in rows}, {'2025-03-31', '2026-03-31'})
if __name__ == '__main__':
    unittest.main()

import os
from pathlib import Path
os.environ.setdefault("FAST_APAM_RUN_CONFIG", str(Path(__file__).with_name("unit-config.json")))
import unittest
from decimal import Decimal
from fast_apam.engine.ttm_yoy_construction import _change, _consecutive, _derive_fcf_quarters, _unit_family, _window_is_consecutive

class TTMYoYConstructionTests(unittest.TestCase):

    @staticmethod
    def _quarter(label, start, end):
        return {'fiscal_quarter': label, 'quarter_period_start': start, 'quarter_period_end': end}

    def test_fiscal_quarter_cycle_and_date_adjacency_are_required(self):
        q4 = self._quarter('Q4', '2024-10-01', '2024-12-31')
        q1 = self._quarter('Q1', '2025-01-01', '2025-03-31')
        self.assertTrue(_consecutive(q4, q1))
        bad = self._quarter('Q2', '2025-01-02', '2025-06-30')
        self.assertFalse(_consecutive(q1, bad))

    def test_four_quarter_window_must_be_consecutive(self):
        rows = [self._quarter('Q1', '2024-01-01', '2024-03-31'), self._quarter('Q2', '2024-04-01', '2024-06-30'), self._quarter('Q3', '2024-07-01', '2024-09-30'), self._quarter('Q4', '2024-10-01', '2024-12-31')]
        self.assertTrue(_window_is_consecutive(rows))

    def test_nonpositive_base_does_not_manufacture_growth_rate(self):
        rate, absolute, method = _change(Decimal('20'), Decimal('-10'))
        self.assertEqual(rate, '')
        self.assertEqual(absolute, '30')
        self.assertEqual(method, 'ABSOLUTE_CHANGE_NONPOSITIVE_BASE')

    def test_positive_base_calculates_growth(self):
        rate, absolute, method = _change(Decimal('120'), Decimal('100'))
        self.assertEqual(rate, '0.2')
        self.assertEqual(absolute, '20')
        self.assertEqual(method, 'PERCENT_CHANGE')

    def test_fcf_is_cfo_minus_positive_capex(self):
        base = {'ticker': 'MSFT', 'cik': '1', 'quarter_period_start': '2025-01-01', 'quarter_period_end': '2025-03-31', 'fiscal_quarter': 'Q3', 'unit_ref': 'usd', 'quarter_status': 'PASS_DIRECT', 'latest_parent_model_available_date': '2025-04-25', 'resolution_id': '', 'parent_lineage_json': '[]', 'mapping_rule_id': 'R'}
        cfo = dict(base, canonical_concept='cash_from_operations', standalone_value='100')
        capex = dict(base, canonical_concept='capital_expenditures', standalone_value='40')
        controls = {('MSFT', 'cash_from_operations'): {'ticker': 'MSFT', 'cik': '1', 'nine_quarter_requirement_status': 'PASS_NINE_QUARTERS'}, ('MSFT', 'capital_expenditures'): {'ticker': 'MSFT', 'cik': '1', 'nine_quarter_requirement_status': 'PASS_NINE_QUARTERS'}}
        rows, updated = _derive_fcf_quarters([cfo, capex], controls)
        self.assertEqual(rows[0]['standalone_value'], '60')
        self.assertEqual(updated['MSFT', 'free_cash_flow']['nine_quarter_requirement_status'], 'PASS_NINE_QUARTERS')

    def test_fcf_accepts_document_local_usd_unit_ids(self):
        self.assertEqual(_unit_family('usd'), _unit_family('unit_standard_usd_company'))
if __name__ == '__main__':
    unittest.main()

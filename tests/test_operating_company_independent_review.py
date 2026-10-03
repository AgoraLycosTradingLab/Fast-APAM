import os
from pathlib import Path
os.environ.setdefault("FAST_APAM_RUN_CONFIG", str(Path(__file__).with_name("unit-config.json")))
import os
import tempfile
import unittest
from decimal import Decimal as D
from pathlib import Path
from fast_apam.engine.operating_company_independent_review import direction, reconcile, reviewed_families, confidence_bounds, independent_persistence, run, read, PREFIX, SUFFIX

class ReviewRuleTests(unittest.TestCase):

    def test_fcf_margin_spec_boundary_is_half_percentage_point(self):
        self.assertEqual(direction('.003', D('.005')), 'NEUTRAL')
        self.assertEqual(direction('-.005', D('.005')), 'NEUTRAL')
        self.assertEqual(direction('-.0051', D('.005')), 'ADVERSE')

    def test_missing_does_not_become_adverse(self):
        self.assertEqual(direction('', D('.005')), 'INELIGIBLE')
        self.assertEqual(reconcile(['INELIGIBLE', 'NEUTRAL']), 'NEUTRAL')

    def test_conflict_is_preserved(self):
        self.assertEqual(reconcile(['SUPPORTIVE', 'ADVERSE']), 'CONFLICTED')

    def test_confidence_unknowns_do_not_receive_point_values(self):
        rows, low, high = confidence_bounds(D('.85'), True)
        self.assertEqual(low, D('74.50'))
        self.assertEqual(high, D('98.50'))
        self.assertEqual(sum((lo == hi for _, w, lo, hi, reason in rows)), 4)

    def test_coverage_does_not_exceed_full_credit(self):
        rows, _, _ = confidence_bounds(D('.95'), False)
        coverage = next((r for r in rows if r[0] == 'metric_factor_coverage'))
        self.assertEqual(coverage[2], 100)

    def test_independent_persistence_arithmetic(self):
        self.assertEqual(independent_persistence({'values_json': '["0.1","0","-0.1","0.1"]', 'neutral_band': '.01'}), 60)
        self.assertIsNone(independent_persistence({'values_json': '["0.1"]', 'neutral_band': '.01'}))
if __name__ == '__main__':
    unittest.main()

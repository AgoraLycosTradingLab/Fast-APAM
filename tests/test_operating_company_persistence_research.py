import os
from pathlib import Path
os.environ.setdefault("FAST_APAM_RUN_CONFIG", str(Path(__file__).with_name("unit-config.json")))
import json
import os
import tempfile
import unittest
from decimal import Decimal as D
from pathlib import Path
from fast_apam.engine.operating_company_persistence_research import combine, composite, run, read, PREFIX, SUFFIX, WEIGHTS

class PersistenceCandidateTests(unittest.TestCase):

    def test_cash_is_one_family(self):
        values = dict(revenue=D(0), operating_income=D(0), cash_from_operations=D(100), free_cash_flow=D(100))
        score, coverage, originals, passed = combine(values, 'EQUAL_FAMILIES_40_60')
        self.assertAlmostEqual(score, D(100) / 3, places=24)
        self.assertAlmostEqual(originals['cash_from_operations'] + originals['free_cash_flow'], D(1) / 3, places=24)
        self.assertTrue(passed)

    def test_missing_cash_reduces_weight_not_score(self):
        values = dict(revenue=D(80), operating_income=D(80), cash_from_operations=None, free_cash_flow=None)
        score, coverage, _, passed = combine(values, 'EQUAL_FAMILIES_40_60')
        self.assertEqual(score, 80)
        self.assertAlmostEqual(coverage, D(2) / 3, places=24)
        self.assertTrue(passed)

    def test_two_cash_metrics_cannot_replace_profit(self):
        self.assertFalse(combine(dict(revenue=D(80), operating_income=None, cash_from_operations=D(90), free_cash_flow=D(90)), 'EQUAL_FAMILIES_40_60')[3])

    def test_strict_history_is_a_separate_sensitivity(self):
        values = dict(revenue=D(80), operating_income=D(80), cash_from_operations=D(80), free_cash_flow=None)
        self.assertTrue(combine(values, 'EQUAL_FAMILIES_40_60')[3])
        self.assertFalse(combine(values, 'STRICT_COMPLETE_HISTORY')[3])

    def test_composite_fixed_weights_and_low_acceleration_allowed(self):
        factors = {f: D(80) for f in WEIGHTS}
        factors['F4_ACCELERATION'] = D(0)
        self.assertEqual(composite(factors, D('.8')), 68)
        self.assertIsNone(composite(factors, D('.69')))
        factors['F4_ACCELERATION'] = None
        self.assertIsNone(composite(factors, D('.8')))

    def test_unknown_candidate_rejected(self):
        with self.assertRaises(ValueError):
            combine({}, 'UNDECLARED')
if __name__ == '__main__':
    unittest.main()

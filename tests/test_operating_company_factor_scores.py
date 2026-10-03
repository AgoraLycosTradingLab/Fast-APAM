import os
from pathlib import Path
os.environ.setdefault("FAST_APAM_RUN_CONFIG", str(Path(__file__).with_name("unit-config.json")))
import json
import os
import tempfile
import unittest
from decimal import Decimal as D
from pathlib import Path
from fast_apam.engine.operating_company_factor_scores import weighted_score, persistence, breadth, run, read, PREFIX, SUFFIX, COMPONENTS

class FactorScoreTests(unittest.TestCase):

    def test_mapping_weights_each_sum_to_one(self):
        for components in COMPONENTS.values():
            self.assertEqual(sum((D(w) for _, w, _ in components)), 1)

    def test_missing_weight_not_zero_economic_score(self):
        rows = [dict(original_weight=D('.5'), applied_weight=D('.5'), metric_score=D(80)), dict(original_weight=D('.5'), applied_weight=D(0), metric_score=None)]
        self.assertEqual(weighted_score(rows), (D(80), D('.5')))

    def test_expansion_over_cap_rejected(self):
        with self.assertRaisesRegex(ValueError, 'cap'):
            weighted_score([dict(original_weight=D('.2'), applied_weight=D('.26'), metric_score=D(80))])

    def test_missing_score_cannot_receive_weight(self):
        with self.assertRaisesRegex(ValueError, 'Missing'):
            weighted_score([dict(original_weight=D('.2'), applied_weight=D('.2'), metric_score=None)])

    def test_persistence_recency_and_neutral_boundaries(self):
        self.assertEqual(persistence(['.1', '.1', '.1', '-.1'], D('.01'))[0], 60)
        self.assertEqual(persistence(['.01', '-.01', '0', '0'], D('.01'))[0], 50)
        self.assertEqual(persistence(['-.1'] * 4, D('.01'))[0], 0)

    def test_short_history_not_renormalized(self):
        self.assertIsNone(persistence(['.1'] * 3, D('.01'))[0])

    def test_breadth_conflict_sensitivity(self):
        classes = ['SUPPORTIVE', 'CONFLICTED', 'ADVERSE', 'INELIGIBLE']
        self.assertEqual(breadth(classes, D('.5')), (D(50), 3))
        self.assertEqual(breadth(classes, D('.25'))[0], D(125) / 3)
        self.assertIsNone(breadth(['SUPPORTIVE', 'ADVERSE'], D('.25'))[0])
if __name__ == '__main__':
    unittest.main()

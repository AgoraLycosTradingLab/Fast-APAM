import os
from pathlib import Path
os.environ.setdefault("FAST_APAM_RUN_CONFIG", str(Path(__file__).with_name("unit-config.json")))
import unittest
from decimal import Decimal
from fast_apam.engine.standalone_quarter_construction import _compatible, _tolerance

class StandaloneQuarterConstructionTests(unittest.TestCase):

    def test_parent_compatibility_requires_concept_rule_and_unit(self):
        base = {'canonical_concept': 'revenue', 'mapping_rule_id': 'R', 'unit_ref': 'USD'}
        self.assertTrue(_compatible(base, dict(base)))
        changed = dict(base)
        changed['unit_ref'] = 'shares'
        self.assertFalse(_compatible(base, changed))

    def test_rounding_tolerance_is_bounded(self):
        self.assertEqual(_tolerance([], Decimal('100'), Decimal('101')), Decimal(1))
        self.assertEqual(_tolerance([], Decimal('10000000000')), Decimal('10.000000000'))
        rounded = [{'rounding_error_bound': '500000'}] * 3
        self.assertEqual(_tolerance(rounded, Decimal('2000000000')), Decimal('1500000'))
if __name__ == '__main__':
    unittest.main()

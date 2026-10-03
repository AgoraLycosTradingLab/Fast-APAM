import os
from pathlib import Path
os.environ.setdefault("FAST_APAM_RUN_CONFIG", str(Path(__file__).with_name("unit-config.json")))
import unittest
from decimal import Decimal
from fast_apam.engine.operating_company_factor_inputs import _combine_directions, _direction, _persistence, _ratio

class OperatingCompanyFactorInputTests(unittest.TestCase):

    def test_ratio_rejects_zero_denominator(self):
        self.assertIsNone(_ratio(Decimal('1'), Decimal('0')))

    def test_absolute_neutral_band_is_symmetric(self):
        self.assertEqual(_direction(Decimal('0.01'), Decimal('0.01')), 'NEUTRAL')
        self.assertEqual(_direction(Decimal('0.011'), Decimal('0.01')), 'SUPPORTIVE')
        self.assertEqual(_direction(Decimal('-0.011'), Decimal('0.01')), 'ADVERSE')

    def test_cash_family_conflict_is_preserved(self):
        self.assertEqual(_combine_directions(['SUPPORTIVE', 'ADVERSE']), 'CONFLICTED')

    def test_missing_family_is_not_adverse(self):
        self.assertEqual(_combine_directions(['INELIGIBLE']), 'INELIGIBLE')

    def test_persistence_is_qualitative_and_uses_recent_sequence(self):
        values = [Decimal('-0.4'), Decimal('-0.3'), Decimal('-0.2'), Decimal('-0.1')]
        self.assertEqual(_persistence(values), 'NEGATIVE_BUT_RECOVERING')

    def test_positive_slowing_is_not_deteriorating(self):
        values = [Decimal('0.4'), Decimal('0.3'), Decimal('0.2'), Decimal('0.1')]
        self.assertEqual(_persistence(values), 'POSITIVE_BUT_SLOWING')
if __name__ == '__main__':
    unittest.main()

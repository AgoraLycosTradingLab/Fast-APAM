import os
from pathlib import Path
os.environ.setdefault("FAST_APAM_RUN_CONFIG", str(Path(__file__).with_name("unit-config.json")))
import unittest
from fast_apam.engine.exception_mapping_continuity import MAPPINGS

class ExceptionMappingTests(unittest.TestCase):

    def test_roper_rule_requires_both_components(self):
        self.assertEqual(MAPPINGS['ROP']['components'], ('PaymentsToAcquireOtherProductiveAssets', 'PaymentsToDevelopSoftware'))

    def test_capital_improvement_aliases_are_explicit(self):
        self.assertEqual(MAPPINGS['GLW']['components'], ('PaymentsForCapitalImprovements',))
        self.assertEqual(MAPPINGS['IT']['components'], ('PaymentsForCapitalImprovements',))
if __name__ == '__main__':
    unittest.main()

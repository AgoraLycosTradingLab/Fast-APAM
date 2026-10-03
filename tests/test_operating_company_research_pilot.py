import os
from pathlib import Path
os.environ.setdefault("FAST_APAM_RUN_CONFIG", str(Path(__file__).with_name("unit-config.json")))
import copy
import json
import os
import tempfile
import unittest
from decimal import Decimal as D
from pathlib import Path
from fast_apam.engine.operating_company_research_pilot import classify, confidence, publication_gate, unique_json, acceleration_evidence, run, read, PREFIX, SUFFIX, POLICY
from fast_apam.engine.research_pilot_vintage import filing_check
RULES = {'absolute_direction_threshold': '.25', 'predominantly_neutral_fraction': '.5'}

def families(value):
    return dict(growth=value, profit=value, cash=value, margin=value, productivity='INELIGIBLE', capital='INELIGIBLE')

class ResearchPilotRulesTests(unittest.TestCase):

    def label(self, level, momentum, fam, acc=None, recovery=None, eligible=True, scenario='BASELINE'):
        return classify(D(level), D(momentum), fam, acc or families('NEUTRAL'), recovery or {}, [], eligible, RULES, scenario)[0]

    def test_critical_gate_precedes_conflict_and_direction(self):
        self.assertEqual(self.label(70, 70, families('SUPPORTIVE'), eligible=False), 'UNSCORED')

    def test_accelerating_needs_level_momentum_and_breadth(self):
        self.assertEqual(self.label(60, 70, families('SUPPORTIVE'), families('SUPPORTIVE')), 'ACCELERATING')

    def test_strong_but_slowing_is_decelerating(self):
        self.assertEqual(self.label(60, 35, families('SUPPORTIVE'), families('ADVERSE')), 'DECELERATING')

    def test_broad_deterioration(self):
        self.assertEqual(self.label(30, 30, families('ADVERSE'), families('ADVERSE')), 'DETERIORATING')

    def test_recovery_from_weakness_is_not_accelerating(self):
        self.assertEqual(self.label(40, 65, families('ADVERSE'), families('SUPPORTIVE'), {'growth': True, 'cash': True}), 'IMPROVING')

    def test_neutral_evidence_is_stable(self):
        self.assertEqual(self.label(50, 50, families('NEUTRAL')), 'STABLE')

    def test_conflict_precedes_high_relative_strength(self):
        fam = families('SUPPORTIVE')
        fam['cash'] = 'CONFLICTED'
        self.assertEqual(self.label(60, 65, fam, families('SUPPORTIVE')), 'MIXED')
        self.assertEqual(self.label(60, 65, fam, families('SUPPORTIVE'), scenario='STRICT_CONFLICT_COUNTS'), 'IMPROVING')

    def test_absolute_weakness_cannot_be_hidden_by_high_percentile(self):
        self.assertEqual(self.label(65, 65, families('ADVERSE'), families('SUPPORTIVE')), 'MIXED')

    def test_company_hold_not_lifted_by_high_confidence(self):
        publish, status, _ = publication_gate(None, 'PASS_KNOWABLE_AT_MODEL_DATE', D(100), 10)
        self.assertFalse(publish)
        self.assertEqual(status, 'INSUFFICIENT_HISTORY')

    def test_vintage_failure_withholds_score(self):
        self.assertFalse(publication_gate(D(80), 'REVIEW_REQUIRED', D(95), 10)[0])

    def test_staleness_and_confidence_boundaries(self):
        self.assertEqual(publication_gate(D(80), 'PASS_KNOWABLE_AT_MODEL_DATE', D(70), 180)[:2], (True, 'STALE'))
        self.assertFalse(publication_gate(D(80), 'PASS_KNOWABLE_AT_MODEL_DATE', D(70), 181)[0])
        self.assertFalse(publication_gate(D(80), 'PASS_KNOWABLE_AT_MODEL_DATE', D('69.99'), 10)[0])

    def test_duplicate_policy_keys_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            unique_json('{"status":1,"status":2}')

    def test_filing_buffer_and_future_eligibility(self):
        filing = {'accepted_timestamp_utc': '2026-07-29T20:08:01+00:00', 'model_available_date': '2026-07-31'}
        self.assertEqual(filing_check(filing, '2026-07-31'), 'PASS')
        self.assertEqual(filing_check(filing, '2026-07-30'), 'SOURCE_AVAILABLE_BEFORE_FILING_BUFFER')
        self.assertEqual(filing_check(filing, '2026-07-31', '2026-07-30'), 'FUTURE_FILING')
        filing['model_available_date'] = '2026-07-30'
        self.assertEqual(filing_check(filing, '2026-07-31'), 'BUFFER_DATE_MISMATCH')

    def test_missing_filing_fails_closed(self):
        self.assertEqual(filing_check(None, '2026-07-31'), 'MISSING_FILING_INDEX_ENTRY')

    def test_cash_recovery_is_one_family(self):
        row = {'cfo_ttm_yoy': '-.01', 'cfo_ttm_yoy_acceleration': '.08', 'fcf_ttm_yoy': '-.01', 'fcf_ttm_yoy_acceleration': '.09'}
        acc, recovering, _ = acceleration_evidence(row, D('.01'))
        self.assertEqual(acc['cash'], 'SUPPORTIVE')
        self.assertEqual(sum(recovering.values()), 1)
if __name__ == '__main__':
    unittest.main()

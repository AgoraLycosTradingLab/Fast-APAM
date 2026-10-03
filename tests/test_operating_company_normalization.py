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
from fast_apam.engine.operating_company_normalization import MODEL_DATE, METHODS, PREFIX, SUFFIX, calculate, eligibility, midranks, percentile_scores, quantile, robust_scores, run, spearman, sensitivity
from fast_apam.engine.operating_company_factor_inputs_v2 import read

def fixture(n=50):
    roster = {str(i): {'cik': str(i)} for i in range(n)}
    rows = [dict(ticker=str(i), cik=str(i), input_id='revenue_ttm_yoy', model_date=MODEL_DATE, value=str(D(i) / 100), raw_input_eligible='YES', data_quality_status='PASS', fallback_status='STANDARD', transformation='PERCENT_CHANGE', normalization_bucket='PERCENT_CHANGE', signal_model_available_date='2026-05-01', as_of_period_end='2026-03-31', data_age_days='91', source_observation_refs_json='[["test.csv",2]]', raw_sequential_qoq_primary_weight='0', history_view='LATEST_RESTATED_AS_OF_MODEL_DATE') for i in range(n)]
    return (rows, roster, set(roster))

class MetricNormalizationTests(unittest.TestCase):

    def test_known_percentile_values_and_ties(self):
        self.assertEqual(percentile_scores([D(1), D(2), D(2), D(4)]), [D('12.5'), D(50), D(50), D('87.5')])

    def test_all_ties_are_neutral_percentile(self):
        self.assertEqual(percentile_scores([D(3)] * 5), [D(50)] * 5)

    def test_quantiles_use_documented_interpolation(self):
        self.assertEqual(quantile([D(0), D(10)], D('.025')), D('.25'))
        self.assertEqual(quantile([D(0), D(10)], D('.95')), D('9.50'))

    def test_robust_center_and_zero_mad(self):
        scores, center, mad = robust_scores([D(-1), D(0), D(1)])
        self.assertEqual(center, 0)
        self.assertEqual(mad, 1)
        self.assertEqual(scores[1], 50)
        self.assertAlmostEqual(float(scores[0] + scores[2]), 100)
        self.assertEqual(robust_scores([D(1)] * 3)[0], [None] * 3)

    def test_robust_z_is_clipped_at_three(self):
        scores, _, _ = robust_scores([D(-10000), D(-1), D(0), D(1), D(10000)])
        self.assertAlmostEqual(float(scores[0]), 0.134989803, places=7)
        self.assertAlmostEqual(float(scores[-1]), 99.865010197, places=7)

    def test_spearman_respects_ties_and_constant_unavailability(self):
        self.assertEqual(spearman([D(1), D(2), D(2)], [D(10), D(20), D(20)]), 1)
        self.assertEqual(spearman([D(1), D(2), D(3)], [D(30), D(20), D(10)]), -1)
        self.assertIsNone(spearman([D(1), D(1)], [D(1), D(2)]))

    def test_49_cannot_meet_baseline_minimum(self):
        results, _, _ = calculate(*fixture(49))
        self.assertTrue(all((r['empirical_percentile_score'] == '' for r in results if r['scenario'] == 'BASELINE')))
        self.assertTrue(any((r['normalization_status'] == 'PASS' for r in results if r['scenario'] == 'PEER_MIN_40')))

    def test_50_meets_baseline_but_not_60_minimum(self):
        results, _, _ = calculate(*fixture())
        self.assertEqual(sum((r['normalization_status'] == 'PASS' for r in results if r['scenario'] == 'BASELINE')), 50)
        self.assertTrue(all((r['empirical_percentile_score'] == '' for r in results if r['scenario'] == 'PEER_MIN_60')))

    def test_company_hold_retains_valid_peer_without_publishing_score(self):
        rows, roster, approved = fixture()
        approved.remove('0')
        results, distributions, exceptions = calculate(rows, roster, approved)
        held = next((r for r in results if r['ticker'] == '0' and r['scenario'] == 'BASELINE'))
        self.assertEqual(held['empirical_percentile_score'], '')
        self.assertEqual(held['midrank'], '')
        self.assertEqual(held['peer_count'], 50)
        self.assertTrue(any((r['reason'] == 'COMPANY_COVERAGE_HOLD_SCORE_WITHHELD' for r in exceptions)))

    def test_fallback_does_not_enter_percentage_distribution(self):
        rows, roster, approved = fixture(51)
        rows[0]['fallback_status'] = 'ABSOLUTE_CHANGE_FALLBACK'
        results, distributions, _ = calculate(rows, roster, approved)
        self.assertFalse(any((r['ticker'] == '0' for r in results)))
        self.assertEqual(next((r['peer_count'] for r in distributions if r['input_id'] == 'revenue_ttm_yoy')), 50)

    def test_future_filing_fails_eligibility(self):
        rows, roster, _ = fixture()
        rows[0]['signal_model_available_date'] = '2026-08-01'
        self.assertEqual(eligibility(rows[0], roster, 180), 'LOOK_AHEAD_OR_MISSING_PERIOD')

    def test_future_parent_filing_is_not_hidden_by_current_signal_date(self):
        rows, roster, _ = fixture()
        rows[0]['filing_availability_dates_json'] = '[{"model_available_date":"2026-08-01"}]'
        self.assertEqual(eligibility(rows[0], roster, 180), 'LOOK_AHEAD_SOURCE_FILING')

    def test_insufficient_sensitivity_scenario_still_has_a_summary_row(self):
        results, _, _ = calculate(*fixture(49))
        summary = sensitivity(results)
        row = next((r for r in summary if r['scenario'] == 'PEER_MIN_60' and r['input_id'] == 'revenue_ttm_yoy' and (r['method'] == 'empirical_percentile_score')))
        self.assertEqual(row['scenario_published_count'], 0)
        self.assertIsNone(row['max_absolute_score_change'])

    def test_wrong_model_date_fails_eligibility(self):
        rows, roster, _ = fixture()
        rows[0]['model_date'] = '2026-08-31'
        self.assertEqual(eligibility(rows[0], roster, 180), 'MODEL_DATE_OR_ROSTER_MISMATCH')

    def test_nonfinite_input_fails_eligibility(self):
        rows, roster, _ = fixture()
        rows[0]['value'] = 'NaN'
        self.assertEqual(eligibility(rows[0], roster, 180), 'NONFINITE_VALUE')

    def test_stale_boundary_and_sensitivity(self):
        rows, roster, _ = fixture()
        rows[0]['data_age_days'] = '180'
        self.assertEqual(eligibility(rows[0], roster, 180), '')
        self.assertEqual(eligibility(rows[0], roster, 150), 'STALE_EXCLUDED')
        rows[0]['data_age_days'] = '181'
        self.assertEqual(eligibility(rows[0], roster, 180), 'STALE_EXCLUDED')

    def test_qoq_cannot_acquire_primary_weight(self):
        rows, roster, _ = fixture()
        rows[0]['raw_sequential_qoq_primary_weight'] = '.1'
        self.assertEqual(eligibility(rows[0], roster, 180), 'INVALID_SEQUENTIAL_QOQ_WEIGHT')
        rows[0]['input_id'] = 'sequential_qoq'
        self.assertEqual(eligibility(rows[0], roster, 180), 'DIAGNOSTIC_OR_CONDITIONAL_INPUT')

    def test_duplicate_input_is_rejected(self):
        rows, roster, approved = fixture()
        rows.append(copy.deepcopy(rows[0]))
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            calculate(rows, roster, approved)

    def test_missing_roster_observation_is_rejected(self):
        rows, roster, approved = fixture()
        with self.assertRaisesRegex(ValueError, 'rectangular'):
            calculate(rows[:-1], roster, approved)

    def test_winsorization_preserves_source_values(self):
        rows, roster, approved = fixture()
        rows[-1]['value'] = '1000000'
        results, _, _ = calculate(rows, roster, approved)
        r = next((r for r in results if r['ticker'] == '49' and r['scenario'] == 'WINSOR_5_95'))
        self.assertEqual(r['raw_value'], D(1000000))
        self.assertLess(r['sensitivity_value'], r['raw_value'])
        self.assertEqual(r['peer_extreme'], 'YES')
if __name__ == '__main__':
    unittest.main()

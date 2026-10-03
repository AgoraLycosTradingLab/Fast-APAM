import os
from pathlib import Path
os.environ.setdefault("FAST_APAM_RUN_CONFIG", str(Path(__file__).with_name("unit-config.json")))
import calendar
import copy
import json
import os
import tempfile
import unittest
from pathlib import Path
from datetime import date, timedelta
from decimal import Decimal as D
from fast_apam.engine.operating_company_factor_inputs_v2 import InvalidInput, MODEL_DATE, CONCEPTS, assemble, check_rows, margin, normalization_coverage, signal, window, yoy, run, read, digest

def fixture(values=None, concept='revenue'):
    values = values or list(range(10, 22))
    rows = []
    for i, value in enumerate(values):
        month_index = 2023 * 12 + 6 + i * 3
        year, month0 = divmod(month_index, 12)
        month = month0 + 1
        end = date(year, month + 2, calendar.monthrange(year, month + 2)[1])
        row = dict(ticker='TEST', cik='1', canonical_concept=concept, history_view='LATEST_RESTATED_AS_OF_MODEL_DATE', model_date=MODEL_DATE, fiscal_quarter='Q' + str((month - 1) // 3 + 1), quarter_period_start=date(year, month, 1).isoformat(), quarter_period_end=end.isoformat(), quarter_value=str(value), unit_ref='usd', quarter_source_status='PASS_DIRECT', ttm_rollforward_status='PASS', signal_model_available_date=(end + timedelta(days=20)).isoformat(), quarter_metric_lineage_json='[{"accession_number":"fixture"}]', _source_file='fixture.csv', _source_row=i + 2)
        for basis in ['quarter', 'ttm']:
            row.update({basis + '_yoy_' + k: '' for k in ['rate', 'absolute_change', 'method', 'acceleration', 'acceleration_absolute_change', 'acceleration_method']})
            if i >= (4 if basis == 'quarter' else 7):
                current = D(value) if basis == 'quarter' else sum((D(v) for v in values[i - 3:i + 1]))
                prior = D(values[i - 4]) if basis == 'quarter' else sum((D(v) for v in values[i - 7:i - 3]))
                row[basis + '_yoy_rate'] = str(current / prior - 1) if prior > 0 else ''
                row[basis + '_yoy_absolute_change'] = str(current - prior)
                row[basis + '_yoy_method'] = 'PERCENT_CHANGE' if prior > 0 else 'ABSOLUTE_CHANGE_NONPOSITIVE_BASE'
                if basis == 'ttm':
                    row.update(ttm_value=str(current), prior_year_ttm_value=str(prior))
                if rows and rows[-1][basis + '_yoy_method']:
                    previous = rows[-1]
                    if row[basis + '_yoy_rate'] and previous[basis + '_yoy_rate']:
                        row[basis + '_yoy_acceleration'] = str(D(row[basis + '_yoy_rate']) - D(previous[basis + '_yoy_rate']))
                        row[basis + '_yoy_acceleration_method'] = 'YOY_RATE_DELTA'
                    else:
                        row[basis + '_yoy_acceleration_absolute_change'] = str(D(row[basis + '_yoy_absolute_change']) - D(previous[basis + '_yoy_absolute_change']))
                        row[basis + '_yoy_acceleration_method'] = 'YOY_ABSOLUTE_CHANGE_DELTA_NONPOSITIVE_BASE'
        rows.append(row)
    return rows

def company():
    observations = [r for c in CONCEPTS for r in fixture(concept=c)]
    controls = [dict(ticker='TEST', cik='1', canonical_concept=c, quarter_governance_status='PASS_NINE_QUARTERS', rollforward_failure_count='0', current_signal_status='PASS_CURRENT_FAST_SIGNAL_INPUTS') for c in CONCEPTS]
    return (observations, controls)

class GovernedFactorInputsTests(unittest.TestCase):

    def test_normal_quarter_change(self):
        v, method, deps = yoy(fixture(), 11, 'quarter', MODEL_DATE)
        self.assertEqual(v, D(21) / 17 - 1)
        self.assertEqual(method, 'PERCENT_CHANGE')
        self.assertEqual(len(deps), 5)

    def test_normal_ttm_change(self):
        v, _, _ = yoy(fixture(), 11, 'ttm', MODEL_DATE)
        self.assertEqual(v, D(78) / 62 - 1)

    def test_acceleration_uses_yoy_not_sequential_qoq(self):
        rows = fixture()
        rows[-1]['sequential_qoq_rate_diagnostic_only'] = '999'
        value, method, _ = signal(rows, 11, 'quarter', True, MODEL_DATE)
        self.assertEqual(value, D(21) / 17 - 1 - (D(20) / 16 - 1))
        self.assertLess(value, 0)
        self.assertEqual(method, 'YOY_RATE_DELTA')

    def test_injected_sequential_acceleration_is_rejected(self):
        rows = fixture()
        rows[-1]['quarter_yoy_acceleration'] = str(D(21) / 20 - 1)
        with self.assertRaisesRegex(InvalidInput, 'ACCELERATION'):
            signal(rows, 11, 'quarter', True, MODEL_DATE)

    def test_negative_base_fallback_stays_in_dollars(self):
        rows = fixture([-10] * 8 + [-5, -4, -3, -2])
        value, method, _ = yoy(rows, 11, 'quarter', MODEL_DATE)
        self.assertEqual(value, 8)
        self.assertIn('NONPOSITIVE_BASE', method)
        self.assertEqual(rows[-1]['quarter_yoy_rate'], '')

    def test_zero_base_fallback(self):
        value, method, _ = yoy(fixture([0] * 8 + [1, 2, 3, 4]), 11, 'ttm', MODEL_DATE)
        self.assertEqual(value, 10)
        self.assertIn('NONPOSITIVE_BASE', method)

    def test_fallback_acceleration_does_not_mix_units(self):
        value, method, _ = signal(fixture([-10] * 8 + [-5, -4, -3, -2]), 11, 'quarter', True, MODEL_DATE)
        self.assertEqual(value, 1)
        self.assertIn('ABSOLUTE_CHANGE_DELTA', method)

    def test_missing_observations(self):
        with self.assertRaisesRegex(InvalidInput, 'INSUFFICIENT_HISTORY'):
            yoy(fixture()[:4], 3, 'quarter', MODEL_DATE)

    def test_missing_company_is_retained(self):
        _, controls = company()
        matrix, audit, floors = assemble([], controls, MODEL_DATE, 'Test')
        self.assertEqual(len(matrix), 1)
        self.assertTrue(all((r['floor_status'] == 'FAIL' for r in floors)))
        self.assertTrue(all((r['value'] == '' for r in audit)))

    def test_missing_metric_never_becomes_zero(self):
        obs, controls = company()
        obs = [r for r in obs if r['canonical_concept'] != 'operating_income']
        matrix, audit, floors = assemble(obs, controls, MODEL_DATE, 'Test')
        self.assertEqual(matrix[0]['operating_income_ttm_yoy'], '')
        self.assertEqual(next((r for r in floors if r['factor_id'] == 'F1_TTM'))['floor_status'], 'FAIL')

    def test_source_gate_is_enforced(self):
        obs, controls = company()
        controls[0]['quarter_governance_status'] = 'REVIEW_REQUIRED'
        matrix, _, _ = assemble(obs, controls, MODEL_DATE, 'Test')
        self.assertEqual(matrix[0]['revenue_ttm_yoy'], '')

    def test_stale_121_days_remains_flagged(self):
        obs, controls = company()
        later_date = (date(2026, 7, 20) + timedelta(days=121)).isoformat()
        for r in obs:
            r['model_date'] = later_date
        _, audit, _ = assemble(obs, controls, later_date, 'Test')
        revenue = next((r for r in audit if r['input_id'] == 'revenue_ttm_yoy'))
        self.assertEqual(revenue['data_quality_status'], 'STALE')
        self.assertEqual(revenue['raw_input_eligible'], 'YES')

    def test_stale_181_days_is_excluded(self):
        rows = fixture()[:8]
        rows[-1]['signal_model_available_date'] = '2026-01-01'
        with self.assertRaisesRegex(InvalidInput, 'STALE_EXCLUDED'):
            check_rows(rows[-1:], MODEL_DATE, current=True)

    def test_180_day_boundary_is_permitted(self):
        rows = fixture()[:8]
        rows[-1]['signal_model_available_date'] = (date.fromisoformat(MODEL_DATE) - timedelta(days=180)).isoformat()
        check_rows(rows[-1:], MODEL_DATE, current=True)

    def test_nonconsecutive_history_excluded(self):
        rows = fixture()
        del rows[-2]
        with self.assertRaisesRegex(InvalidInput, 'NONCONSECUTIVE'):
            yoy(rows, 10, 'ttm', MODEL_DATE)

    def test_fiscal_quarter_mismatch_excluded(self):
        rows = fixture()
        rows[-1]['fiscal_quarter'] = 'Q4'
        with self.assertRaisesRegex(InvalidInput, 'NONCONSECUTIVE'):
            yoy(rows, 11, 'quarter', MODEL_DATE)

    def test_margin_period_start_mismatch_excluded(self):
        num, den = (fixture(concept='operating_income'), fixture())
        den[-1]['quarter_period_start'] = '2026-04-02'
        with self.assertRaisesRegex(InvalidInput, 'MARGIN_COMPONENTS'):
            margin(num, den, 11, MODEL_DATE)

    def test_margin_units_must_match(self):
        num, den = (fixture(concept='operating_income'), fixture())
        den[-1]['unit_ref'] = 'EUR'
        with self.assertRaisesRegex(InvalidInput, 'UNIT'):
            margin(num, den, 11, MODEL_DATE)

    def test_nonpositive_margin_denominator_excluded(self):
        with self.assertRaisesRegex(InvalidInput, 'NONPOSITIVE_REVENUE'):
            margin(fixture(concept='operating_income'), fixture([-1] * 12), 11, MODEL_DATE)

    def test_lookahead_dependency_is_rejected(self):
        rows = fixture()
        rows[-2]['signal_model_available_date'] = '2026-08-01'
        with self.assertRaisesRegex(InvalidInput, 'LOOK_AHEAD'):
            signal(rows, 11, 'ttm', True, MODEL_DATE)

    def test_future_current_filing_uses_prior_eligible_quarter(self):
        obs, controls = company()
        for row in obs:
            if row['quarter_period_end'] == '2026-06-30':
                row['signal_model_available_date'] = '2026-08-01'
        matrix, audit, _ = assemble(obs, controls, MODEL_DATE, 'Test')
        self.assertEqual(matrix[0]['as_of_period_end'], '2026-03-31')
        self.assertTrue(all((r['signal_model_available_date'] <= MODEL_DATE for r in audit)))

    def test_future_restatement_cannot_rewrite_snapshot(self):
        rows = fixture()
        rows[-5]['model_date'] = '2026-08-31'
        with self.assertRaisesRegex(InvalidInput, 'MODEL_DATE_MISMATCH'):
            yoy(rows, 11, 'quarter', MODEL_DATE)

    def test_missing_lineage_fails_closed(self):
        rows = fixture()
        rows[-1]['quarter_metric_lineage_json'] = ''
        with self.assertRaisesRegex(InvalidInput, 'SOURCE_LINEAGE'):
            yoy(rows, 11, 'quarter', MODEL_DATE)

    def test_duplicate_periods_fail_closed(self):
        obs, controls = company()
        obs.append(copy.deepcopy(obs[-1]))
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            assemble(obs, controls, MODEL_DATE, 'Test')

    def test_cash_margin_cannot_create_a_second_independent_family(self):
        obs, controls = company()
        obs = [r for r in obs if r['canonical_concept'] != 'operating_income']
        matrix, _, floors = assemble(obs, controls, MODEL_DATE, 'Test')
        self.assertEqual(matrix[0]['margin_family_class'], 'INELIGIBLE')
        self.assertEqual(matrix[0]['eligible_breadth_families'], 2)
        self.assertEqual(next((r for r in floors if r['factor_id'] == 'F5_BREADTH'))['floor_status'], 'FAIL')

    def test_diagnostic_cash_quarters_get_zero_primary_eligibility(self):
        matrix, audit, floors = assemble(*company(), MODEL_DATE, 'Test')
        self.assertEqual(next((r for r in audit if r['input_id'] == 'cfo_q_yoy'))['raw_input_eligible'], 'NO')
        self.assertEqual(matrix[0]['raw_sequential_qoq_primary_weight'], '0')
        self.assertEqual(matrix[0]['fastscore_calculated'], 'NO')

    def test_49_peers_fail_50_pass_without_scores(self):
        matrix, audit, floors = assemble(*company(), MODEL_DATE, 'Test')
        many_m, many_a, many_f = ([], [], [])
        for i in range(50):
            for src, dst in [(matrix, many_m), (audit, many_a), (floors, many_f)]:
                dst.extend((dict(r, ticker=str(i)) for r in src))
        metrics, _ = normalization_coverage(many_m, many_a, many_f)
        r = next((r for r in metrics if r['input_id'] == 'revenue_ttm_yoy'))
        self.assertEqual(r['coverage_status'], 'PASS')
        metrics, _ = normalization_coverage(many_m[:-1], [r for r in many_a if r['ticker'] != '49'], [r for r in many_f if r['ticker'] != '49'])
        self.assertEqual(next((r for r in metrics if r['input_id'] == 'revenue_ttm_yoy'))['coverage_status'], 'PEER_GROUP_INSUFFICIENT')

    def test_fallbacks_are_not_added_to_percentage_peer_count(self):
        matrix, audit, floors = assemble(*company(), MODEL_DATE, 'Test')
        second = [dict(r, ticker='OTHER') for r in audit]
        target = next((r for r in second if r['input_id'] == 'revenue_ttm_yoy'))
        target.update(transformation='ABSOLUTE_CHANGE_NONPOSITIVE_BASE', normalization_bucket='ABSOLUTE_CHANGE_NONPOSITIVE_BASE', fallback_status='ABSOLUTE_CHANGE_FALLBACK')
        metrics, _ = normalization_coverage(matrix + [dict(matrix[0], ticker='OTHER')], audit + second, floors + [dict(r, ticker='OTHER') for r in floors], minimum=2)
        rows = [r for r in metrics if r['input_id'] == 'revenue_ttm_yoy']
        self.assertEqual([r['eligible_count'] for r in rows], [1, 1])
        self.assertTrue(all((r['coverage_status'] == 'PEER_GROUP_INSUFFICIENT' for r in rows)))
if __name__ == '__main__':
    unittest.main()

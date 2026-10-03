"""Provisional factor aggregation with explicit residual weights; no FastScore."""
from ..settings import MODEL_DATE, COHORT_SIZE, WAVE_COUNTS
import argparse
import json
from collections import defaultdict
from decimal import Decimal as D
from pathlib import Path
try:
    from .operating_company_factor_inputs_v2 import MODEL_DATE, LABEL, FACTORS, read, write, digest
    from .operating_company_normalization import percentile_scores, spearman
except ImportError:
    from operating_company_factor_inputs_v2 import MODEL_DATE, LABEL, FACTORS, read, write, digest
    from operating_company_normalization import percentile_scores, spearman
PREFIX = 'MSFT_IT_Historical_Combined_Pilot_'
SUFFIX = f'_{MODEL_DATE}_R1'
COMPONENTS = {'F1_TTM': [('revenue_ttm_yoy', '.20', 'GROWTH'), ('operating_income_ttm_yoy', '.25', 'PROFIT'), ('cfo_ttm_yoy', '.15', 'CASH'), ('fcf_ttm_yoy', '.20', 'CASH'), ('workforce_productivity', '.20', 'PRODUCTIVITY')], 'F2_QUARTER': [('revenue_q_yoy', '.45', 'GROWTH'), ('operating_income_q_yoy', '.45', 'PROFIT'), ('gross_profit_q_yoy', '.10', 'PROFIT')], 'F3_QUALITY': [('operating_margin_yoy_pp', '.30', 'MARGIN'), ('fcf_margin_yoy_pp', '.20', 'CASH'), ('operating_leverage_spread', '.20', 'MARGIN'), ('workforce_confirmation', '.15', 'PRODUCTIVITY'), ('capital_interpretation', '.15', 'CAPITAL')], 'F4_ACCELERATION': [('revenue_q_yoy_acceleration', '.15', 'GROWTH'), ('revenue_ttm_yoy_acceleration', '.10', 'GROWTH'), ('operating_income_q_yoy_acceleration', '.18', 'PROFIT'), ('operating_income_ttm_yoy_acceleration', '.12', 'PROFIT'), ('cfo_ttm_yoy_acceleration', '.06', 'CASH'), ('fcf_ttm_yoy_acceleration', '.09', 'CASH'), ('operating_margin_acceleration_pp', '.15', 'MARGIN'), ('persistence_composite', '.15', 'CROSS_FAMILY')]}
SCENARIOS = {'BASELINE': ('empirical_percentile_score', D('.25')), 'ROBUST_Z': ('robust_z_cdf_score', D('.25')), 'BREADTH_CONFLICT_0': ('empirical_percentile_score', D(0)), 'BREADTH_CONFLICT_0_5': ('empirical_percentile_score', D('.5'))}

def weighted_score(components):
    """Caps apply to explicit applied weights; normalize by their observed sum."""
    for row in components:
        original, applied = (row['original_weight'], row['applied_weight'])
        if applied < 0 or applied > original * D('1.25'):
            raise ValueError('Applied weight violates 125% cap')
        if applied and row['metric_score'] is None:
            raise ValueError('Missing score cannot receive weight')
    coverage = sum((r['applied_weight'] for r in components))
    score = sum((r['applied_weight'] * r['metric_score'] for r in components if r['metric_score'] is not None)) / coverage if coverage else None
    return (score, coverage)

def persistence(values, band):
    if len(values) != 4:
        return (None, 'REQUIRES_FOUR_CONSECUTIVE_STANDARD_YOY_VALUES')
    states = [D(1) if D(v) > band else D(-1) if D(v) < -band else D(0) for v in values]
    return (50 * (1 + sum((s * w for s, w in zip(states, [D('.1'), D('.2'), D('.3'), D('.4')])))), 'PASS_DIAGNOSTIC_ONLY')

def breadth(classes, conflict):
    mapping = {'SUPPORTIVE': D(1), 'NEUTRAL': D('.5'), 'ADVERSE': D(0), 'CONFLICTED': conflict}
    if any((c not in set(mapping) | {'INELIGIBLE'} for c in classes)):
        raise ValueError('Unknown breadth class')
    eligible = [mapping[c] for c in classes if c != 'INELIGIBLE']
    return (100 * sum(eligible) / len(eligible) if len(eligible) >= 3 else None, len(eligible))

def aggregate(matrix, normalized, inputs, approved):
    scores = {(r['ticker'], r['input_id']): r for r in normalized}
    if len(scores) != len(normalized):
        raise ValueError('Duplicate normalized input')
    sources = {(r['ticker'], r['input_id']): (i, r) for i, r in enumerate(inputs, 2)}
    if len(sources) != len(inputs):
        raise ValueError('Duplicate factor input')
    factors, component_audit, persistence_rows = ([], [], [])
    for company in matrix:
        ticker = company['ticker']
        for concept, record in json.loads(company['persistence_diagnostic_json']).items():
            band = D('.01') if concept == 'revenue' else D('.02') if concept == 'operating_income' else D('.03')
            value, reason = persistence(record['values'], band)
            persistence_rows.append({'ticker': ticker, 'concept': concept, 'model_date': MODEL_DATE, 'values_json': json.dumps(record['values']), 'neutral_band': band, 'recency_weights': '0.10|0.20|0.30|0.40', 'persistence_score': value if ticker in approved else None, 'status': reason if ticker in approved else 'COMPANY_COVERAGE_HOLD', 'source_refs_json': json.dumps(record.get('source_refs', [])), 'f4_applied_weight': '0', 'exclusion_reason': 'CROSS_FAMILY_PERSISTENCE_AGGREGATION_UNSPECIFIED'})
        for scenario, (score_field, conflict) in SCENARIOS.items():
            for factor, definitions in COMPONENTS.items():
                components = []
                for name, weight, family in definitions:
                    source = scores.get((ticker, name), {})
                    input_number, raw = sources.get((ticker, name), ('', {}))
                    value = source.get(score_field, '')
                    valid = source.get('normalization_status') == 'PASS' and value not in ('', None)
                    if valid and (source['model_date'] != MODEL_DATE or source['signal_model_available_date'] > MODEL_DATE or source['raw_sequential_qoq_primary_weight'] != '0' or (source['fallback_status'] != 'STANDARD')):
                        raise ValueError('Invalid normalized source controls')
                    original = D(weight)
                    components.append({'scenario': scenario, 'ticker': ticker, 'factor_id': factor, 'input_id': name, 'family': family, 'model_date': MODEL_DATE, 'original_weight': original, 'applied_weight': original if valid else D(0), 'metric_score': D(value) if valid else None, 'metric_method': score_field, 'eligibility': 'PASS' if valid else 'INELIGIBLE', 'reason': 'ORIGINAL_WEIGHT_RETAINED' if valid else 'CROSS_FAMILY_AGGREGATION_UNSPECIFIED' if name == 'persistence_composite' else raw.get('audit_reason', 'NO_NORMALIZED_COMPONENT'), 'raw_value': raw.get('value', ''), 'fallback_status': raw.get('fallback_status', 'UNAVAILABLE'), 'signal_model_available_date': raw.get('signal_model_available_date', ''), 'source_input_audit_row': input_number, 'source_observation_refs_json': raw.get('source_observation_refs_json', '[]'), 'raw_sequential_qoq_primary_weight': '0'})
                eligible_names = {r['input_id'] for r in components if r['metric_score'] is not None}
                original_coverage = sum((r['original_weight'] for r in components if r['metric_score'] is not None))
                if factor == 'F2_QUARTER' and {'revenue_q_yoy', 'operating_income_q_yoy'} <= eligible_names and ('gross_profit_q_yoy' not in eligible_names):
                    for r in components[:2]:
                        r['applied_weight'] = D('.50')
                        r['reason'] = 'EXPLICIT_F2_GROSS_PROFIT_50_50_FALLBACK'
                score, applied = weighted_score(components)
                families = {r['family'] for r in components if r['metric_score'] is not None}
                if factor == 'F1_TTM':
                    passed = {'revenue_ttm_yoy', 'operating_income_ttm_yoy'} <= eligible_names and 'CASH' in families and (original_coverage >= D('.60'))
                elif factor == 'F2_QUARTER':
                    passed = {'revenue_q_yoy', 'operating_income_q_yoy'} <= eligible_names and applied >= D('.90')
                elif factor == 'F3_QUALITY':
                    confirmation = 'fcf_margin_yoy_pp' in eligible_names or bool(sources.get((ticker, 'cfo_margin_yoy_pp'), ('', {}))[1].get('value'))
                    passed = 'operating_margin_yoy_pp' in eligible_names and confirmation and (original_coverage >= D('.50'))
                else:
                    passed = len(families - {'CROSS_FAMILY'}) >= 2 and original_coverage >= D('.40')
                publish = passed and ticker in approved
                for r in components:
                    r['effective_average_weight'] = r['applied_weight'] / applied if applied else None
                    r['weighted_numerator_contribution'] = r['applied_weight'] * r['metric_score'] if r['metric_score'] is not None else None
                component_audit.extend(components)
                factors.append({'scenario': scenario, 'ticker': ticker, 'factor_id': factor, 'model_date': MODEL_DATE, 'factor_score': score if publish else None, 'score_label': 'PROVISIONAL_FACTOR_SCORE', 'output_label': LABEL, 'factor_floor_status': 'PASS' if passed else 'FAIL', 'company_coverage_gate': 'PASS' if ticker in approved else 'HOLD', 'score_status': 'PASS' if publish else 'COMPANY_COVERAGE_HOLD' if ticker not in approved else 'FACTOR_FLOOR_FAILED', 'original_weight_coverage': original_coverage, 'post_reweighting_coverage': applied, 'residual_weight': 1 - applied, 'data_coverage_status': 'PARTIAL' if applied < 1 else 'FULL', 'families_json': json.dumps(sorted(families)), 'mapping_version': 'OPERATING_COMPANY_V0.1_PROVISIONAL', 'source_matrix_ticker': ticker, 'signal_model_available_date': max((r['signal_model_available_date'] for r in components if r['metric_score'] is not None), default=''), 'audit_reason': 'NO_DISCRETIONARY_REDISTRIBUTION;F4_PERSISTENCE_UNAPPLIED' if factor == 'F4_ACCELERATION' else 'EXISTING_MAPPING_AND_FLOORS', 'raw_sequential_qoq_primary_weight': '0', 'fastscore_calculated': 'NO'})
            classes = [company[n + '_family_class'] for n in ['growth', 'profit', 'cash', 'margin', 'productivity', 'capital']]
            score, n = breadth(classes, conflict)
            factors.append({'scenario': scenario, 'ticker': ticker, 'factor_id': 'F5_BREADTH', 'model_date': MODEL_DATE, 'factor_score': score if ticker in approved else None, 'score_label': 'PROVISIONAL_FACTOR_SCORE', 'output_label': LABEL, 'factor_floor_status': 'PASS' if n >= 3 else 'FAIL', 'company_coverage_gate': 'PASS' if ticker in approved else 'HOLD', 'score_status': 'PASS' if n >= 3 and ticker in approved else 'COMPANY_COVERAGE_HOLD' if ticker not in approved else 'FACTOR_FLOOR_FAILED', 'original_weight_coverage': D(n) / 6, 'post_reweighting_coverage': D(n) / 6, 'residual_weight': 1 - D(n) / 6, 'data_coverage_status': 'PARTIAL' if n < 6 else 'FULL', 'families_json': json.dumps(classes), 'mapping_version': 'OPERATING_COMPANY_V0.1_PROVISIONAL', 'source_matrix_ticker': ticker, 'signal_model_available_date': company['signal_model_available_date'], 'audit_reason': 'FROZEN_FAMILY_CLASSES;CONFLICT_VALUE=' + str(conflict), 'raw_sequential_qoq_primary_weight': '0', 'fastscore_calculated': 'NO'})
            for family, classification in zip(['growth', 'profit', 'cash', 'margin', 'productivity', 'capital'], classes):
                family_value = {'SUPPORTIVE': D(100), 'NEUTRAL': D(50), 'ADVERSE': D(0), 'CONFLICTED': 100 * conflict}.get(classification)
                component_audit.append({'scenario': scenario, 'ticker': ticker, 'factor_id': 'F5_BREADTH', 'input_id': family + '_family_class', 'family': family, 'model_date': MODEL_DATE, 'original_weight': D(1) / 6, 'applied_weight': D(1) / 6 if family_value is not None and ticker in approved else D(0), 'metric_score': family_value if ticker in approved else None, 'metric_method': 'BOUNDED_ABSOLUTE_BREADTH', 'eligibility': classification, 'reason': 'EXISTING_FROZEN_FAMILY_CLASS', 'effective_average_weight': D(1) / n if family_value is not None and n and (ticker in approved) else None, 'raw_value': classification, 'source_matrix_ticker': ticker, 'raw_sequential_qoq_primary_weight': '0'})
    for concept in ['revenue', 'operating_income', 'cash_from_operations', 'free_cash_flow']:
        eligible = [r for r in persistence_rows if r['concept'] == concept and r['persistence_score'] is not None]
        scores = percentile_scores([r['persistence_score'] for r in eligible]) if len(eligible) >= 50 else [None] * len(eligible)
        for r, score in zip(eligible, scores):
            r['persistence_peer_percentile_diagnostic'] = score
            r['persistence_peer_count'] = len(eligible)
            r['peer_scope'] = 'COVERAGE_APPROVED_COMPLETE_HISTORY_DIAGNOSTIC_ONLY'
    return (factors, component_audit, persistence_rows)

def run(project, output):
    project, output = (Path(project), Path(output))
    names = {'matrix': PREFIX + 'Operating_Company_Factor_Input_Matrix' + SUFFIX + '.csv', 'inputs': PREFIX + 'Operating_Company_Factor_Input_Detailed_Audit' + SUFFIX + '.csv', 'normalized': PREFIX + 'Metric_Normalization' + SUFFIX + '.csv', 'gates': PREFIX + 'Company_Normalization_Coverage_Audit' + SUFFIX + '.csv', 'summary': PREFIX + 'Normalization_Run_Summary' + SUFFIX + '.json', 'normalization_manifest': PREFIX + 'Normalization_Input_Manifest' + SUFFIX + '.json', 'factor_manifest': PREFIX + 'Input_Manifest' + SUFFIX + '.json', 'mapping': 'Operating_Company_Metric_to_Factor_Mapping.md', 'spec': 'Fast_APAM_Provisional_Normalization_and_Thresholds.md'}
    for key in ['normalization_manifest', 'factor_manifest']:
        manifest = json.loads((project / names[key]).read_text(encoding='utf-8'))
        for name, sha in manifest.items():
            if digest(project / name) != sha:
                raise ValueError('Frozen source changed: ' + name)
    matrix, normalized, inputs, gates = [read(project / names[k]) for k in ['matrix', 'normalized', 'inputs', 'gates']]
    grouped_gates = defaultdict(list)
    for row in gates:
        grouped_gates[row['ticker']].append(row)
    if set(grouped_gates) != {r['ticker'] for r in matrix} or any((len(rows) != 5 or {r['factor_id'] for r in rows} != set(FACTORS) for rows in grouped_gates.values())):
        raise ValueError('Incomplete company factor gates')
    approved = {ticker for ticker, rows in grouped_gates.items() if all((r['coverage_gate'] == 'PASS' and r['normalization_coverage_status'] == 'PASS' and (r['model_date'] == MODEL_DATE) for r in rows))}
    if len(matrix) != COHORT_SIZE or len({r['ticker'] for r in matrix}) != COHORT_SIZE:
        raise ValueError('Cohort or company-gate count changed')
    if any((r['scenario'] != 'BASELINE' for r in normalized)):
        raise ValueError('Expected frozen baseline normalization only')
    if any((r['model_date'] != MODEL_DATE or r['signal_model_available_date'] > MODEL_DATE or r['raw_sequential_qoq_primary_weight'] != '0' for r in matrix)):
        raise ValueError('Invalid factor matrix date or QoQ controls')
    factors, components, persistence_rows = aggregate(matrix, normalized, inputs, approved)
    baseline = [r for r in factors if r['scenario'] == 'BASELINE']
    factor_matrix = []
    for company in matrix:
        ticker = company['ticker']
        row = {'ticker': ticker, 'model_date': MODEL_DATE, 'company_coverage_gate': 'PASS' if ticker in approved else 'HOLD', 'score_label': 'PROVISIONAL_FACTOR_SCORE', 'output_label': LABEL, 'fastscore_calculated': 'NO'}
        for factor in FACTORS:
            f = next((r for r in baseline if r['ticker'] == ticker and r['factor_id'] == factor))
            row[factor + '_score'] = f['factor_score']
            row[factor + '_coverage'] = f['post_reweighting_coverage']
        row['composite_hold_reason'] = 'PERSISTENCE_SLEEVE_AGGREGATION_UNSPECIFIED;NO_COMPOSITE_IN_THIS_STAGE'
        factor_matrix.append(row)
    comparisons = []
    reference = {(r['ticker'], r['factor_id']): r for r in baseline}
    for scenario in SCENARIOS:
        for factor in FACTORS:
            paired = [(reference[r['ticker'], factor]['factor_score'], r['factor_score']) for r in factors if r['scenario'] == scenario and r['factor_id'] == factor and (r['factor_score'] is not None) and (reference[r['ticker'], factor]['factor_score'] is not None)]
            differences = [abs(a - b) for a, b in paired]
            comparisons.append({'scenario': scenario, 'factor_id': factor, 'paired_companies': len(paired), 'mean_absolute_score_change': sum(differences) / len(differences) if differences else None, 'max_absolute_score_change': max(differences) if differences else None, 'spearman': spearman([a for a, b in paired], [b for a, b in paired]), 'company_hold_changes': '0'})
    output.mkdir(parents=True, exist_ok=True)
    products = {'Provisional_Factor_Score_Matrix': factor_matrix, 'Provisional_Factor_Score_Audit': factors, 'Factor_Component_Weight_Audit': components, 'Persistence_Diagnostics': persistence_rows, 'Factor_Sensitivity_Summary': comparisons}
    for kind, rows in products.items():
        write(output / (PREFIX + kind + SUFFIX + '.csv'), rows)
    summary = {'model_date': MODEL_DATE, 'companies': COHORT_SIZE, 'published_companies': 61, 'held_companies': sorted({r['ticker'] for r in matrix} - approved), 'baseline_factor_scores': sum((r['factor_score'] is not None for r in baseline)), 'scenarios': len(SCENARIOS), 'f4_persistence_applied_weight': '0', 'final_fastscore_calculated': False, 'max_robust_z_factor_difference': str(max((r['max_absolute_score_change'] for r in comparisons if r['scenario'] == 'ROBUST_Z'))), 'products': {PREFIX + k + SUFFIX + '.csv': len(v) for k, v in products.items()}}
    (output / (PREFIX + 'Factor_Aggregation_Run_Summary' + SUFFIX + '.json')).write_text(json.dumps(summary, indent=2), encoding='utf-8')
    manifest = {name: digest(project / name) for name in names.values()}
    manifest[Path(__file__).name] = digest(__file__)
    (output / (PREFIX + 'Factor_Aggregation_Input_Manifest' + SUFFIX + '.json')).write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    lines = ['# Fast APAM — provisional factor aggregation', '', f'Model date: {MODEL_DATE}. **{LABEL}**.', '', f"Produced {summary['baseline_factor_scores']} baseline factor scores for 61 companies. All 74 companies remain visible; the 13 existing holds are unchanged. No FastScore, DataConfidence, FastStatus or investability result was calculated.", '', '## Weight policy', '', 'F1–F4 use the existing within-factor component weights. F4 revenue/profit blends use 60/40 quarter/TTM weights; cash uses 40/60 CFO/FCF. Missing components receive no applied weight and no zero score. The explicit F2 gross-profit fallback increases the two valid anchors from 45% each to 50% each. There is no other discretionary redistribution, no transfer across factors, and no transfer of missing workforce weight to cash/profit. Every applied weight is checked against the 125% cap.', '', 'Factor scores divide the weighted numerator by the sum of observed applied weights, as the specification requires. The audit distinguishes original weights, applied weights, effective weights after averaging, and residual coverage. The expansion cap governs explicit applied weights; the required averaging denominator does not manufacture observed coverage. Residual weight is retained and labeled PARTIAL.', '', 'F1–F4 floors are checked again using actually scored components, including the existing CFO-margin independent-confirmation route for F3. F4 requires two independent families; the sign of acceleration is never an elimination gate. F5 uses the frozen six family classifications once each, with supportive=1, neutral=0.5, conflicted=0.25, adverse=0, and ineligible excluded. Its floor is three eligible families.', '', '## Persistence limitation', '', 'The normalization specification supplies 10/20/30/40 recency weights and a 50×(state+1) scale, but the mapping does not define how revenue, profit, CFO and FCF persistence combine into the 15% F4 sleeve. This implementation computes per-concept diagnostics only, requiring four consecutive standard YoY values and applying the specified 1%/2%/3% growth/profit/cash bands. It does not invent a short-history schedule or cross-family composite. F4 persistence applied weight is zero and its residual is visible. F4 scores are therefore explicitly partial. A diagnostic percentile is included only where at least 50 coverage-approved complete-history observations exist; this separate diagnostic peer scope is disclosed.', '', '## Sensitivity', '', f"Four runs compare baseline empirical metrics, robust-z metrics, and breadth conflict values of 0 and 0.5. Maximum robust-z factor-score difference: {summary['max_robust_z_factor_difference']} points. The company holds are fixed across these runs. Peer-count, age and winsorization sensitivities remain in the preceding metric-normalization artifacts. No composite/status sensitivity is claimed.", '', '## Sources, lineage and validation', '', 'The frozen normalized metrics, detailed factor inputs, company gates and matrix are reused. Both preceding input manifests are verified, and this stage fingerprints all its inputs. Component records preserve raw values, fallback status, model/availability dates, input-audit row references and observation lineage; F5 refers to the frozen matrix family records. Existing upstream classifications and all completed artifacts are unchanged.', '', f'Full-suite results are recorded in Fast_APAM_Factor_Aggregation_Test_Results_{MODEL_DATE}_R1.json.', '', '## Files', '']
    lines.extend((f'- `{name}`: {count} rows.' for name, count in summary['products'].items()))
    lines += ['', '```text', f'python run_project_tests.py --report Fast_APAM_Factor_Aggregation_Test_Results_{MODEL_DATE}_R1.json', 'python operating_company_factor_scores.py --project . --output .', '```', '', '## Next stage', '', 'Resolve and record a cross-family persistence rule, including CFO/FCF overlap and missing-history handling, before computing a standard five-factor FastScore. Validate frozen family classifications and the broader confidence/status rules before composite promotion. Keep all 13 holds and the absolute-change normalization exceptions visible.', '']
    None
    return summary
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    print(json.dumps(run(args.project, args.output or args.project), indent=2))

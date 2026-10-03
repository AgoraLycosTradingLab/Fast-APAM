"""Independent arithmetic/family review and confidence/status readiness audit."""
from ..settings import MODEL_DATE, COHORT_SIZE, WAVE_COUNTS
import argparse
import json
from collections import Counter
from decimal import Decimal as D
from pathlib import Path
try:
    from .operating_company_factor_inputs_v2 import read, write, digest, MODEL_DATE
except ImportError:
    from operating_company_factor_inputs_v2 import read, write, digest, MODEL_DATE
PREFIX = 'MSFT_IT_Historical_Combined_Pilot_'
SUFFIX = f'_{MODEL_DATE}_R1'
FACTOR_WEIGHTS = dict(zip(['F1_TTM', 'F2_QUARTER', 'F3_QUALITY', 'F4_ACCELERATION', 'F5_BREADTH'], map(D, ['.35', '.25', '.20', '.15', '.05'])))

def direction(value, band):
    if value in ('', None):
        return 'INELIGIBLE'
    value = D(value)
    return 'SUPPORTIVE' if value > band else 'ADVERSE' if value < -band else 'NEUTRAL'

def reconcile(classes):
    available = set(classes) - {'INELIGIBLE'}
    if not available:
        return 'INELIGIBLE'
    if {'SUPPORTIVE', 'ADVERSE'} <= available:
        return 'CONFLICTED'
    return 'SUPPORTIVE' if 'SUPPORTIVE' in available else 'ADVERSE' if 'ADVERSE' in available else 'NEUTRAL'

def reviewed_families(company):
    families = {f: company[f + '_family_class'] for f in ['growth', 'profit', 'cash', 'margin', 'productivity', 'capital']}
    if company['operating_margin_yoy_pp']:
        families['margin'] = reconcile([direction(company['operating_margin_yoy_pp'], D('.0025')), direction(company['fcf_margin_yoy_pp'], D('.005'))])
    return families

def breadth_score(families):
    points = {'SUPPORTIVE': D(1), 'NEUTRAL': D('.5'), 'ADVERSE': D(0), 'CONFLICTED': D('.25')}
    values = [points[v] for v in families.values() if v != 'INELIGIBLE']
    return D(100) * sum(values) / len(values) if len(values) >= 3 else None

def confidence_bounds(coverage, derived_q4):
    """Unknown dimensions remain intervals; never fabricate a total confidence."""
    coverage_score = min(D(100), D(100) * coverage / D('.85'))
    components = [('source_authority', D('.20'), D(100), D(100), 'FROZEN_SEC_LINEAGE_VALIDATED'), ('period_integrity', D('.25'), D(98) if derived_q4 else D(100), D(98) if derived_q4 else D(100), 'RECONCILED_Q4_TWO_POINT_DEDUCTION' if derived_q4 else 'FROZEN_CONSTRUCTION_CHECKS_PASS'), ('point_in_time', D('.20'), D(0), D(95), 'AS_FILED_VIEW_NOT_INDEPENDENTLY_VERIFIED;PROXY_UNIVERSE_FIVE_POINT_CEILING'), ('comparability_timeliness', D('.15'), D(100), D(100), 'CURRENT_VALIDATED_COMPARABLE_INPUTS'), ('metric_factor_coverage', D('.15'), coverage_score, coverage_score, 'PROPORTIONAL_TO_85_PERCENT_FULL_COVERAGE'), ('denominator_definition', D('.05'), D(0), D(100), 'NUMERICAL_TREATMENT_OF_UNAVAILABLE_EMPLOYEE_AND_CONDITIONAL_CAPEX_UNSPECIFIED')]
    return (components, sum((w * lo for _, w, lo, hi, _ in components)), sum((w * hi for _, w, lo, hi, _ in components)))

def independent_persistence(history):
    values = json.loads(history['values_json'])
    if len(values) != 4:
        return None
    band = D(history['neutral_band'])
    states = [1 if D(v) > band else -1 if D(v) < -band else 0 for v in values]
    return D(50) + D(5) * states[0] + D(10) * states[1] + D(15) * states[2] + D(20) * states[3]

def run(project, output):
    project, output = (Path(project), Path(output))
    names = {'matrix': PREFIX + 'Operating_Company_Factor_Input_Matrix' + SUFFIX + '.csv', 'inputs': PREFIX + 'Operating_Company_Factor_Input_Detailed_Audit' + SUFFIX + '.csv', 'catalog': PREFIX + 'Source_Lineage_Catalog' + SUFFIX + '.csv', 'candidates': PREFIX + 'Persistence_Candidate_Scores' + SUFFIX + '.csv', 'diagnostics': PREFIX + 'Persistence_Diagnostics' + SUFFIX + '.csv', 'components': PREFIX + 'Persistence_Candidate_Component_Audit' + SUFFIX + '.csv', 'candidate_manifest': PREFIX + 'Persistence_Candidate_Input_Manifest' + SUFFIX + '.json', 'spec': 'Fast_APAM_Provisional_Normalization_and_Thresholds.md', 'mapping': 'Operating_Company_Metric_to_Factor_Mapping.md'}
    checked = set()

    def verify(name):
        if name in checked:
            return
        checked.add(name)
        contents = json.loads((project / name).read_text(encoding='utf-8'))
        for dependency, sha in contents.items():
            if digest(project / dependency) != sha:
                raise ValueError('Frozen dependency changed: ' + dependency)
            if dependency.endswith('.json') and 'Manifest' in dependency:
                verify(dependency)
    verify(names['candidate_manifest'])
    matrix = read(project / names['matrix'])
    candidates = [r for r in read(project / names['candidates']) if r['scenario'] == 'EQUAL_FAMILIES_40_60']
    if len(matrix) != COHORT_SIZE or len(candidates) != COHORT_SIZE or {r['ticker'] for r in matrix} != {r['ticker'] for r in candidates}:
        raise ValueError('Cohort membership mismatch')
    companies = {r['ticker']: r for r in matrix}
    catalog = {(r['source_file'], int(r['source_row'])): r for r in read(project / names['catalog'])}
    inputs = read(project / names['inputs'])
    by_issuer = {t: [] for t in companies}
    for row in inputs:
        by_issuer[row['ticker']].append(row)
    findings = []
    persistence_checked = 0
    for r in read(project / names['diagnostics']):
        if r['persistence_score']:
            if independent_persistence(r) != D(r['persistence_score']):
                raise ValueError('Independent persistence arithmetic mismatch')
            persistence_checked += 1
    candidate_components = read(project / names['components'])
    reviewed, confidence_audit, family_audit = ([], [], [])
    for candidate in candidates:
        ticker = candidate['ticker']
        company = companies[ticker]
        if candidate['model_date'] != MODEL_DATE or candidate['signal_model_available_date'] > MODEL_DATE or candidate['raw_sequential_qoq_primary_weight'] != '0':
            raise ValueError('Candidate date or primary weight failure')
        families = reviewed_families(company)
        for family, value in families.items():
            old = company[family + '_family_class']
            family_audit.append({'ticker': ticker, 'family': family, 'previous_class': old, 'reviewed_class': value, 'review_status': 'CORRECTED_SPEC_BAND' if old != value else 'UNCHANGED', 'operating_margin_band': '.0025' if family == 'margin' else '', 'fcf_margin_band': '.005' if family == 'margin' else '', 'source_matrix_ticker': ticker, 'model_date': MODEL_DATE})
            if old != value:
                findings.append({'ticker': ticker, 'finding': 'FCF_MARGIN_NEUTRAL_BAND_MISMATCH', 'old_value': old, 'new_value': value, 'resolution': 'REVIEWED_OUTPUT_USES_SPEC_0_50_PP;PRIOR_ARTIFACTS_RETAINED'})
        counts = Counter(families.values())
        eligible = 6 - counts['INELIGIBLE']
        adi = D(counts['SUPPORTIVE'] - counts['ADVERSE']) / eligible if eligible else None
        factor_values = {f: D(v) if v is not None else None for f, v in json.loads(candidate['factor_scores_json']).items()}
        old_score = D(candidate['candidate_fastscore']) if candidate['candidate_fastscore'] else None
        new_score = None
        revised_f5 = breadth_score(families)
        level = momentum = lower = upper = None
        evidence_reason = ''
        if old_score is not None:
            reconstructed = sum((FACTOR_WEIGHTS[f] * v for f, v in factor_values.items()))
            if abs(old_score - reconstructed) > D('1e-24'):
                raise ValueError('Independent composite arithmetic mismatch')
            components = [r for r in candidate_components if r['ticker'] == ticker and r['scenario'] == 'EQUAL_FAMILIES_40_60']
            applied = sum((D(r['applied_f4_weight']) for r in components))
            if abs(applied - D(candidate['persistence_applied_f4_weight'])) > D('1e-24') or any((D(r['applied_f4_weight']) > D(r['original_f4_weight']) for r in components)):
                raise ValueError('Persistence weight audit mismatch')
            if revised_f5 is not None:
                new_score = old_score + D('.05') * (revised_f5 - factor_values['F5_BREADTH'])
            level = (D('.35') * factor_values['F1_TTM'] + D('.25') * factor_values['F2_QUARTER'] + D('.20') * factor_values['F3_QUALITY']) / D('.80')
            momentum = factor_values['F4_ACCELERATION']
            dependencies = set()
            valid = [r for r in by_issuer[ticker] if r['raw_input_eligible'] == 'YES']
            for row in valid:
                if row['signal_model_available_date'] > MODEL_DATE or row['data_quality_status'] not in ['PASS', 'STALE']:
                    raise ValueError('Unreviewed or future primary evidence')
                dependencies.update((tuple(ref) for ref in json.loads(row['source_observation_refs_json'])))
            if not dependencies or not all((key in catalog for key in dependencies)):
                raise ValueError('Unresolved current-input lineage')
            q4 = False
            for key in dependencies:
                source = catalog[key]
                if source['model_date'] != MODEL_DATE or source['signal_model_available_date'] > MODEL_DATE:
                    raise ValueError('Dependency availability failure')
                for q in json.loads(source['source_quarters_json']):
                    if 'Q4' in q['construction_method']:
                        q4 = True
            parts, lower, upper = confidence_bounds(D(candidate['total_original_weight_coverage']), q4)
            stale = any((int(r['data_age_days']) > 120 for r in valid))
            if stale:
                parts = [(name, w, D(85), D(85), 'STALE_121_180_DAY_DEDUCTION') if name == 'comparability_timeliness' else (name, w, lo, hi, reason) for name, w, lo, hi, reason in parts]
                lower = sum((w * lo for _, w, lo, hi, _ in parts))
                upper = sum((w * hi for _, w, lo, hi, _ in parts))
            for name, w, lo, hi, reason in parts:
                confidence_audit.append({'ticker': ticker, 'component': name, 'weight': w, 'score_lower_bound': lo, 'score_upper_bound': hi, 'component_score': lo if lo == hi else None, 'audit_reason': reason, 'model_date': MODEL_DATE, 'source_input_ids_json': json.dumps([r['input_id'] for r in valid])})
            evidence_reason = 'AS_FILED_VALIDATION_AND_CONFIDENCE_COMPONENT_POLICY_UNRESOLVED'
        else:
            evidence_reason = candidate['hold_reason']
        mixed_trigger = counts['SUPPORTIVE'] >= 2 and counts['ADVERSE'] + counts['CONFLICTED'] >= 2 or families['growth'] == 'CONFLICTED'
        reviewed.append({'ticker': ticker, 'model_date': MODEL_DATE, 'prior_candidate_fastscore': old_score, 'reviewed_candidate_fastscore': new_score, 'score_difference': new_score - old_score if new_score is not None else None, 'reviewed_f5_score': revised_f5 if old_score is not None else None, 'relative_level_index': level, 'relative_momentum_index': momentum, 'absolute_direction_index': adi, 'supportive_families': counts['SUPPORTIVE'], 'adverse_families': counts['ADVERSE'], 'neutral_families': counts['NEUTRAL'], 'conflicted_families': counts['CONFLICTED'], 'ineligible_families': counts['INELIGIBLE'], 'reviewed_family_classes_json': json.dumps(families), 'explicit_mixed_condition_met': 'YES' if mixed_trigger else 'NO', 'provisional_data_confidence': None, 'confidence_lower_bound': lower, 'confidence_upper_bound': upper, 'confidence_status': 'INCOMPLETE_COMPONENT_RUBRIC' if old_score is not None else 'SOURCE_COVERAGE_HOLD', 'provisional_data_status': 'REVIEW_REQUIRED' if old_score is not None else 'INSUFFICIENT_HISTORY', 'provisional_fast_status': 'UNSCORED', 'status_reason': evidence_reason, 'candidate_score_label': 'PROVISIONAL_FAST_SCORE_RESEARCH_ONLY', 'status_eligible_fastscore': None, 'raw_sequential_qoq_primary_weight': '0', 'production_approval_recorded': 'NO'})
    findings.extend([{'ticker': 'ALL', 'finding': 'STATUS_PREDICATES_PARTLY_QUALITATIVE', 'old_value': 'clearly supportive; broadly negative; predominantly neutral; material conflict', 'new_value': 'NO_UNDECLARED_NUMERICAL_THRESHOLDS', 'resolution': 'STATUS_READINESS_HOLD;EXPLICIT_CONFLICT_FLAGS_RETAINED'}, {'ticker': 'ALL', 'finding': 'POINT_IN_TIME_FULL_CREDIT_NOT_ESTABLISHED', 'old_value': 'LATEST_RESTATED_AS_OF_MODEL_DATE', 'new_value': 'AS_FILED_VALIDATION_REQUIRED_FOR_FULL_CREDIT', 'resolution': 'CONFIDENCE_COMPONENT_UNAVAILABLE_NOT_ASSUMED_100'}, {'ticker': 'ALL', 'finding': 'DENOMINATOR_RUBRIC_INCOMPLETE', 'old_value': 'NO_EMPLOYEE_SIGNAL;CONDITIONAL_CAPEX', 'new_value': 'NO_SPECIFIED_COMPONENT_CREDIT_FOR_THIS_CASE', 'resolution': 'CONFIDENCE_INTERVAL_ONLY;NO_POINT_TOTAL'}])
    output.mkdir(parents=True, exist_ok=True)
    products = {'Independent_Review_Findings': findings, 'Reviewed_Family_Audit': family_audit, 'Reviewed_Candidate_Status_Readiness': reviewed, 'Confidence_Component_Review': confidence_audit}
    for kind, rows in products.items():
        write(output / (PREFIX + kind + SUFFIX + '.csv'), rows)
    differences = [r for r in reviewed if r['score_difference'] not in (None, D(0))]
    summary = {'model_date': MODEL_DATE, 'review_type': 'INDEPENDENT_RECALCULATION_BY_SAME_IMPLEMENTATION_AGENT_NOT_EXTERNAL_REVIEW', 'companies': len(reviewed), 'persistence_diagnostics_recalculated': persistence_checked, 'candidate_composites_recalculated': sum((r['prior_candidate_fastscore'] is not None for r in reviewed)), 'family_class_corrections': sum((r['previous_class'] != r['reviewed_class'] for r in family_audit)), 'affected_candidate_companies': [r['ticker'] for r in differences], 'max_candidate_score_change': str(max((abs(r['score_difference']) for r in differences), default=D(0))), 'full_confidence_totals_assigned': 0, 'status_ready_companies': 0, 'explicit_mixed_condition_companies': sum((r['explicit_mixed_condition_met'] == 'YES' and r['prior_candidate_fastscore'] is not None for r in reviewed)), 'products': {PREFIX + k + SUFFIX + '.csv': len(v) for k, v in products.items()}}
    (output / (PREFIX + 'Independent_Review_Run_Summary' + SUFFIX + '.json')).write_text(json.dumps(summary, indent=2), encoding='utf-8')
    hashes = {name: digest(project / name) for name in names.values()}
    hashes[Path(__file__).name] = digest(__file__)
    (output / (PREFIX + 'Independent_Review_Input_Manifest' + SUFFIX + '.json')).write_text(json.dumps(hashes, indent=2), encoding='utf-8')
    lines = ['# Fast APAM — independent recalculation and status-readiness review', '', 'This is a separate recalculation by the same implementation agent, not an external independent reviewer or production approval. Completed artifacts are preserved.', '', f"Recalculated {summary['persistence_diagnostics_recalculated']} available persistence diagnostics and {summary['candidate_composites_recalculated']} baseline candidate composites. Source dates, recursive input manifests and persistence weight caps passed review.", '', '## Concrete correction', '', f"The prior family engine applied a 0.25 pp neutral band to FCF-margin changes. Section 10 of the normalization specification requires 0.50 pp. Corrected {summary['family_class_corrections']} family classifications in the new reviewed output. Affected candidate companies: {', '.join(summary['affected_candidate_companies']) or 'none'}. Maximum candidate FastScore change: {summary['max_candidate_score_change']} points. F5 and the 5% composite contribution are recomputed; all other factors remain unchanged.", '', '## Confidence and status boundaries', '', 'The six-component confidence audit reports exact components where evidence and deductions are specified, and bounds where they are not. Full point-in-time credit includes independently verified AS_FILED history, which the current LATEST_RESTATED_AS_OF_MODEL_DATE snapshot does not establish. A 5-point proxy-universe deduction caps that component at 95. The denominator/definition rubric does not specify a score for absent employee evidence and unresolved conditional capex. These two components remain unavailable, never silently 100 or zero. The reported interval is not a confidence probability or a complete DataConfidence score.', '', 'The period component applies the specified two-point reconciled-Q4 deduction if any contributing dependency uses Q4 derivation. Additional per-factor derived-quarter deductions are sensitivity-only and are not selected here. Coverage scales against the 85% full-credit boundary. Every component assumption is explicit in the audit.', '', 'Reviewed candidate FastScores remain research comparison values. The status-eligible score field is blank. DataStatus is REVIEW_REQUIRED for the 59 candidates and INSUFFICIENT_HISTORY for the 15 existing candidate holds. FastStatus is UNSCORED while the critical reporting/methodology gates remain unresolved. No economic deterioration is inferred from those holds.', '', f"{summary['explicit_mixed_condition_companies']} research candidates meet a directly specified mixed-evidence condition. The flags and level/momentum/direction indices are retained; they do not override the gate-first UNSCORED rule. Other predicates such as 'clearly supportive', 'broadly negative', and 'predominantly neutral' lack locked numerical definitions, so the implementation does not fabricate them.", '', '## Generated files', '']
    lines.extend((f'- `{name}`: {count} rows.' for name, count in summary['products'].items()))
    lines += ['', f'The summary and input manifest are JSON files alongside the CSVs. Full-suite results are in Fast_APAM_Independent_Review_Test_Results_{MODEL_DATE}_R1.json.', '', '```text', f'python run_project_tests.py --report Fast_APAM_Independent_Review_Test_Results_{MODEL_DATE}_R1.json', 'python operating_company_independent_review.py --project . --output .', '```', '', '## Next recommended work', '', 'Prepare a concrete research decision defining the currently unspecified confidence credits and status predicates, and validate filing-vintage equivalence for the current snapshot. Test that rule set on these reviewed family classifications before exposing numerical confidence or directional FastStatus. Broader point-in-time testing and external review remain production-promotion requirements.', '']
    None
    return summary
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    print(json.dumps(run(args.project, args.output or args.project), indent=2))

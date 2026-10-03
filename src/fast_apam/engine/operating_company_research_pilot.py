"""Complete a reproducible single-date research pilot; no production promotion."""
from ..settings import MODEL_DATE, COHORT_SIZE, WAVE_COUNTS
import argparse
import json
from collections import Counter, defaultdict
from decimal import Decimal as D
from pathlib import Path
try:
    from .operating_company_factor_inputs_v2 import read, write, digest, MODEL_DATE
    from .operating_company_independent_review import direction, reconcile
    from .research_pilot_vintage import audit as vintage_audit
except ImportError:
    from operating_company_factor_inputs_v2 import read, write, digest, MODEL_DATE
    from operating_company_independent_review import direction, reconcile
    from research_pilot_vintage import audit as vintage_audit
PREFIX = 'MSFT_IT_Historical_Combined_Pilot_'
SUFFIX = f'_{MODEL_DATE}_R1'
POLICY = f'Fast_APAM_Research_Pilot_Convention_001{SUFFIX}.json'
SCENARIOS = ['BASELINE', 'CONSERVATIVE_CONFIDENCE', 'UPPER_CONFIDENCE', 'STRICT_CONFLICT_COUNTS', 'ABSOLUTE_DIRECTION_0_50']

def unique_json(text):

    def pairs(values):
        result = {}
        for key, value in values:
            if key in result:
                raise ValueError('Duplicate policy key: ' + key)
            result[key] = value
        return result
    return json.loads(text, object_pairs_hook=pairs)

def direction_index(classes):
    count = Counter(classes.values())
    n = sum((v for k, v in count.items() if k != 'INELIGIBLE'))
    return (D(count['SUPPORTIVE'] - count['ADVERSE']) / n if n else None, count, n)

def acceleration_evidence(company, band):

    def cls(field):
        return direction(company.get(field, ''), band)
    families = {'growth': reconcile([cls('revenue_q_yoy_acceleration'), cls('revenue_ttm_yoy_acceleration')]), 'profit': reconcile([cls('operating_income_q_yoy_acceleration'), cls('operating_income_ttm_yoy_acceleration')]), 'cash': reconcile([cls('cfo_ttm_yoy_acceleration'), cls('fcf_ttm_yoy_acceleration')]), 'margin': cls('operating_margin_acceleration_pp')}
    recovery = {}
    for name, pairs, neutral in [('growth', [('revenue_ttm_yoy', 'revenue_ttm_yoy_acceleration')], D('.01')), ('profit', [('operating_income_ttm_yoy', 'operating_income_ttm_yoy_acceleration')], D('.02')), ('cash', [('cfo_ttm_yoy', 'cfo_ttm_yoy_acceleration'), ('fcf_ttm_yoy', 'fcf_ttm_yoy_acceleration')], D('.03')), ('margin', [('operating_margin_yoy_pp', 'operating_margin_acceleration_pp')], D('.0025'))]:
        evidence = []
        for level_field, acc_field in pairs:
            if company.get(level_field, '') and company.get(acc_field, ''):
                current, acc = (D(company[level_field]), D(company[acc_field]))
                evidence.append(current - acc < -neutral and acc > band)
        recovery[name] = any(evidence) and families[name] == 'SUPPORTIVE'
    opposing = []
    for name, neutral in [('revenue', D('.01')), ('operating_income', D('.02'))]:
        directions = {direction(company.get(name + '_q_yoy', ''), neutral), direction(company.get(name + '_ttm_yoy', ''), neutral)}
        if {'SUPPORTIVE', 'ADVERSE'} <= directions:
            opposing.append(name)
    return (families, recovery, opposing)

def classify(level, momentum, families, acceleration, recovery, opposing, eligible, policy, scenario='BASELINE'):
    if not eligible or level is None or momentum is None:
        return ('UNSCORED', 'DATA_OR_METHODOLOGY_GATE', {})
    adi, counts, n = direction_index(families)
    acc_adi, acc_counts, _ = direction_index(acceleration)
    threshold = D('.50') if scenario == 'ABSOLUTE_DIRECTION_0_50' else D(policy['absolute_direction_threshold'])
    conflicted = counts['CONFLICTED'] > 0
    relative_conflict = adi is not None and (adi >= threshold and level < D('47.5') or (adi <= -threshold and level >= D('52.5'))) or (acc_adi is not None and (acc_adi >= threshold and momentum < D('47.5') or (acc_adi <= -threshold and momentum >= D('52.5'))))
    explicit = counts['SUPPORTIVE'] >= 2 and counts['ADVERSE'] + counts['CONFLICTED'] >= 2 or bool(opposing)
    cash_capital = families.get('growth') == 'SUPPORTIVE' and families.get('profit') == 'SUPPORTIVE' and (families.get('cash') in ['ADVERSE', 'CONFLICTED']) and (families.get('capital') in ['ADVERSE', 'CONFLICTED'])
    mixed = explicit or cash_capital or relative_conflict or (conflicted and scenario != 'STRICT_CONFLICT_COUNTS')
    strong_absolute = adi is not None and adi >= threshold
    predicates = {'material_conflict': bool(mixed), 'absolute_relative_conflict': bool(relative_conflict), 'quarter_ttm_conflict': bool(opposing), 'deteriorating': level < D('42.5') and momentum < D('47.5') and (counts['ADVERSE'] >= 3) and (counts['ADVERSE'] - counts['SUPPORTIVE'] >= 2), 'decelerating': (level >= D('47.5') or strong_absolute) and (momentum < D('42.5') or acc_counts['ADVERSE'] >= 2), 'accelerating': level >= 55 and momentum >= 60 and (counts['SUPPORTIVE'] >= 3) and (counts['SUPPORTIVE'] - counts['ADVERSE'] >= 2) and (not conflicted) and (adi is not None) and (adi > -threshold), 'improving_positive': level >= D('52.5') and (momentum >= D('47.5') or strong_absolute), 'improving_recovery': 35 <= level < D('52.5') and momentum >= 60 and (sum(recovery.values()) >= 2) and (acc_adi is not None) and (acc_adi > 0), 'stable': 45 <= level <= 55 and D('42.5') <= momentum <= D('57.5') and (n > 0) and (D(counts['NEUTRAL']) / n >= D(policy['predominantly_neutral_fraction'])) and (not conflicted)}
    if mixed:
        return ('MIXED', 'MATERIAL_CONFLICT_PRECEDENCE', predicates)
    for predicate, status in [('deteriorating', 'DETERIORATING'), ('decelerating', 'DECELERATING'), ('accelerating', 'ACCELERATING'), ('improving_positive', 'IMPROVING'), ('improving_recovery', 'IMPROVING'), ('stable', 'STABLE')]:
        if predicates[predicate]:
            return (status, predicate.upper(), predicates)
    return ('MIXED', 'NO_DIRECTIONAL_RULE_MATCH_REVIEW', predicates)

def confidence(parts, vintage_pass, policy, scenario):
    if not parts or not vintage_pass:
        return (None, [])
    settings = policy['confidence']['sensitivity'].get(scenario, policy['confidence'])
    component_rows = []
    for row in parts:
        name = row['component']
        if name == 'point_in_time':
            score = D(settings['point_in_time_credit'])
            reason = 'CURRENT_SNAPSHOT_FILINGS_VERIFIED;RESEARCH_CREDIT_WITH_HISTORICAL_LIMITATION'
        elif name == 'denominator_definition':
            score = D(settings['denominator_definition_credit'])
            reason = 'CANDIDATE_CREDIT;EMPLOYEE_AND_CONDITIONAL_CAPEX_LIMITATIONS_RETAINED'
        else:
            score = D(row['component_score'])
            reason = row['audit_reason']
        weight = D(row['weight'])
        if not 0 <= score <= 100:
            raise ValueError('Confidence component out of bounds')
        component_rows.append({'component': name, 'weight': weight, 'score': score, 'weighted_contribution': weight * score, 'reason': reason})
    if len(component_rows) != 6 or len({r['component'] for r in component_rows}) != 6 or sum((r['weight'] for r in component_rows)) != 1:
        raise ValueError('Incomplete confidence components')
    return (sum((r['weighted_contribution'] for r in component_rows)), component_rows)

def publication_gate(candidate_score, vintage_status, confidence_value, age, minimum_confidence=D(70)):
    if candidate_score is None:
        return (False, 'INSUFFICIENT_HISTORY', 'EXISTING_CANDIDATE_COVERAGE_OR_HISTORY_HOLD')
    if vintage_status != 'PASS_KNOWABLE_AT_MODEL_DATE':
        return (False, 'REVIEW_REQUIRED', 'FILING_VINTAGE_VALIDATION_FAILED')
    if confidence_value is None or confidence_value < minimum_confidence:
        return (False, 'REVIEW_REQUIRED', 'CONFIDENCE_BELOW_RESEARCH_FLOOR')
    if age is None or age > 180:
        return (False, 'STALE', 'PRIMARY_EVIDENCE_TOO_OLD_OR_AGE_UNKNOWN')
    return (True, 'STALE' if age > 120 else 'PARTIAL', 'OPTIONAL_WORKFORCE_AND_CONDITIONAL_SLEEVES_MISSING')

def run(project, output, policy_path=None):
    project, output = (Path(project), Path(output))
    policy_path = Path(policy_path) if policy_path else project / POLICY
    policy = unique_json(policy_path.read_text(encoding='utf-8'))
    if policy['model_date'] != MODEL_DATE or not policy['no_production_approval']:
        raise ValueError('Invalid research policy')
    names = {'review': PREFIX + 'Reviewed_Candidate_Status_Readiness' + SUFFIX + '.csv', 'matrix': PREFIX + 'Operating_Company_Factor_Input_Matrix' + SUFFIX + '.csv', 'inputs': PREFIX + 'Operating_Company_Factor_Input_Detailed_Audit' + SUFFIX + '.csv', 'diagnostics': PREFIX + 'Persistence_Diagnostics' + SUFFIX + '.csv', 'catalog': PREFIX + 'Source_Lineage_Catalog' + SUFFIX + '.csv', 'confidence': PREFIX + 'Confidence_Component_Review' + SUFFIX + '.csv', 'candidates': PREFIX + 'Persistence_Candidate_Scores' + SUFFIX + '.csv', 'manifest': PREFIX + 'Independent_Review_Input_Manifest' + SUFFIX + '.json', 'roster': f'MSFT_IT_Sector_Extraction_Batch_{MODEL_DATE}_R1.csv'}
    names['refresh_exceptions'] = 'Dated_Input_Exceptions.json'
    refresh_exceptions = json.loads((project / names['refresh_exceptions']).read_text())
    verified = set()

    def verify(name):
        if name in verified:
            return
        verified.add(name)
        for dependency, sha in json.loads((project / name).read_text(encoding='utf-8')).items():
            if digest(project / dependency) != sha:
                raise ValueError('Frozen source changed: ' + dependency)
            if dependency.endswith('.json') and 'Manifest' in dependency:
                verify(dependency)
    verify(names['manifest'])
    reviewed = read(project / names['review'])
    matrix = {r['ticker']: r for r in read(project / names['matrix'])}
    roster = {r['ticker']: r for r in read(project / names['roster'])}
    if len(reviewed) != COHORT_SIZE or len(matrix) != COHORT_SIZE or set(matrix) != set(roster) or ({r['ticker'] for r in reviewed} != set(roster)):
        raise ValueError('Frozen cohort mismatch')
    inputs = read(project / names['inputs'])
    candidates = {r['ticker']: r for r in read(project / names['candidates']) if r['scenario'] == 'EQUAL_FAMILIES_40_60'}
    if set(candidates) != set(matrix):
        raise ValueError('Candidate coverage membership mismatch')
    diags = read(project / names['diagnostics'])
    catalog = {(r['source_file'], int(r['source_row'])): r for r in read(project / names['catalog'])}
    vintage_details, vintage_summary = vintage_audit(project, inputs, diags, catalog, matrix)
    vintage = {r['ticker']: r for r in vintage_summary}
    confidence_sources = defaultdict(list)
    for row in read(project / names['confidence']):
        confidence_sources[row['ticker']].append(row)
    ages = defaultdict(list)
    for row in inputs:
        if row['raw_input_eligible'] == 'YES':
            ages[row['ticker']].append(int(row['data_age_days']))
    results, component_audit, status_audit = ([], [], [])
    for scenario in SCENARIOS:
        for reviewed_row in reviewed:
            ticker = reviewed_row['ticker']
            candidate = D(reviewed_row['reviewed_candidate_fastscore']) if reviewed_row['reviewed_candidate_fastscore'] else None
            if reviewed_row['model_date'] != MODEL_DATE:
                raise ValueError('Reviewed model date mismatch')
            family = json.loads(reviewed_row['reviewed_family_classes_json'])
            acceleration, recovery, opposing = acceleration_evidence(matrix[ticker], D(policy['status']['acceleration_neutral_band']))
            v = vintage[ticker]
            confidence_value, parts = confidence(confidence_sources[ticker], v['vintage_status'] == 'PASS_KNOWABLE_AT_MODEL_DATE', policy, scenario)
            age = max(ages[ticker]) if ages[ticker] else None
            publish, data_status, gate_reason = publication_gate(candidate, v['vintage_status'], confidence_value, age, D(policy['confidence']['minimum_publishable_confidence']))
            if roster[ticker].get('peer_eligible') == 'NO':
                publish, data_status, gate_reason = (False, 'EXCLUDED_PEER_GROUP', roster[ticker]['peer_exclusion_reason'])
            if ticker in refresh_exceptions:
                publish, data_status, gate_reason = (False, 'REVIEW_REQUIRED', refresh_exceptions[ticker])
            level = D(reviewed_row['relative_level_index']) if reviewed_row['relative_level_index'] else None
            momentum = D(reviewed_row['relative_momentum_index']) if reviewed_row['relative_momentum_index'] else None
            status, reason, predicates = classify(level, momentum, family, acceleration, recovery, opposing, publish, policy['status'], scenario)
            for part in parts:
                component_audit.append(dict(part, ticker=ticker, scenario=scenario, model_date=MODEL_DATE, decision_id=policy['decision_id']))
            status_audit.append({'scenario': scenario, 'ticker': ticker, 'model_date': MODEL_DATE, 'decision_id': policy['decision_id'], 'family_classes_json': json.dumps(family), 'acceleration_family_classes_json': json.dumps(acceleration), 'recovering_families_json': json.dumps(recovery), 'quarter_ttm_conflicts_json': json.dumps(opposing), 'relative_level_index': level, 'relative_momentum_index': momentum, 'rule_predicates_json': json.dumps(predicates), 'first_matching_rule': reason, 'data_gate_reason': gate_reason, 'provisional_faststatus': status, 'source_review_ticker': ticker, 'source_matrix_ticker': ticker})
            results.append({'scenario': scenario, 'ticker': ticker, 'company_name': roster[ticker]['company_name'], 'cik': matrix[ticker]['cik'], 'model_date': MODEL_DATE, 'as_of_period_end': matrix[ticker]['as_of_period_end'], 'fiscal_quarter': matrix[ticker]['fiscal_quarter'], 'signal_model_available_date': matrix[ticker]['signal_model_available_date'], 'data_age_days': age, 'history_view': policy['history_view'], 'output_label': 'PROVISIONAL_SECTOR_NORMALIZED_RESEARCH_PILOT', 'PROVISIONAL_FAST_SCORE': candidate if publish else None, 'PROVISIONAL_DATA_CONFIDENCE': confidence_value, 'PROVISIONAL_FAST_STATUS': status, 'PROVISIONAL_DATA_STATUS': data_status, 'confidence_scope': 'CURRENT_SNAPSHOT_RESEARCH_CONVENTION;NOT_HISTORICAL_BACKTEST_VALIDATION', 'reviewed_candidate_score_reference': candidate, 'score_published': 'YES' if publish else 'NO', 'gate_reason': gate_reason, 'underlying_candidate_hold_reason': reviewed_row['status_reason'] if candidate is None else '', 'status_reason': reason, 'filing_vintage_status': v['vintage_status'], 'parent_evidence_count': v['parent_evidence_count'], 'relative_level_index': level, 'relative_momentum_index': momentum, 'absolute_direction_index': reviewed_row['absolute_direction_index'], 'original_total_metric_weight_coverage': candidates[ticker]['total_original_weight_coverage'], 'missing_employee_signal': 'YES', 'conditional_capex_unscored': 'YES', 'policy_id': policy['decision_id'], 'raw_sequential_qoq_primary_weight': '0', 'historical_as_filed_backtest_verified': 'NO', 'production_approved': 'NO', 'investability_status_calculated': 'NO'})
    base = {r['ticker']: r for r in results if r['scenario'] == 'BASELINE'}
    sensitivity = []
    for scenario in SCENARIOS:
        rows = [r for r in results if r['scenario'] == scenario]
        changed = [r['ticker'] for r in rows if r['PROVISIONAL_FAST_STATUS'] != base[r['ticker']]['PROVISIONAL_FAST_STATUS']]
        diffs = [abs(r['PROVISIONAL_DATA_CONFIDENCE'] - base[r['ticker']]['PROVISIONAL_DATA_CONFIDENCE']) for r in rows if r['PROVISIONAL_DATA_CONFIDENCE'] is not None]
        sensitivity.append({'scenario': scenario, 'scored_companies': sum((r['score_published'] == 'YES' for r in rows)), 'status_changes': len(changed), 'changed_tickers_json': json.dumps(changed), 'max_confidence_change': max(diffs) if diffs else None, 'status_counts_json': json.dumps(dict(Counter((r['PROVISIONAL_FAST_STATUS'] for r in rows))))})
    output.mkdir(parents=True, exist_ok=True)
    products = {'Research_Pilot_Output': list(base.values()), 'Research_Pilot_Sensitivity_Outputs': results, 'Research_Pilot_Vintage_Parent_Audit': vintage_details, 'Research_Pilot_Vintage_Summary': vintage_summary, 'Research_Pilot_Confidence_Audit': component_audit, 'Research_Pilot_Status_Audit': status_audit, 'Research_Pilot_Sensitivity_Summary': sensitivity}
    for name, rows in products.items():
        write(output / (PREFIX + name + SUFFIX + '.csv'), rows)
    summary = {'model_date': MODEL_DATE, 'policy_id': policy['decision_id'], 'cohort_companies': COHORT_SIZE, 'research_scores_published': sum((r['score_published'] == 'YES' for r in base.values())), 'held_tickers': [r['ticker'] for r in base.values() if r['score_published'] == 'NO'], 'status_counts': dict(Counter((r['PROVISIONAL_FAST_STATUS'] for r in base.values()))), 'data_status_counts': dict(Counter((r['PROVISIONAL_DATA_STATUS'] for r in base.values()))), 'confidence_min': str(min((r['PROVISIONAL_DATA_CONFIDENCE'] for r in base.values() if r['PROVISIONAL_DATA_CONFIDENCE'] is not None))), 'confidence_max': str(max((r['PROVISIONAL_DATA_CONFIDENCE'] for r in base.values() if r['PROVISIONAL_DATA_CONFIDENCE'] is not None))), 'parent_evidence_checks': len(vintage_details), 'parent_evidence_failures': sum((r['vintage_status'] != 'PASS' for r in vintage_details)), 'snapshot_vintage_pass_companies': sum((r['vintage_status'] == 'PASS_KNOWABLE_AT_MODEL_DATE' for r in vintage_summary)), 'parents_different_from_earliest_stored': sum((r['differs_from_earliest_stored_value'] == 'YES' for r in vintage_details)), 'historical_backtest_validated': False, 'production_approved': False, 'products': {PREFIX + k + SUFFIX + '.csv': len(v) for k, v in products.items()}}
    (output / (PREFIX + 'Research_Pilot_Run_Summary' + SUFFIX + '.json')).write_text(json.dumps(summary, indent=2), encoding='utf-8')
    source_names = list(names.values()) + [f'MSFT_IT_SEC_Filing_Index_{MODEL_DATE}_R2.csv']
    source_names += [f'MSFT_IT_Historical_{wave}_Canonical_Selected_Facts_{MODEL_DATE}_R1.csv' for wave in ['Wave1', 'Wave2']]
    source_names += [f'MSFT_IT_Historical_Wave1_Standalone_Quarters_{MODEL_DATE}_R3.csv', f'MSFT_IT_Historical_Wave2_Standalone_Quarters_{MODEL_DATE}_R4.csv', 'sec_filing_index.py', 'Data_Contract.md']
    hashes = {name: digest(project / name) for name in source_names}
    hashes[policy_path.name] = digest(policy_path)
    hashes[Path(__file__).name] = digest(__file__)
    hashes['research_pilot_vintage.py'] = digest(Path(__file__).with_name('research_pilot_vintage.py'))
    (output / (PREFIX + 'Research_Pilot_Input_Manifest' + SUFFIX + '.json')).write_text(json.dumps(hashes, indent=2), encoding='utf-8')
    report(output, summary, policy, sensitivity, list(base.values()))
    return summary

def report(output, summary, policy, sensitivity, rows):
    return None
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--policy', type=Path)
    args = parser.parse_args()
    print(json.dumps(run(args.project, args.output or args.project, args.policy), indent=2))

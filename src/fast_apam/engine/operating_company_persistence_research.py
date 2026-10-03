"""Evaluate a declared persistence research candidate; never production scoring."""
from ..settings import MODEL_DATE, COHORT_SIZE, WAVE_COUNTS
import argparse
import json
from collections import defaultdict
from decimal import Decimal as D
from pathlib import Path
try:
    from .operating_company_factor_scores import MODEL_DATE, PREFIX, SUFFIX, read, write, digest, persistence
except ImportError:
    from operating_company_factor_scores import MODEL_DATE, PREFIX, SUFFIX, read, write, digest, persistence
DECISION_ID = 'FAPAM-PERSISTENCE-RESEARCH-001'
WEIGHTS = {'F1_TTM': D('.35'), 'F2_QUARTER': D('.25'), 'F3_QUALITY': D('.20'), 'F4_ACCELERATION': D('.15'), 'F5_BREADTH': D('.05')}
SCENARIOS = ['EQUAL_FAMILIES_40_60', 'MAPPED_FAMILIES_40_60', 'EQUAL_FAMILIES_50_50', 'STRICT_COMPLETE_HISTORY']

def combine(values, scenario):
    """Original sleeve shares retained; missing data cannot acquire applied weight."""
    if scenario not in SCENARIOS:
        raise ValueError('Unspecified candidate')
    family = [D(1)] * 3 if scenario != 'MAPPED_FAMILIES_40_60' else [D(25), D(30), D(15)]
    cash_split = D('.5') if scenario == 'EQUAL_FAMILIES_50_50' else D('.4')
    shares = dict(zip(['revenue', 'operating_income', 'cash_from_operations', 'free_cash_flow'], [family[0], family[1], family[2] * cash_split, family[2] * (1 - cash_split)]))
    originals = {c: w / sum(family) for c, w in shares.items()}
    passed = values.get('revenue') is not None and values.get('operating_income') is not None
    if scenario == 'STRICT_COMPLETE_HISTORY':
        passed = passed and all((values.get(c) is not None for c in originals))
    available_shares = sum((w for c, w in shares.items() if values.get(c) is not None), D(0)) if passed else D(0)
    coverage = available_shares / sum(family)
    numerator = sum((w * values[c] for c, w in shares.items() if values.get(c) is not None), D(0)) if passed else D(0)
    score = numerator / available_shares if available_shares else None
    return (score, coverage, originals, passed)

def composite(factors, coverage):
    if set(factors) != set(WEIGHTS) or any((v is None for v in factors.values())) or coverage < D('.70'):
        return None
    if any((not D(0) <= v <= D(100) for v in factors.values())):
        raise ValueError('Unbounded factor score')
    return sum((WEIGHTS[k] * v for k, v in factors.items()))

def evaluate(matrix, factors, diagnostics):
    baseline = {(r['ticker'], r['factor_id']): r for r in factors if r['scenario'] == 'BASELINE'}
    if len(baseline) != len(matrix) * 5:
        raise ValueError('Missing or duplicate baseline factor rows')
    diagnostic_map = {(r['ticker'], r['concept']): (i, r) for i, r in enumerate(diagnostics, 2)}
    if len(diagnostic_map) != len(diagnostics):
        raise ValueError('Duplicate persistence diagnostics')
    results, audit = ([], [])
    for company in matrix:
        ticker = company['ticker']
        existing = {f: baseline[ticker, f] for f in WEIGHTS}
        allowed = all((r['company_coverage_gate'] == 'PASS' and r['factor_floor_status'] == 'PASS' and r['factor_score'] for r in existing.values()))
        for r in existing.values():
            if r['model_date'] != MODEL_DATE or r['signal_model_available_date'] > MODEL_DATE or r['raw_sequential_qoq_primary_weight'] != '0':
                raise ValueError('Invalid factor availability or QoQ controls')
        values = {}
        for concept in ['revenue', 'operating_income', 'cash_from_operations', 'free_cash_flow']:
            _, diagnostic = diagnostic_map[ticker, concept]
            if diagnostic['model_date'] != MODEL_DATE:
                raise ValueError('Diagnostic model date mismatch')
            expected, _ = persistence(json.loads(diagnostic['values_json']), D(diagnostic['neutral_band']))
            stored = D(diagnostic['persistence_score']) if diagnostic['persistence_score'] else None
            if stored is not None and (expected != stored or diagnostic['status'] != 'PASS_DIAGNOSTIC_ONLY' or (not json.loads(diagnostic['source_refs_json']))):
                raise ValueError('Persistence source reconciliation failed')
            values[concept] = stored if allowed else None
        for scenario in SCENARIOS:
            score, sleeve_coverage, originals, history_pass = combine(values, scenario)
            publish = allowed and history_pass
            old_f4 = existing['F4_ACCELERATION']
            old_applied = D(old_f4['post_reweighting_coverage'])
            persistence_applied = D('.15') * sleeve_coverage if publish else D(0)
            new_f4_coverage = old_applied + persistence_applied
            if new_f4_coverage > 1 + D('1e-24'):
                raise ValueError('Persistence overfills F4')
            old_f4_score = D(old_f4['factor_score']) if old_f4['factor_score'] else None
            updated_f4 = (old_f4_score * old_applied + score * persistence_applied) / new_f4_coverage if publish else None
            factor_values = {f: D(r['factor_score']) if r['factor_score'] else None for f, r in existing.items()}
            factor_values['F4_ACCELERATION'] = updated_f4
            total_coverage = sum((WEIGHTS[f] * (new_f4_coverage if f == 'F4_ACCELERATION' else D(r['post_reweighting_coverage']) if f == 'F2_QUARTER' else D(r['original_weight_coverage'])) for f, r in existing.items()))
            fastscore = composite(factor_values, total_coverage) if publish else None
            hold = 'EXISTING_COMPANY_HOLD' if not allowed else 'PERSISTENCE_HISTORY_INCOMPLETE' if not history_pass else 'TOTAL_COVERAGE_BELOW_70_PERCENT' if fastscore is None else ''
            results.append({'scenario': scenario, 'ticker': ticker, 'model_date': MODEL_DATE, 'decision_id': DECISION_ID, 'decision_status': 'PROVISIONAL_RESEARCH_CANDIDATE_NOT_PRODUCTION_APPROVED', 'score_label': 'PROVISIONAL_FAST_SCORE', 'candidate_fastscore': fastscore, 'candidate_f4_score': updated_f4, 'old_partial_f4_score': old_f4_score, 'persistence_score': score if publish else None, 'persistence_original_coverage': sleeve_coverage if publish else D(0), 'persistence_applied_f4_weight': persistence_applied, 'f4_evidence_coverage': new_f4_coverage, 'total_original_weight_coverage': total_coverage, 'candidate_status': 'RESEARCH_SCORE_AVAILABLE' if fastscore is not None else 'HOLD', 'hold_reason': hold, 'factor_scores_json': json.dumps({f: str(v) if v is not None else None for f, v in factor_values.items()}), 'as_of_period_end': company['as_of_period_end'], 'signal_model_available_date': company['signal_model_available_date'], 'source_factor_matrix_ticker': ticker, 'raw_sequential_qoq_primary_weight': '0', 'production_score_calculated': 'NO', 'faststatus_calculated': 'NO', 'investability_status_calculated': 'NO'})
            for concept, w in originals.items():
                number, source = diagnostic_map[ticker, concept]
                applied = D('.15') * w if publish and values[concept] is not None else D(0)
                audit.append({'scenario': scenario, 'ticker': ticker, 'concept': concept, 'family': 'CASH' if concept in ['cash_from_operations', 'free_cash_flow'] else 'GROWTH' if concept == 'revenue' else 'PROFIT', 'model_date': MODEL_DATE, 'decision_id': DECISION_ID, 'original_persistence_sleeve_weight': w, 'original_f4_weight': D('.15') * w, 'applied_f4_weight': applied, 'metric_persistence_score': values[concept], 'weighted_f4_numerator': applied * values[concept] if applied else None, 'source_diagnostic_row': number, 'source_refs_json': source['source_refs_json'], 'history_values_json': source['values_json'], 'reason': 'CANDIDATE_ORIGINAL_WEIGHT' if applied else hold or 'MISSING_FOUR_CONSECUTIVE_STANDARD_YOY_VALUES'})
    return (results, audit)

def run(project, output):
    project, output = (Path(project), Path(output))
    names = {'matrix': PREFIX + 'Operating_Company_Factor_Input_Matrix' + SUFFIX + '.csv', 'factors': PREFIX + 'Provisional_Factor_Score_Audit' + SUFFIX + '.csv', 'diagnostics': PREFIX + 'Persistence_Diagnostics' + SUFFIX + '.csv', 'manifest': PREFIX + 'Factor_Aggregation_Input_Manifest' + SUFFIX + '.json', 'spec': 'Fast_APAM_Provisional_Normalization_and_Thresholds.md', 'mapping': 'Operating_Company_Metric_to_Factor_Mapping.md'}
    manifest = json.loads((project / names['manifest']).read_text(encoding='utf-8'))
    for name, sha in manifest.items():
        if digest(project / name) != sha:
            raise ValueError('Frozen aggregation input changed: ' + name)
    matrix, factors, diagnostics = [read(project / names[k]) for k in ['matrix', 'factors', 'diagnostics']]
    if len(matrix) != COHORT_SIZE or len({r['ticker'] for r in matrix}) != COHORT_SIZE:
        raise ValueError('Frozen cohort mismatch')
    results, audit = evaluate(matrix, factors, diagnostics)
    baseline = {r['ticker']: r for r in results if r['scenario'] == 'EQUAL_FAMILIES_40_60'}
    sensitivity = []
    for scenario in SCENARIOS:
        rows = [r for r in results if r['scenario'] == scenario]
        paired = [(r['candidate_fastscore'], baseline[r['ticker']]['candidate_fastscore']) for r in rows if r['candidate_fastscore'] is not None and baseline[r['ticker']]['candidate_fastscore'] is not None]
        delta = [abs(a - b) for a, b in paired]
        sensitivity.append({'scenario': scenario, 'candidate_scores': sum((r['candidate_fastscore'] is not None for r in rows)), 'paired_companies': len(paired), 'max_absolute_composite_change': max(delta) if delta else None, 'mean_absolute_composite_change': sum(delta) / len(delta) if delta else None, 'held_companies_json': json.dumps([r['ticker'] for r in rows if r['candidate_fastscore'] is None])})
    output.mkdir(parents=True, exist_ok=True)
    for kind, rows in [('Persistence_Candidate_Scores', results), ('Persistence_Candidate_Component_Audit', audit), ('Persistence_Candidate_Sensitivity', sensitivity)]:
        write(output / (PREFIX + kind + SUFFIX + '.csv'), rows)
    summary = {'model_date': MODEL_DATE, 'decision_id': DECISION_ID, 'baseline_candidate_scores': sum((r['candidate_fastscore'] is not None for r in baseline.values())), 'existing_hold_count': sum((r['hold_reason'] == 'EXISTING_COMPANY_HOLD' for r in baseline.values())), 'additional_history_holds': [r['ticker'] for r in baseline.values() if r['hold_reason'] == 'PERSISTENCE_HISTORY_INCOMPLETE'], 'scenarios': [{k: str(v) if isinstance(v, D) else v for k, v in s.items()} for s in sensitivity], 'production_approval_recorded': False, 'production_scores_or_statuses_calculated': False}
    (output / (PREFIX + 'Persistence_Candidate_Run_Summary' + SUFFIX + '.json')).write_text(json.dumps(summary, indent=2), encoding='utf-8')
    hashes = {name: digest(project / name) for name in names.values()}
    hashes[Path(__file__).name] = digest(__file__)
    (output / (PREFIX + 'Persistence_Candidate_Input_Manifest' + SUFFIX + '.json')).write_text(json.dumps(hashes, indent=2), encoding='utf-8')
    lines = ['# Persistence aggregation research decision and candidate results', '', f'Decision ID: {DECISION_ID}. Model date: {MODEL_DATE}.', '', '**Status: PROVISIONAL RESEARCH CANDIDATE. No production approval is recorded.** The user authorized research development; the existing Decision Register is unchanged.', '', '## Candidate rule', '', 'Growth, profit and cash each receive one third of the persistence sleeve. CFO and FCF share the cash third at 40/60. This cash split is borrowed from the specified cash-acceleration convention for testing, not represented as an existing persistence rule. Revenue and operating-income persistence require four consecutive standard quarter-YoY observations. A missing cash component retains its original missing weight; there is no redistribution or adverse zero. Both growth and profit histories are required, so two cash expressions cannot substitute for two independent families.', '', 'Per-concept states retain the preceding 1% revenue, 2% profit and 3% cash bands and 10/20/30/40 recency weights. The persistence score averages available original shares. Its applied F4 weight is 15% multiplied by the available original share. Its weighted contribution is added to the existing F4 numerator and denominator; F1–F3 and F5 remain frozen. Acceleration sign never gates eligibility. Raw sequential QoQ retains zero weight.', '', '## Alternatives', '', '- Equal family weights with CFO/FCF 40/60: declared baseline research candidate.', '- Family weights 25/30/15, scaled to sum to one: mirrors the acceleration growth/profit/cash proportions.', '- Equal families with CFO/FCF 50/50: tests sensitivity to the cash blend.', '- Complete history for all four concepts: tests a stricter missingness rule.', '', 'Equal weighting of the four concepts is not used because it would give cash two independent family votes. The choice is not tuned to maximize candidate FastScores or returns. A single-date sensitivity exercise cannot establish predictive validity.', '', '## Composite boundary', '', 'Candidate FastScore = 35% F1 + 25% F2 + 20% F3 + 15% candidate F4 + 5% F5. Outputs are explicitly PROVISIONAL_FAST_SCORE tied to this candidate decision. All five previously validated factor floors, the existing company gate, persistence history and at least 70% original total evidence coverage are required. F2 retains the documented 50/50 fallback for coverage. No weights move across factors. No company ranks, DataConfidence, FastStatus, production FastScore or investability status is calculated.', '', f"Baseline candidate scores: **{summary['baseline_candidate_scores']}**. Existing company holds retained: **{summary['existing_hold_count']}**. Additional history holds: {', '.join(summary['additional_history_holds']) or 'none'}.", '', '| Candidate | Scores | Paired versus baseline | Maximum composite difference |', '|---|---:|---:|---:|']
    lines.extend((f"| {r['scenario']} | {r['candidate_scores']} | {r['paired_companies']} | {r['max_absolute_composite_change']} |" for r in sensitivity))
    lines += ['', '## Audit and reproduction', '', f'The component audit retains original/applied weights, family assignment, source-diagnostic row, observed history and observation references. Source manifests are checked and current inputs are fingerprinted. Existing accounting, normalization and factor artifacts remain unchanged. Tests are recorded in Fast_APAM_Persistence_Candidate_Test_Results_{MODEL_DATE}_R1.json.', '', '```text', f'python run_project_tests.py --report Fast_APAM_Persistence_Candidate_Test_Results_{MODEL_DATE}_R1.json', 'python operating_company_persistence_research.py --project . --output .', '```', '', '## Next stage', '', 'Independently review this concrete research choice and validate it across additional point-in-time dates before promoting a persistence convention. Review frozen family classifications, then implement provisional DataConfidence and FastStatus with explicit conflict precedence. Keep the production methodology approval and historical validation separate from this implementation result.', '']
    None
    return summary
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    print(json.dumps(run(args.project, args.output or args.project), indent=2))

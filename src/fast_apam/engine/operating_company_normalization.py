"""Controlled metric normalization for the dated IT pilot; no composite scoring."""
from __future__ import annotations
from ..settings import MODEL_DATE, COHORT_SIZE, WAVE_COUNTS
import argparse
import json
import math
from collections import Counter, defaultdict
from datetime import date
from decimal import Decimal as D
from pathlib import Path
from statistics import median
try:
    from .operating_company_factor_inputs_v2 import read, write, digest, MODEL_DATE, LABEL
except ImportError:
    from operating_company_factor_inputs_v2 import read, write, digest, MODEL_DATE, LABEL
PREFIX = f'MSFT_IT_Historical_Combined_Pilot_'
SUFFIX = f'_{MODEL_DATE}_R1'
METHODS = {**{a + '_' + b + '_yoy': 'PERCENT_CHANGE' for a, b in [('revenue', 'q'), ('revenue', 'ttm'), ('operating_income', 'q'), ('operating_income', 'ttm'), ('cfo', 'ttm'), ('fcf', 'ttm')]}, **{a + '_' + b + '_yoy_acceleration': 'YOY_RATE_DELTA' for a, b in [('revenue', 'q'), ('revenue', 'ttm'), ('operating_income', 'q'), ('operating_income', 'ttm'), ('cfo', 'ttm'), ('fcf', 'ttm')]}, 'operating_margin_yoy_pp': 'MARGIN_YOY_PP', 'fcf_margin_yoy_pp': 'MARGIN_YOY_PP', 'operating_margin_acceleration_pp': 'MARGIN_YOY_PP_DELTA', 'operating_leverage_spread': 'YOY_RATE_SPREAD'}
SCENARIOS = {'BASELINE': (50, 120, 180, None), 'PEER_MIN_40': (40, 120, 180, None), 'PEER_MIN_60': (60, 120, 180, None), 'AGE_90_150': (50, 90, 150, None), 'AGE_150_210': (50, 150, 210, None), 'WINSOR_2_5_97_5': (50, 120, 180, D('.025')), 'WINSOR_5_95': (50, 120, 180, D('.05'))}

def midranks(values):
    positions = defaultdict(list)
    for index, value in enumerate(sorted(values), 1):
        positions[value].append(index)
    return {v: D(sum(p)) / len(p) for v, p in positions.items()}

def percentile_scores(values):
    ranks = midranks(values)
    return [D(100) * (ranks[v] - D('.5')) / len(values) for v in values]

def quantile(values, probability):
    """Linear interpolation at (N-1)p, explicitly chosen for diagnostic cutoffs."""
    ordered = sorted(values)
    if not ordered:
        raise ValueError('Empty distribution')
    pos = D(len(ordered) - 1) * probability
    lo = int(pos)
    hi = min(lo + 1, len(ordered) - 1)
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (pos - lo)

def robust_scores(values):
    center = median(values)
    mad = median([abs(v - center) for v in values])
    if mad == 0:
        return ([None] * len(values), center, mad)
    scores = []
    for v in values:
        z = max(D(-3), min(D(3), D('.6745') * (v - center) / mad))
        scores.append(D(str(50 * (1 + math.erf(float(z) / math.sqrt(2))))))
    return (scores, center, mad)

def spearman(left, right):
    if len(left) < 2:
        return None
    a, b = (midranks(left), midranks(right))
    x, y = ([a[v] for v in left], [b[v] for v in right])
    xm, ym = (sum(x) / len(x), sum(y) / len(y))
    numerator = sum(((v - xm) * (w - ym) for v, w in zip(x, y)))
    variance = sum(((v - xm) ** 2 for v in x)) * sum(((w - ym) ** 2 for w in y))
    return numerator / variance.sqrt() if variance else None

def eligibility(row, roster, maximum_age):
    if row['input_id'] not in METHODS:
        return 'DIAGNOSTIC_OR_CONDITIONAL_INPUT'
    if row['model_date'] != MODEL_DATE or row['ticker'] not in roster or row['cik'] != roster[row['ticker']]['cik']:
        return 'MODEL_DATE_OR_ROSTER_MISMATCH'
    if row['raw_sequential_qoq_primary_weight'] != '0':
        return 'INVALID_SEQUENTIAL_QOQ_WEIGHT'
    if row['raw_input_eligible'] != 'YES' or row['data_quality_status'] not in ['PASS', 'STALE'] or (not row['value']):
        return 'SOURCE_INPUT_INELIGIBLE'
    available = row['signal_model_available_date']
    if not available or available > MODEL_DATE or (not row['as_of_period_end']) or (row['as_of_period_end'] > MODEL_DATE):
        return 'LOOK_AHEAD_OR_MISSING_PERIOD'
    if not row['source_observation_refs_json'] or not json.loads(row['source_observation_refs_json']):
        return 'MISSING_LINEAGE'
    if any((not f.get('model_available_date') or f['model_available_date'] > MODEL_DATE for f in json.loads(row.get('filing_availability_dates_json', '[]')))):
        return 'LOOK_AHEAD_SOURCE_FILING'
    if row['fallback_status'] != 'STANDARD' or row['transformation'] != METHODS[row['input_id']] or row['normalization_bucket'] != row['transformation']:
        return 'FALLBACK_OR_UNAPPROVED_TRANSFORMATION'
    age = max(int(row['data_age_days']), (date.fromisoformat(MODEL_DATE) - date.fromisoformat(available)).days)
    if age > maximum_age:
        return 'STALE_EXCLUDED'
    if not D(row['value']).is_finite():
        return 'NONFINITE_VALUE'
    return ''

def calculate(rows, roster, approved):
    results, distributions, exceptions = ([], [], [])
    seen = set()
    for number, row in enumerate(rows, 2):
        key = (row['ticker'], row['input_id'])
        if key in seen:
            raise ValueError('Duplicate issuer input')
        seen.add(key)
        row['_input_audit_row'] = number
    if seen != {(t, name) for t in roster for name in {r['input_id'] for r in rows}}:
        raise ValueError('Input audit is not rectangular against frozen roster')
    for scenario, (minimum, current_age, maximum_age, winsor) in SCENARIOS.items():
        groups = defaultdict(list)
        for row in rows:
            reason = eligibility(row, roster, maximum_age)
            if not reason:
                groups[row['input_id']].append(row)
            if scenario == 'BASELINE' and (reason or row['ticker'] not in approved):
                exceptions.append({'ticker': row['ticker'], 'input_id': row['input_id'], 'model_date': MODEL_DATE, 'raw_value': row['value'], 'fallback_status': row['fallback_status'], 'peer_distribution_eligible': 'NO' if reason else 'YES', 'reason': reason or 'COMPANY_COVERAGE_HOLD_SCORE_WITHHELD', 'source_input_audit_row': row['_input_audit_row']})
        for name in sorted(METHODS):
            group = sorted(groups[name], key=lambda r: r['ticker'])
            raw = [D(r['value']) for r in group]
            n = len(group)
            sufficient = n >= minimum
            lo, hi = (quantile(raw, D('.025')), quantile(raw, D('.975'))) if raw else (None, None)
            low_clip, high_clip = (quantile(raw, winsor), quantile(raw, 1 - winsor)) if raw and winsor else (None, None)
            values = [max(low_clip, min(high_clip, v)) for v in raw] if winsor else raw
            ranks = midranks(values)
            percentile = percentile_scores(values) if sufficient else [None] * n
            robust, center, mad = robust_scores(values) if sufficient else ([None] * n, None, None)
            counts = Counter(values)
            distributions.append({'scenario': scenario, 'input_id': name, 'model_date': MODEL_DATE, 'transformation': METHODS[name], 'direction_multiplier': '1', 'peer_level': 'DATED_IT_SECTOR', 'peer_count': n, 'minimum_peers': minimum, 'coverage_status': 'PASS' if sufficient else 'PEER_GROUP_INSUFFICIENT', 'median': center, 'mad': mad, 'raw_p02_5': lo, 'raw_p97_5': hi, 'winsor_lower': low_clip, 'winsor_upper': high_clip, 'robust_z_status': 'PASS' if sufficient and mad else 'MAD_ZERO' if sufficient else 'PEER_GROUP_INSUFFICIENT', 'stale_peer_count': sum((int(r['data_age_days']) > current_age for r in group)), 'distinct_values': len(counts), 'tied_observations': sum((c for c in counts.values() if c > 1)), 'peer_tickers_json': json.dumps([r['ticker'] for r in group]), 'distribution_values_json': json.dumps([str(v) for v in values]), 'distribution_input_rows_json': json.dumps([r['_input_audit_row'] for r in group])})
            for i, row in enumerate(group):
                publish = row['ticker'] in approved and sufficient
                results.append({'scenario': scenario, 'ticker': row['ticker'], 'input_id': name, 'model_date': MODEL_DATE, 'output_label': LABEL, 'score_label': 'PROVISIONAL_METRIC_SCORE', 'raw_value': raw[i], 'aligned_value': raw[i], 'sensitivity_value': values[i], 'direction_multiplier': '1', 'transformation': row['transformation'], 'fallback_status': row['fallback_status'], 'company_coverage_gate': 'PASS' if row['ticker'] in approved else 'HOLD', 'normalization_status': 'PASS' if publish else 'COMPANY_COVERAGE_HOLD' if row['ticker'] not in approved else 'PEER_GROUP_INSUFFICIENT', 'peer_level': 'DATED_IT_SECTOR', 'peer_count': n, 'minimum_peers': minimum, 'midrank': ranks[values[i]] if publish else '', 'tie_count': counts[values[i]], 'empirical_percentile_score': percentile[i] if publish else '', 'robust_z_cdf_score': robust[i] if publish and robust[i] is not None else '', 'robust_z_status': 'PASS' if publish and robust[i] is not None else 'MAD_ZERO' if publish else 'WITHHELD', 'peer_extreme': 'YES' if raw[i] < lo or raw[i] > hi else 'NO', 'data_quality_status': row['data_quality_status'], 'data_age_days': row['data_age_days'], 'scenario_age_class': 'STALE' if int(row['data_age_days']) > current_age else 'CURRENT', 'as_of_period_end': row['as_of_period_end'], 'signal_model_available_date': row['signal_model_available_date'], 'history_view': row['history_view'], 'source_input_audit_row': row['_input_audit_row'], 'source_observation_refs_json': row['source_observation_refs_json'], 'raw_sequential_qoq_primary_weight': '0', 'fastscore_calculated': 'NO'})
    return (results, distributions, exceptions)

def sensitivity(results):
    baseline = {(r['ticker'], r['input_id']): r for r in results if r['scenario'] == 'BASELINE' and r['normalization_status'] == 'PASS'}
    grouped = defaultdict(list)
    for row in results:
        if row['normalization_status'] == 'PASS':
            grouped[row['scenario'], row['input_id']].append(row)
    comparisons = []
    for scenario in SCENARIOS:
        for name in METHODS:
            grouped.setdefault((scenario, name), [])
    for (scenario, name), rows in sorted(grouped.items()):
        for method in ['empirical_percentile_score', 'robust_z_cdf_score']:
            paired = [(baseline[r['ticker'], name]['empirical_percentile_score'], r[method]) for r in rows if (r['ticker'], name) in baseline and r[method] != '']
            left, right = ([x for x, _ in paired], [y for _, y in paired])
            delta = [abs(x - y) for x, y in paired]
            comparisons.append({'scenario': scenario, 'input_id': name, 'method': method, 'reference': 'BASELINE_EMPIRICAL_PERCENTILE', 'paired_observations': len(paired), 'spearman_rank_correlation': spearman(left, right), 'mean_absolute_score_change': sum(delta) / len(delta) if delta else None, 'max_absolute_score_change': max(delta) if delta else None, 'changes_over_10_points': sum((v > 10 for v in delta)), 'baseline_published_count': sum((k[1] == name for k in baseline)), 'scenario_published_count': sum((r[method] != '' for r in rows))})
    return comparisons

def run(project, output):
    project, output = (Path(project), Path(output))
    source_names = {'inputs': PREFIX + 'Operating_Company_Factor_Input_Detailed_Audit' + SUFFIX + '.csv', 'companies': PREFIX + 'Company_Normalization_Coverage_Audit' + SUFFIX + '.csv', 'coverage': PREFIX + 'Normalization_Coverage_Audit' + SUFFIX + '.csv', 'summary': PREFIX + 'Factor_Input_Run_Summary' + SUFFIX + '.json', 'lineage': PREFIX + 'Source_Lineage_Catalog' + SUFFIX + '.csv', 'manifest': PREFIX + 'Input_Manifest' + SUFFIX + '.json', 'roster': f'MSFT_IT_Sector_Extraction_Batch_{MODEL_DATE}_R1.csv', 'spec': 'Fast_APAM_Provisional_Normalization_and_Thresholds.md', 'mapping': 'Operating_Company_Metric_to_Factor_Mapping.md', 'peer_decision': 'Microsoft_Dated_GICS_and_Peer_Hierarchy_Decision.md'}
    prior_manifest = json.loads((project / source_names['manifest']).read_text(encoding='utf-8'))
    for name, sha in prior_manifest.items():
        if digest(project / name) != sha:
            raise ValueError('Frozen factor-input source changed: ' + name)
    summary = json.loads((project / source_names['summary']).read_text(encoding='utf-8'))
    if summary['standard_sector_coverage_gate'] != 'PASS' or summary['model_date'] != MODEL_DATE:
        raise ValueError('Standard cohort coverage must pass before normalization')
    roster_rows = read(project / source_names['roster'])
    roster = {r['ticker']: r for r in roster_rows}
    if len(roster) != COHORT_SIZE or len(roster_rows) != COHORT_SIZE or any((r['model_date'] != MODEL_DATE or r['model_route'] != 'OPERATING_COMPANY' or (r['confirmed_sector'] != 'Information Technology' and r.get('peer_eligible') != 'NO') for r in roster_rows)):
        raise ValueError('Frozen roster mismatch')
    company_rows = read(project / source_names['companies'])
    by_company = defaultdict(list)
    for row in company_rows:
        by_company[row['ticker']].append(row)
    if set(by_company) != set(roster) or any((len(rows) != 5 or len({r['factor_id'] for r in rows}) != 5 for rows in by_company.values())):
        raise ValueError('Invalid company coverage audit')
    approved = {ticker for ticker, rows in by_company.items() if all((r['coverage_gate'] == 'PASS' and r['normalization_coverage_status'] == 'PASS' and (r['model_date'] == MODEL_DATE) for r in rows))}
    if len(approved) != summary['companies_passing_normalization_coverage']:
        raise ValueError('Company gate summary mismatch')
    rows = read(project / source_names['inputs'])
    catalog = {(r['source_file'], int(r['source_row'])) for r in read(project / source_names['lineage'])}
    for row in rows:
        if row['raw_input_eligible'] == 'YES' and (not all((tuple(ref) in catalog for ref in json.loads(row['source_observation_refs_json'])))):
            raise ValueError('Unresolved factor-input lineage')
    results, distributions, exceptions = calculate(rows, roster, approved)
    baseline_counts = {r['input_id']: r['peer_count'] for r in distributions if r['scenario'] == 'BASELINE'}
    if baseline_counts != summary['standard_primary_metric_counts'] or any((n < 50 for n in baseline_counts.values())):
        raise ValueError('Independent normalization coverage disagrees with factor-stage gate')
    comparisons = sensitivity(results)
    baseline = [r for r in results if r['scenario'] == 'BASELINE']
    method_review = sorted([{'ticker': r['ticker'], 'input_id': r['input_id'], 'model_date': MODEL_DATE, 'empirical_percentile_score': r['empirical_percentile_score'], 'robust_z_cdf_score': r['robust_z_cdf_score'], 'absolute_score_difference': abs(r['empirical_percentile_score'] - r['robust_z_cdf_score']), 'peer_extreme': r['peer_extreme'], 'source_input_audit_row': r['source_input_audit_row']} for r in baseline if r['normalization_status'] == 'PASS' and r['robust_z_cdf_score'] != ''], key=lambda r: (-r['absolute_score_difference'], r['ticker'], r['input_id']))
    output.mkdir(parents=True, exist_ok=True)
    products = {'Metric_Normalization': baseline, 'Normalization_Sensitivity_Observations': results, 'Normalization_Peer_Distributions': distributions, 'Normalization_Sensitivity_Summary': comparisons, 'Normalization_Exceptions': exceptions}
    if method_review:
        products['Normalization_Method_Difference_Review'] = method_review
    for kind, data in products.items():
        write(output / (PREFIX + kind + SUFFIX + '.csv'), data)
    report = {'model_date': MODEL_DATE, 'output_label': LABEL, 'cohort_companies': len(roster), 'published_companies': len(approved), 'held_companies': sorted(set(roster) - approved), 'primary_metrics': len(METHODS), 'scenarios': len(SCENARIOS), 'baseline_published_metric_scores': sum((r['normalization_status'] == 'PASS' for r in baseline)), 'baseline_peer_counts': baseline_counts, 'fallback_values_ranked': 0, 'final_scores_calculated': False, 'baseline_mad_zero_metrics': [r['input_id'] for r in distributions if r['scenario'] == 'BASELINE' and r['mad'] == 0], 'sensitivity_coverage_failures': sum((r['coverage_status'] != 'PASS' for r in distributions)), 'products': {PREFIX + k + SUFFIX + '.csv': len(v) for k, v in products.items()}}
    robust_checks = [r for r in comparisons if r['scenario'] == 'BASELINE' and r['method'] == 'robust_z_cdf_score']
    max_difference = max((r['max_absolute_score_change'] for r in robust_checks if r['max_absolute_score_change'] is not None), default=None)
    min_correlation = min((r['spearman_rank_correlation'] for r in robust_checks if r['spearman_rank_correlation'] is not None), default=None)
    report['max_baseline_robust_z_score_difference'] = str(max_difference) if max_difference is not None else None
    report['minimum_baseline_robust_z_spearman'] = str(min_correlation) if min_correlation is not None else None
    report['max_winsorized_percentile_difference'] = str(max((r['max_absolute_score_change'] for r in comparisons if r['scenario'].startswith('WINSOR') and r['method'] == 'empirical_percentile_score' and (r['max_absolute_score_change'] is not None))))
    (output / (PREFIX + 'Normalization_Run_Summary' + SUFFIX + '.json')).write_text(json.dumps(report, indent=2), encoding='utf-8')
    manifest = {name: digest(project / name) for name in source_names.values()}
    manifest[Path(__file__).name] = digest(__file__)
    (output / (PREFIX + 'Normalization_Input_Manifest' + SUFFIX + '.json')).write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    write_report(output, report, comparisons, distributions)
    return report

def write_report(output, summary, comparisons, distributions):
    return None
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    print(json.dumps(run(args.project, args.output or args.project), indent=2))

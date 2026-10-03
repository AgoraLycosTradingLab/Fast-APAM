"""Wave 2 and combined IT pilot input validation. No normalization or scoring.

Uses the frozen observation/quarter artifacts; does not reconstruct completed stages.
Absolute-change observations are never mixed with rate observations.
"""
from __future__ import annotations
from ..settings import MODEL_DATE, COHORT_SIZE, WAVE_COUNTS
import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from datetime import date
from decimal import Decimal as D
from pathlib import Path
try:
    from .operating_company_factor_inputs import _factor_audit, _direction, _combine_directions, _persistence, NEUTRAL
    from .ttm_yoy_construction import _consecutive, _change, _unit_family
except ImportError:
    from operating_company_factor_inputs import _factor_audit, _direction, _combine_directions, _persistence, NEUTRAL
    from ttm_yoy_construction import _consecutive, _change, _unit_family
date.fromisoformat(MODEL_DATE)
FACTORS = ['F1_TTM', 'F2_QUARTER', 'F3_QUALITY', 'F4_ACCELERATION', 'F5_BREADTH']
CONCEPTS = ['revenue', 'operating_income', 'cash_from_operations', 'free_cash_flow', 'capital_expenditures']
ALIASES = dict(zip(CONCEPTS, ['revenue', 'operating_income', 'cfo', 'fcf', 'capex']))
LABEL = 'PROVISIONAL — SECTOR-NORMALIZED PILOT'

def read(path):
    with Path(path).open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))

def write(path, rows):
    if not rows:
        raise ValueError('Refusing an empty artifact: ' + str(path))
    fields = list(dict.fromkeys((k for r in rows for k in r)))
    with Path(path).open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

def js(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'))

def fmt(value):
    return '' if value is None else format(value, 'f')

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

class InvalidInput(ValueError):
    pass

def check_rows(rows, model_date, current=False):
    """Fail closed on lineage, vintage, date, scope/unit, and construction defects."""
    if not rows:
        raise InvalidInput('MISSING_OBSERVATION')
    if len({(r['ticker'], r['cik'], r['history_view'], _unit_family(r['unit_ref'])) for r in rows}) != 1:
        raise InvalidInput('INCOMPATIBLE_ENTITY_VINTAGE_OR_UNIT')
    for row in rows:
        if row['model_date'] != model_date:
            raise InvalidInput('MODEL_DATE_MISMATCH')
        if not row.get('quarter_metric_lineage_json'):
            raise InvalidInput('MISSING_SOURCE_LINEAGE')
        if not row['quarter_source_status'].startswith('PASS_') or row['ttm_rollforward_status'] == 'FAIL':
            raise InvalidInput('PERIOD_INCOMPARABLE_OR_CONSTRUCTION_FAILURE')
        available = row['signal_model_available_date']
        if not available or available > model_date or row['quarter_period_end'] > model_date:
            raise InvalidInput('LOOK_AHEAD_OR_MISSING_AVAILABILITY')
        if available < row['quarter_period_end']:
            raise InvalidInput('AVAILABILITY_PRECEDES_PERIOD_END')
    if current and (date.fromisoformat(model_date) - date.fromisoformat(rows[-1]['signal_model_available_date'])).days > 180:
        raise InvalidInput('STALE_EXCLUDED_OVER_180_DAYS')

def window(series, index, count, model_date):
    rows = series[max(0, index - count + 1):index + 1]
    if len(rows) != count:
        raise InvalidInput('INSUFFICIENT_HISTORY')
    check_rows(rows, model_date)
    if not all((_consecutive(a, b) for a, b in zip(rows, rows[1:]))):
        raise InvalidInput('PERIOD_INCOMPARABLE_NONCONSECUTIVE')
    return rows

def yoy(series, index, basis, model_date):
    rows = window(series, index, 5 if basis == 'quarter' else 8, model_date)
    current, prior = (D(rows[-1]['quarter_value']), D(rows[0]['quarter_value'])) if basis == 'quarter' else (sum((D(r['quarter_value']) for r in rows[-4:])), sum((D(r['quarter_value']) for r in rows[:4])))
    if rows[-1]['fiscal_quarter'] != rows[-5]['fiscal_quarter']:
        raise InvalidInput('PERIOD_INCOMPARABLE_FISCAL_QUARTER')
    rate, absolute, method = _change(current, prior)
    source = rows[-1]
    if method != source[basis + '_yoy_method'] or (rate and D(rate) != D(source[basis + '_yoy_rate'])) or D(absolute) != D(source[basis + '_yoy_absolute_change']):
        raise InvalidInput('SOURCE_YOY_RECONCILIATION_FAILED')
    if basis == 'ttm' and (D(source['ttm_value']) != current or D(source['prior_year_ttm_value']) != prior):
        raise InvalidInput('SOURCE_TTM_RECONCILIATION_FAILED')
    return (D(rate or absolute), method, rows)

def signal(series, index, basis, acceleration, model_date):
    value, method, rows = yoy(series, index, basis, model_date)
    if not acceleration:
        return (value, method, rows)
    previous, previous_method, previous_rows = yoy(series, index - 1, basis, model_date)
    if method == previous_method == 'PERCENT_CHANGE':
        method = 'YOY_RATE_DELTA'
        value -= previous
        field = basis + '_yoy_acceleration'
    else:
        method = 'YOY_ABSOLUTE_CHANGE_DELTA_NONPOSITIVE_BASE'
        value = D(series[index][basis + '_yoy_absolute_change']) - D(series[index - 1][basis + '_yoy_absolute_change'])
        field = basis + '_yoy_acceleration_absolute_change'
    if series[index][basis + '_yoy_acceleration_method'] != method or not series[index][field] or D(series[index][field]) != value:
        raise InvalidInput('ACCELERATION_NOT_VERIFIED_YOY_DELTA')
    return (value, method, previous_rows[:1] + rows)

def margin(numerator, revenue, index, model_date):
    n = window(numerator, index, 8, model_date)
    by_period = {r['quarter_period_end']: r for r in revenue}
    try:
        den = [by_period[r['quarter_period_end']] for r in n]
    except KeyError:
        raise InvalidInput('MISSING_ALIGNED_REVENUE')
    check_rows(n + den, model_date)
    for a, b in zip(n, den):
        if any((a[k] != b[k] for k in ['quarter_period_start', 'quarter_period_end', 'fiscal_quarter'])):
            raise InvalidInput('PERIOD_INCOMPARABLE_MARGIN_COMPONENTS')
    current_den = sum((D(r['quarter_value']) for r in den[-4:]))
    prior_den = sum((D(r['quarter_value']) for r in den[:4]))
    if min(current_den, prior_den) <= 0:
        raise InvalidInput('NONPOSITIVE_REVENUE_DENOMINATOR')
    current = sum((D(r['quarter_value']) for r in n[-4:])) / current_den
    prior = sum((D(r['quarter_value']) for r in n[:4])) / prior_den
    return (current, prior, n + den)

def assemble(observations, controls, model_date, wave):
    grouped = defaultdict(list)
    for row in observations:
        grouped[row['ticker'], row['canonical_concept']].append(row)
    for values in grouped.values():
        values.sort(key=lambda r: r['quarter_period_end'])
        if len({r['quarter_period_end'] for r in values}) != len(values):
            raise ValueError('Duplicate observation period')
    control_map = {(r['ticker'], r['canonical_concept']): r for r in controls}
    issuers = {r['ticker']: r['cik'] for r in controls}
    matrix, detailed, floors = ([], [], [])
    for ticker, cik in sorted(issuers.items()):
        series = {c: grouped[ticker, c] for c in CONCEPTS}
        dated = {c: [r for r in s if r['signal_model_available_date'] and r['signal_model_available_date'] <= model_date and (r['quarter_period_end'] <= model_date)] for c, s in series.items()}
        anchors = dated['revenue'] + dated['operating_income']
        all_dated = [r for s in dated.values() for r in s]
        period = max((r['quarter_period_end'] for r in anchors or all_dated), default='')
        out = {'ticker': ticker, 'cik': cik, 'wave': wave, 'model_date': model_date, 'as_of_period_end': period, 'fiscal_quarter': next((r['fiscal_quarter'] for r in all_dated if r['quarter_period_end'] == period), ''), 'output_label': LABEL, 'raw_sequential_qoq_primary_weight': '0', 'fastscore_calculated': 'NO'}
        inputs = {}

        def add(name, concepts, calculate, factor_ids, diagnostic=False):
            deps, value, method, reason = ([], None, '', '')
            selected = []
            try:
                for concept in concepts:
                    control = control_map.get((ticker, concept), {})
                    if control.get('quarter_governance_status') != 'PASS_NINE_QUARTERS' or control.get('rollforward_failure_count', '0') != '0':
                        raise InvalidInput('SOURCE_GATE:' + control.get('current_signal_status', 'MISSING_CONTROL'))
                    matches = [r for r in dated[concept] if r['quarter_period_end'] == period]
                    if not matches:
                        raise InvalidInput('MISSING_ALIGNED_CURRENT_OBSERVATION')
                    selected.append(matches[-1])
                    check_rows([matches[-1]], model_date, current=True)
                value, method, deps = calculate(selected)
                check_rows(deps, model_date)
            except (InvalidInput, KeyError, IndexError) as error:
                reason = str(error)
                value = None
            age = max(((date.fromisoformat(model_date) - date.fromisoformat(r['signal_model_available_date'])).days for r in selected), default=None)
            fallback = 'NONPOSITIVE_BASE' in method
            eligible = value is not None and (not diagnostic)
            status = ('STALE' if age is not None and age > 120 else 'PASS') if value is not None else 'INELIGIBLE'
            source_refs = sorted({(r.get('_source_file', ''), r.get('_source_row', 0)) for r in deps or selected})
            filing_refs = {js(f): f for r in deps or selected for f in r.get('_source_filings', [])}
            record = {'ticker': ticker, 'cik': cik, 'wave': wave, 'model_date': model_date, 'input_id': name, 'factor_ids': '|'.join(factor_ids), 'value': fmt(value), 'transformation': method, 'fallback_status': 'ABSOLUTE_CHANGE_FALLBACK' if fallback else 'STANDARD' if value is not None else 'UNAVAILABLE', 'data_quality_status': status, 'audit_reason': reason or ('CONDITIONAL_DIAGNOSTIC_ONLY' if diagnostic else 'VALIDATED_SOURCE_AND_PERIODS'), 'raw_input_eligible': 'YES' if eligible else 'NO', 'normalization_bucket': method if eligible else '', 'data_age_days': '' if age is None else age, 'as_of_period_end': period, 'signal_model_available_date': max((r['signal_model_available_date'] for r in deps or selected), default=''), 'history_view': '|'.join(sorted({r['history_view'] for r in deps or selected})), 'period_identity_json': js([{k: r[k] for k in ['canonical_concept', 'fiscal_quarter', 'quarter_period_start', 'quarter_period_end', 'unit_ref']} for r in selected]), 'source_observation_refs_json': js(source_refs), 'filing_availability_dates_json': js(list(filing_refs.values())), 'source_quality_control_json': js([control_map.get((ticker, c), {'canonical_concept': c, 'current_signal_status': 'MISSING_CONTROL'}) for c in concepts]), 'construction_method': method, 'raw_sequential_qoq_primary_weight': '0', 'score_calculated': 'NO'}
            inputs[name] = record
            detailed.append(record)
            out[name] = fmt(value) if not fallback else ''
            out[name + '_absolute_change_fallback'] = fmt(value) if fallback else ''
            out[name + '_status'] = status
            return record
        for concept in CONCEPTS:
            alias = ALIASES[concept]
            for basis in ['quarter', 'ttm']:
                for acceleration in [False, True]:
                    short = 'q' if basis == 'quarter' else 'ttm'
                    name = alias + '_' + short + '_yoy' + ('_acceleration' if acceleration else '')
                    diagnostic = concept == 'capital_expenditures' or (basis == 'quarter' and concept in ['cash_from_operations', 'free_cash_flow'])
                    factors = [] if diagnostic else ['F4_ACCELERATION'] if acceleration else ['F2_QUARTER' if basis == 'quarter' else 'F1_TTM']
                    add(name, [concept], lambda selected, c=concept, b=basis, a=acceleration: signal(series[c], series[c].index(selected[0]), b, a, model_date), factors, diagnostic)
        for concept, prefix in [('operating_income', 'operating_margin'), ('cash_from_operations', 'cfo_margin'), ('free_cash_flow', 'fcf_margin'), ('capital_expenditures', 'capex_intensity')]:

            def get_margin(selected, c=concept):
                return margin(series[c], series['revenue'], series[c].index(selected[0]), model_date)
            for suffix in ['ttm', 'prior_ttm', 'yoy_pp'] + (['acceleration_pp'] if concept == 'operating_income' else []):

                def calc(selected, suffix=suffix, c=concept, helper=get_margin):
                    current, prior, deps = helper(selected)
                    if suffix == 'acceleration_pp':
                        old, old_prior, older_deps = margin(series[c], series['revenue'], series[c].index(selected[0]) - 1, model_date)
                        return (current - prior - (old - old_prior), 'MARGIN_YOY_PP_DELTA', deps + older_deps)
                    return ({'ttm': current, 'prior_ttm': prior, 'yoy_pp': current - prior}[suffix], 'MARGIN_LEVEL' if suffix != 'yoy_pp' else 'MARGIN_YOY_PP', deps)
                primary = suffix == 'acceleration_pp' or (suffix == 'yoy_pp' and concept in ['operating_income', 'free_cash_flow'])
                add(prefix + '_' + suffix, [concept, 'revenue'], calc, ['F4_ACCELERATION' if suffix == 'acceleration_pp' else 'F3_QUALITY'] if primary else [], not primary)

        def leverage(selected):
            p, pm, pd = yoy(series['operating_income'], series['operating_income'].index(selected[0]), 'ttm', model_date)
            r, rm, rd = yoy(series['revenue'], series['revenue'].index(selected[1]), 'ttm', model_date)
            if pm != rm or pm != 'PERCENT_CHANGE':
                raise InvalidInput('INCOMPATIBLE_TRANSFORMATIONS_FOR_SPREAD')
            return (p - r, 'YOY_RATE_SPREAD', pd + rd)
        add('operating_leverage_spread', ['operating_income', 'revenue'], leverage, ['F3_QUALITY'])
        for optional, factors, reason in [('workforce_productivity', ['F1_TTM', 'F3_QUALITY'], 'NO_EMPLOYEE_SIGNAL'), ('gross_profit_q_yoy', ['F2_QUARTER'], 'APPROVED_F2_50_50_FALLBACK'), ('capital_interpretation', ['F3_QUALITY'], 'CONDITIONAL_RULE_NOT_VALIDATED')]:

            def absent(selected, reason=reason):
                raise InvalidInput(reason)
            add(optional, [], absent, factors)

        def present(name):
            return inputs[name]['raw_input_eligible'] == 'YES'

        def direction(name, band):
            r = inputs[name]
            return _direction(D(r['value']), band) if r['value'] and r['fallback_status'] == 'STANDARD' else 'INELIGIBLE'
        families = {'growth': _combine_directions([direction('revenue_ttm_yoy', NEUTRAL['growth']), direction('revenue_q_yoy', NEUTRAL['growth'])]), 'profit': _combine_directions([direction('operating_income_ttm_yoy', NEUTRAL['profit']), direction('operating_margin_yoy_pp', NEUTRAL['margin'])]) if direction('operating_income_ttm_yoy', NEUTRAL['profit']) != 'INELIGIBLE' else 'INELIGIBLE', 'cash': _combine_directions([direction('cfo_ttm_yoy', NEUTRAL['cash']), direction('fcf_ttm_yoy', NEUTRAL['cash'])]), 'margin': _combine_directions([direction('operating_margin_yoy_pp', NEUTRAL['margin']), direction('fcf_margin_yoy_pp', NEUTRAL['margin'])]) if present('operating_margin_yoy_pp') else 'INELIGIBLE', 'productivity': 'INELIGIBLE', 'capital': 'INELIGIBLE'}
        out.update({name + '_family_class': value for name, value in families.items()})
        persistence = {}
        for concept in CONCEPTS[:4]:
            s = series[concept]
            eligible = [i for i, r in enumerate(s) if r['quarter_period_end'] == period and r in dated[concept]]
            values, refs = ([], [])
            if eligible and present(ALIASES[concept] + '_ttm_yoy'):
                for i in range(max(0, eligible[0] - 3), eligible[0] + 1):
                    try:
                        v, method, deps = yoy(s, i, 'quarter', model_date)
                        if method != 'PERCENT_CHANGE':
                            values, refs = ([], [])
                        else:
                            values.append(v)
                            refs.extend(((r.get('_source_file', ''), r.get('_source_row', 0)) for r in deps))
                    except InvalidInput:
                        values, refs = ([], [])
            persistence[concept] = {'values': [fmt(v) for v in values], 'classification': _persistence(values), 'source_refs': sorted(set(refs))}
        persistence_families = sum([len(persistence['revenue']['values']) >= 2, len(persistence['operating_income']['values']) >= 2, max((len(persistence[c]['values']) for c in ['cash_from_operations', 'free_cash_flow'])) >= 2])
        out['persistence_diagnostic_json'] = js(persistence)
        n_acc = sum([any((present(a + '_' + b + '_yoy_acceleration') for b in ['q', 'ttm'])) for a in ['revenue', 'operating_income']]) + int(any((present(a + '_ttm_yoy_acceleration') for a in ['cfo', 'fcf']))) + int(present('operating_margin_acceleration_pp'))
        n_breadth = sum((v != 'INELIGIBLE' for v in families.values()))
        coverage = {'F1_TTM': sum((D(w) for a, w in [('revenue', '.20'), ('operating_income', '.25'), ('cfo', '.15'), ('fcf', '.20')] if present(a + '_ttm_yoy')), D(0)), 'F2_QUARTER': D(1) if present('revenue_q_yoy') and present('operating_income_q_yoy') else D('.45') * (int(present('revenue_q_yoy')) + int(present('operating_income_q_yoy'))), 'F3_QUALITY': sum((D(w) for a, w in [('operating_margin_yoy_pp', '.30'), ('fcf_margin_yoy_pp', '.20'), ('operating_leverage_spread', '.20')] if present(a)), D(0)), 'F4_ACCELERATION': sum((D(w) for a, w in [('revenue', '.25'), ('operating_income', '.30')] if any((present(a + '_' + b + '_yoy_acceleration') for b in ['q', 'ttm']))), D(0)) + D('.15') * sum([any((present(a + '_ttm_yoy_acceleration') for a in ['cfo', 'fcf'])), present('operating_margin_acceleration_pp'), persistence_families >= 2]), 'F5_BREADTH': D(n_breadth) / 6}
        evidence = {'revenue_ttm': present('revenue_ttm_yoy'), 'profit_ttm': present('operating_income_ttm_yoy'), 'cash_ttm': present('cfo_ttm_yoy') or present('fcf_ttm_yoy'), 'revenue_q': present('revenue_q_yoy'), 'profit_q': present('operating_income_q_yoy'), 'operating_margin': present('operating_margin_yoy_pp'), 'quality_confirmation': bool(inputs['fcf_margin_yoy_pp']['value'] or inputs['cfo_margin_yoy_pp']['value']), 'acceleration_family_count': n_acc, 'breadth_family_count': n_breadth}
        factor_rows = _factor_audit(ticker, coverage, evidence)
        for f in factor_rows:
            related = list(inputs.values()) if f['factor_id'] in ['F4_ACCELERATION', 'F5_BREADTH'] else [r for r in inputs.values() if f['factor_id'] in r['factor_ids']]
            f.update(model_date=model_date, wave=wave, audit_reason='RAW_EVIDENCE_FLOOR_ONLY;NORMALIZATION_SEPARATE', input_audit_ids=js([k for k, v in inputs.items() if f['factor_id'] in v['factor_ids']]), persistence_diagnostic_json=out['persistence_diagnostic_json'] if f['factor_id'] == 'F4_ACCELERATION' else '', family_evidence_json=js(families) if f['factor_id'] == 'F5_BREADTH' else '', supporting_input_audit_ids=js([r['input_id'] for r in related]), as_of_period_end=period, signal_model_available_date=max((r['signal_model_available_date'] for r in related if r['value']), default=''), fallback_status='ABSOLUTE_CHANGE_FALLBACK_PRESENT' if any((r['fallback_status'] == 'ABSOLUTE_CHANGE_FALLBACK' for r in related)) else 'NO_FALLBACK', data_quality_status='PASS_RAW_FLOOR' if f['floor_status'] == 'PASS' else 'INSUFFICIENT_RAW_COVERAGE', construction_method='EXISTING_MAPPING_FLOORS_WITH_VALIDATED_INPUTS', raw_sequential_qoq_primary_weight='0')
        floors.extend(factor_rows)
        out.update({f.lower() + '_original_weight_coverage': fmt(v) for f, v in coverage.items()})
        out.update({f'f{i}_original_weight_coverage': fmt(coverage[f]) for i, f in enumerate(FACTORS[:4], 1)})
        out['eligible_breadth_families'] = n_breadth
        out['employee_signal_status'] = 'NO_EMPLOYEE_SIGNAL'
        out['capex_interpretation'] = 'AMBIGUOUS_UNTIL_DETERMINISTIC_RULE_VALIDATED' if inputs['capex_intensity_ttm']['value'] else 'INELIGIBLE'
        out['signal_model_available_date'] = max((r['signal_model_available_date'] for r in inputs.values() if r['value']), default='')
        matrix.append(out)
    return (matrix, detailed, floors)

def normalization_coverage(matrix, inputs, floors, minimum=50):
    """Count like-for-like transforms first; never pool dollars and percentages."""
    buckets = defaultdict(set)
    all_names = sorted({r['input_id'] for r in inputs})
    for r in inputs:
        if r['raw_input_eligible'] == 'YES':
            buckets[r['input_id'], r['normalization_bucket']].add(r['ticker'])
    metric = []
    for name in all_names:
        groups = sorted(((key, tickers) for key, tickers in buckets.items() if key[0] == name))
        for key, tickers in groups or [((name, 'UNAVAILABLE_OR_DIAGNOSTIC'), set())]:
            metric.append({'level': 'METRIC', 'input_id': name, 'transformation': key[1], 'eligible_count': len(tickers), 'cohort_count': len(matrix), 'minimum_count': minimum, 'coverage_status': 'PASS' if len(tickers) >= minimum else 'PEER_GROUP_INSUFFICIENT', 'eligible_tickers': '|'.join(sorted(tickers)), 'peer_level': 'DATED_IT_SECTOR', 'percentiles_calculated': 'NO'})
    by_company = defaultdict(dict)
    for r in inputs:
        by_company[r['ticker']][r['input_id']] = r
    raw_floors = {(r['ticker'], r['factor_id']): r for r in floors}
    company_results = []
    for m in matrix:
        ticker = m['ticker']
        data = by_company[ticker]

        def ok(name):
            r = data[name]
            return r['raw_input_eligible'] == 'YES' and len(buckets[name, r['normalization_bucket']]) >= minimum
        rev, profit = (ok('revenue_ttm_yoy'), ok('operating_income_ttm_yoy'))
        cash = ok('cfo_ttm_yoy') or ok('fcf_ttm_yoy')
        f1 = sum((D(w) for a, w in [('revenue', '.20'), ('operating_income', '.25'), ('cfo', '.15'), ('fcf', '.20')] if ok(a + '_ttm_yoy')), D(0))
        f2 = D(1) if ok('revenue_q_yoy') and ok('operating_income_q_yoy') else D('.45') * (int(ok('revenue_q_yoy')) + int(ok('operating_income_q_yoy')))
        f3 = sum((D(w) for a, w in [('operating_margin_yoy_pp', '.30'), ('fcf_margin_yoy_pp', '.20'), ('operating_leverage_spread', '.20')] if ok(a)), D(0))
        acceleration_groups = [any((ok(a + '_' + b + '_yoy_acceleration') for b in ['q', 'ttm'])) for a in ['revenue', 'operating_income']]
        acceleration_groups += [ok('cfo_ttm_yoy_acceleration') or ok('fcf_ttm_yoy_acceleration'), ok('operating_margin_acceleration_pp')]
        f4 = sum((D(w) * sum((D(bw) * int(ok(a + '_' + b + '_yoy_acceleration')) for b, bw in [('q', '.60'), ('ttm', '.40')])) for a, w in [('revenue', '.25'), ('operating_income', '.30')]), D(0))
        f4 += D('.15') * (D('.40') * int(ok('cfo_ttm_yoy_acceleration')) + D('.60') * int(ok('fcf_ttm_yoy_acceleration'))) + D('.15') * int(ok('operating_margin_acceleration_pp'))
        persistence = json.loads(m['persistence_diagnostic_json'])
        persistence_count = sum([len(persistence[c]['values']) >= 2 for c in ['revenue', 'operating_income']]) + int(any((len(persistence[c]['values']) >= 2 for c in ['cash_from_operations', 'free_cash_flow'])))
        f4 += D('.15') * int(persistence_count >= 2)
        breadth_count = int(m['eligible_breadth_families'])
        coverage = dict(zip(FACTORS, [f1, f2, f3, f4, D(breadth_count) / 6]))
        evidence = {'revenue_ttm': rev, 'profit_ttm': profit, 'cash_ttm': cash, 'revenue_q': ok('revenue_q_yoy'), 'profit_q': ok('operating_income_q_yoy'), 'operating_margin': ok('operating_margin_yoy_pp'), 'quality_confirmation': ok('fcf_margin_yoy_pp') or bool(data['cfo_margin_yoy_pp']['value']), 'acceleration_family_count': sum(acceleration_groups), 'breadth_family_count': breadth_count}
        checked = _factor_audit(ticker, coverage, evidence)
        total = f1 * D('.35') + f2 * D('.25') + f3 * D('.20') + f4 * D('.15') + coverage['F5_BREADTH'] * D('.05')
        for r in checked:
            company_results.append({'ticker': ticker, 'factor_id': r['factor_id'], 'raw_floor_status': raw_floors[ticker, r['factor_id']]['floor_status'], 'normalization_coverage_status': r['floor_status'], 'normalizable_original_weight': r['original_weight_coverage'], 'total_original_weight_coverage': fmt(total), 'total_70pct_floor_status': 'PASS' if total >= D('.70') else 'FAIL', 'coverage_gate': 'PASS' if total >= D('.70') and all((x['floor_status'] == 'PASS' for x in checked)) else 'HOLD', 'model_date': m['model_date'], 'score_calculated': 'NO'})
    for factor in FACTORS:
        count = sum((r['factor_id'] == factor and r['normalization_coverage_status'] == 'PASS' for r in company_results))
        metric.append({'level': 'FACTOR', 'input_id': factor, 'transformation': 'COMPONENT_COVERAGE_ONLY', 'eligible_count': count, 'cohort_count': len(matrix), 'minimum_count': minimum, 'coverage_status': 'PASS' if count >= minimum else 'PEER_GROUP_INSUFFICIENT', 'peer_level': 'DATED_IT_SECTOR', 'percentiles_calculated': 'NO'})
    return (metric, company_results)

def load_wave(root, wave, manifest):
    obs_path = root / f'MSFT_IT_Historical_{wave}_TTM_YoY_Observations_{MODEL_DATE}_R1.csv'
    audit_path = root / f'MSFT_IT_Historical_{wave}_TTM_YoY_Audit_{MODEL_DATE}_R1.csv'
    quarter_path = root / f"MSFT_IT_Historical_{wave}_Standalone_Quarters_{MODEL_DATE}_R{(3 if wave == 'Wave1' else 4)}.csv"
    for path in [obs_path, audit_path, quarter_path]:
        manifest[path.name] = digest(path)
    quarters = defaultdict(list)
    filing_path = root / f'MSFT_IT_SEC_Filing_Index_{MODEL_DATE}_R2.csv'
    filing_index = {r['accession_number']: (number, r) for number, r in enumerate(read(filing_path), 2)}
    for number, r in enumerate(read(quarter_path), 2):
        quarters[r['ticker'], r['canonical_concept'], r['quarter_period_start'], r['quarter_period_end']].append((number, r))
    observations, lineage = (read(obs_path), [])
    for number, r in enumerate(observations, 2):
        r['_source_file'], r['_source_row'] = (obs_path.name, number)
        concepts = ['cash_from_operations', 'capital_expenditures'] if r['canonical_concept'] == 'free_cash_flow' else [r['canonical_concept']]
        sources = []
        source_values = []
        filing_records = {}
        for concept in concepts:
            matches = quarters[r['ticker'], concept, r['quarter_period_start'], r['quarter_period_end']]
            matches = [(n, q) for n, q in matches if q['quarter_status'].startswith('PASS_')]
            if len(matches) != 1:
                raise ValueError(f"Quarter lineage cardinality: {wave} {r['ticker']} {concept} {r['quarter_period_end']}")
            n, q = matches[0]
            if q['latest_parent_model_available_date'] > MODEL_DATE:
                raise ValueError('Future quarter lineage')
            if _unit_family(q['unit_ref']) != _unit_family(r['unit_ref']) or q['fiscal_quarter'] != r['fiscal_quarter']:
                raise ValueError('Source quarter unit or fiscal identity mismatch')
            if q['latest_parent_model_available_date'] > r['signal_model_available_date']:
                raise ValueError('Signal predates source-quarter availability')
            source_values.append(D(q['standalone_value']))
            for parent in json.loads(q['parent_lineage_json']):
                accession = parent['accession_number']
                if accession in filing_index:
                    filing_number, filing = filing_index[accession]
                    if filing['model_available_date'] > MODEL_DATE:
                        raise ValueError('Parent SEC filing unavailable on model date')
                    filing_records[accession] = {'accession_number': accession, 'filed_date': filing['filed_date'], 'accepted_timestamp_utc': filing['accepted_timestamp_utc'], 'model_available_date': filing['model_available_date'], 'filing_index_file': filing_path.name, 'filing_index_row': filing_number}
                else:
                    filing_records[accession] = {'accession_number': accession, 'filing_index_status': 'NOT_IN_SUMMARY_INDEX_USE_QUARTER_LINEAGE', 'model_available_date': q['latest_parent_model_available_date']}
            sources.append({'file': quarter_path.name, 'row': n, 'construction_method': q['construction_method'], 'resolution_id': q['resolution_id'], 'parent_lineage_json': q['parent_lineage_json'], 'latest_parent_model_available_date': q['latest_parent_model_available_date']})
        expected_value = source_values[0] - source_values[1] if len(source_values) == 2 else source_values[0]
        if expected_value != D(r['quarter_value']):
            raise ValueError('Observation does not reconcile to frozen quarter sources')
        r['_source_filings'] = list(filing_records.values())
        lineage.append({'source_file': obs_path.name, 'source_row': number, 'ticker': r['ticker'], 'canonical_concept': r['canonical_concept'], 'quarter_period_start': r['quarter_period_start'], 'quarter_period_end': r['quarter_period_end'], 'history_view': r['history_view'], 'model_date': r['model_date'], 'signal_model_available_date': r['signal_model_available_date'], 'quarter_source_status': r['quarter_source_status'], 'source_quarters_json': js(sources), 'filing_availability_dates_json': js(r['_source_filings'])})
    return (observations, read(audit_path), lineage)

def run(root, output):
    root, output = (Path(root), Path(output))
    output.mkdir(parents=True, exist_ok=True)
    manifest, lineages = ({}, [])
    waves = {}
    for wave, expected in [('Wave2', WAVE_COUNTS['Wave2']), ('Wave1', WAVE_COUNTS['Wave1'])]:
        obs, controls, lineage = load_wave(root, wave, manifest)
        result = assemble(obs, controls, MODEL_DATE, wave)
        if len(result[0]) != expected:
            raise ValueError('Unexpected wave issuer count')
        if wave == 'Wave2':
            if len(controls) != WAVE_COUNTS['Wave2'] * len(CONCEPTS) or len({(r['ticker'], r['canonical_concept']) for r in controls}) != WAVE_COUNTS['Wave2'] * len(CONCEPTS):
                raise ValueError('Expected 315 distinct issuer-metric series')
            if any((r['ttm_rollforward_status'] == 'FAIL' or r['signal_model_available_date'] > MODEL_DATE for r in obs)):
                raise ValueError('Frozen Wave 2 construction or look-ahead violation')
        waves[wave] = result
        lineages.extend(lineage)
    roster_path = root / f'MSFT_IT_Sector_Extraction_Batch_{MODEL_DATE}_R1.csv'
    legacy_path = root / f'MSFT_IT_Historical_Wave1_Operating_Company_Factor_Input_Matrix_{MODEL_DATE}_R1.csv'
    legacy_floor_path = root / f'MSFT_IT_Historical_Wave1_Operating_Company_Factor_Coverage_Audit_{MODEL_DATE}_R1.csv'
    specs = ['Operating_Company_Metric_to_Factor_Mapping.md', 'Fast_APAM_Scoring_and_Status_Specification.md', 'Fast_APAM_Metric_Dictionary.md', 'Fast_APAM_Provisional_Normalization_and_Thresholds.md', 'Microsoft_Dated_GICS_and_Peer_Hierarchy_Decision.md', 'Data_Contract.md', 'Period_Construction_Rules.md', 'Decision_Register.md', 'operating_company_factor_inputs.py', 'ttm_yoy_construction.py', f'MSFT_IT_SEC_Filing_Index_{MODEL_DATE}_R2.csv']
    for path in [roster_path, legacy_path, legacy_floor_path] + [root / name for name in specs]:
        manifest[path.name] = digest(path)
    roster = read(roster_path)
    legacy = {r['ticker']: r for r in read(legacy_path)}
    old_floors = {(r['ticker'], r['factor_id']): r for r in read(legacy_floor_path)}
    wave1, detail1, floor1 = waves['Wave1']
    if set(legacy) != {r['ticker'] for r in wave1}:
        raise ValueError('Wave 1 output membership changed')
    differences = []
    for r in wave1:
        old = legacy[r['ticker']]
        r['wave1_existing_output_json'] = js(old)
        for key, value in old.items():
            if key in r and str(r[key]) != value:
                try:
                    equal = D(value) == D(str(r[key]))
                except Exception:
                    equal = False
                if not equal:
                    differences.append({'ticker': r['ticker'], 'field': key, 'legacy_value': value, 'validated_value': r[key], 'reason': 'ENFORCED_AVAILABILITY_COMPARABILITY_AND_FAMILY_RECONCILIATION'})
            elif key not in r:
                r[key] = value
    matrix = sorted(waves['Wave2'][0] + wave1, key=lambda r: r['ticker'])
    details = waves['Wave2'][1] + detail1
    floors = waves['Wave2'][2] + floor1
    for r in floor1:
        r['legacy_wave1_floor_json'] = js(old_floors[r['ticker'], r['factor_id']])
    if len(matrix) != COHORT_SIZE or len({r['ticker'] for r in matrix}) != COHORT_SIZE or {r['ticker'] for r in matrix} != {r['ticker'] for r in roster}:
        raise ValueError('Combined cohort must equal frozen 74-company roster exactly')
    by_ticker = {r['ticker']: r for r in roster}
    for r in matrix:
        source = by_ticker[r['ticker']]
        if source['cik'] != r['cik'] or source['model_date'] != MODEL_DATE or source['model_route'] != 'OPERATING_COMPANY' or (source['confirmed_sector'] != 'Information Technology' and source.get('peer_eligible') != 'NO'):
            raise ValueError('Roster eligibility mismatch')
        if source.get('peer_eligible') == 'NO' and any((x['ticker'] == r['ticker'] and x['raw_input_eligible'] == 'YES' for x in details)):
            raise ValueError('Excluded sector issuer entered primary inputs')
        r['peer_level'] = 'DATED_IT_SECTOR'
        r['sector_evidence_date'] = source['sector_evidence_date']
    metrics, companies = normalization_coverage(matrix, details, floors)
    products = {}
    for cohort, result in [('Wave2', waves['Wave2']), ('Combined_Pilot', (matrix, details, floors))]:
        for kind, rows in zip(['Factor_Input_Matrix', 'Factor_Input_Detailed_Audit', 'Factor_Coverage_Audit'], result):
            name = f'MSFT_IT_Historical_{cohort}_Operating_Company_{kind}_{MODEL_DATE}_R1.csv'
            write(output / name, rows)
            products[name] = len(rows)
    for kind, rows in [('Normalization_Coverage_Audit', metrics), ('Company_Normalization_Coverage_Audit', companies), ('Source_Lineage_Catalog', lineages)]:
        name = f'MSFT_IT_Historical_Combined_Pilot_{kind}_{MODEL_DATE}_R1.csv'
        write(output / name, rows)
        products[name] = len(rows)
    reconciliation_name = f'MSFT_IT_Historical_Wave1_Factor_Input_Validation_Differences_{MODEL_DATE}_R1.json'
    (output / reconciliation_name).write_text(json.dumps(differences, indent=2), encoding='utf-8')
    required_names = {r['input_id'] for r in details if r['factor_ids'] and r['raw_input_eligible'] == 'YES'}
    standard_checks = [r for r in metrics if r['level'] == 'METRIC' and r['input_id'] in required_names and ('NONPOSITIVE_BASE' not in r['transformation'])]
    factor_checks = [r for r in metrics if r['level'] == 'FACTOR']
    summary = {'model_date': MODEL_DATE, 'output_label': LABEL, 'wave2_companies': WAVE_COUNTS['Wave2'], 'combined_companies': COHORT_SIZE, 'wave2_raw_factor_passes': dict(Counter((r['factor_id'] for r in waves['Wave2'][2] if r['floor_status'] == 'PASS'))), 'combined_raw_factor_passes': dict(Counter((r['factor_id'] for r in floors if r['floor_status'] == 'PASS'))), 'combined_normalization_factor_passes': {r['input_id']: r['eligible_count'] for r in factor_checks}, 'standard_primary_metric_counts': {r['input_id']: r['eligible_count'] for r in standard_checks}, 'fallback_buckets': [{k: r[k] for k in ['input_id', 'eligible_count', 'coverage_status']} for r in metrics if 'NONPOSITIVE_BASE' in r['transformation']], 'companies_passing_normalization_coverage': len({r['ticker'] for r in companies if r['coverage_gate'] == 'PASS'}), 'companies_on_coverage_hold': sorted({r['ticker'] for r in companies if r['coverage_gate'] != 'PASS'}), 'standard_sector_coverage_gate': 'PASS' if all((r['coverage_status'] == 'PASS' for r in standard_checks + factor_checks)) else 'HOLD', 'all_74_company_coverage_gate': 'PASS' if all((r['coverage_gate'] == 'PASS' for r in companies)) else 'HOLD', 'wave2_primary_fallback_inputs': sum((r['raw_input_eligible'] == 'YES' and r['fallback_status'] == 'ABSOLUTE_CHANGE_FALLBACK' for r in waves['Wave2'][1])), 'stale_inputs': sum((r['data_quality_status'] == 'STALE' for r in details)), 'look_ahead_violations_in_eligible_inputs': sum((r['raw_input_eligible'] == 'YES' and r['signal_model_available_date'] > MODEL_DATE for r in details)), 'wave1_changed_fields': len(differences), 'products': products, 'scores_percentiles_ranks_statuses_calculated': False}
    filing_records = [f for row in lineages for f in json.loads(row['filing_availability_dates_json'])]
    summary['source_accessions_absent_from_filing_index'] = sorted({r['accession_number'] for r in filing_records if r.get('filing_index_status')})
    (output / f'MSFT_IT_Historical_Combined_Pilot_Factor_Input_Run_Summary_{MODEL_DATE}_R1.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    (output / f'MSFT_IT_Historical_Combined_Pilot_Input_Manifest_{MODEL_DATE}_R1.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    write_report(output, summary, differences, companies)
    return summary

def write_report(output, summary, differences, companies):
    return None
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    print(json.dumps(run(args.project, args.output or args.project), indent=2))

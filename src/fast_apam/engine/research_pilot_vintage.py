"""Verify the current pilot's selected filing evidence without rewriting history."""
from ..settings import MODEL_DATE, COHORT_SIZE, WAVE_COUNTS
import json
from collections import defaultdict
from decimal import Decimal as D
from pathlib import Path
try:
    from .operating_company_factor_inputs_v2 import read, MODEL_DATE
    from .sec_filing_index import calculate_availability, parse_sec_timestamp
except ImportError:
    from operating_company_factor_inputs_v2 import read, MODEL_DATE
    from sec_filing_index import calculate_availability, parse_sec_timestamp

def filing_check(filing, declared_available, model_date=MODEL_DATE):
    if filing is None:
        return 'MISSING_FILING_INDEX_ENTRY'
    actual = calculate_availability(parse_sec_timestamp(filing['accepted_timestamp_utc'])).model_available_date.isoformat()
    if actual != filing['model_available_date']:
        return 'BUFFER_DATE_MISMATCH'
    if actual > model_date:
        return 'FUTURE_FILING'
    if actual > declared_available:
        return 'SOURCE_AVAILABLE_BEFORE_FILING_BUFFER'
    return 'PASS'

def audit(project, inputs, diagnostics, catalog, tickers):
    project = Path(project)
    index = {r['accession_number']: r for r in read(project / f'MSFT_IT_SEC_Filing_Index_{MODEL_DATE}_R2.csv')}
    selected = defaultdict(list)
    parent_vintages = defaultdict(list)
    for wave in ['Wave1', 'Wave2']:
        path = project / f'MSFT_IT_Historical_{wave}_Canonical_Selected_Facts_{MODEL_DATE}_R1.csv'
        for number, r in enumerate(read(path), 2):
            key = (r['ticker'], r['canonical_concept'], r['period_start'], r['period_end'])
            selected[key + (r['accession_number'],)].append((path.name, number, r))
            if r['model_available_date'] <= MODEL_DATE:
                parent_vintages[key].append(r)
    needed = defaultdict(set)
    for r in inputs:
        if r['raw_input_eligible'] == 'YES':
            needed[r['ticker']].update((tuple(ref) for ref in json.loads(r['source_observation_refs_json'])))
    for r in diagnostics:
        if r['persistence_score']:
            needed[r['ticker']].update((tuple(ref) for ref in json.loads(r['source_refs_json'])))
    quarter_cache = {}
    details = []
    for ticker in sorted(tickers):
        done = set()
        for observation_ref in sorted(needed[ticker]):
            observation = catalog.get(observation_ref)
            if observation is None:
                raise ValueError('Missing observation lineage')
            if observation['signal_model_available_date'] > MODEL_DATE:
                raise ValueError('Future observation dependency')
            for reference in json.loads(observation['source_quarters_json']):
                if reference['file'] not in quarter_cache:
                    quarter_cache[reference['file']] = read(project / reference['file'])
                quarter = quarter_cache[reference['file']][int(reference['row']) - 2]
                for p in json.loads(quarter['parent_lineage_json']):
                    key = (ticker, quarter['canonical_concept'], p['period_start'], p['period_end'])
                    unique = key + (p['accession_number'], p['value'])
                    if unique in done:
                        continue
                    done.add(unique)
                    filing = index.get(p['accession_number'])
                    status = filing_check(filing, quarter['latest_parent_model_available_date'])
                    matches = selected[key + (p['accession_number'],)]
                    exact = [(file, n, r) for file, n, r in matches if D(r['value']) == D(p['value'])]
                    reason = 'CANONICAL_VALUE_MATCH' if exact else 'CANONICAL_PARENT_NOT_MATCHED'
                    if reason == 'CANONICAL_PARENT_NOT_MATCHED':
                        status = reason
                    if filing and filing['ticker'] != ticker:
                        status = 'FILING_ISSUER_MISMATCH'
                    available = filing['model_available_date'] if filing else ''
                    vintages = parent_vintages[key]
                    earliest = min(vintages, key=lambda r: r['model_available_date']) if vintages else None
                    latest = max((r['model_available_date'] for r in vintages), default='')
                    details.append({'ticker': ticker, 'canonical_concept': quarter['canonical_concept'], 'period_start': p['period_start'], 'period_end': p['period_end'], 'accession_number': p['accession_number'], 'parent_value': p['value'], 'model_date': MODEL_DATE, 'accepted_timestamp_utc': filing['accepted_timestamp_utc'] if filing else '', 'recomputed_model_available_date': available, 'quarter_available_date': quarter['latest_parent_model_available_date'], 'vintage_status': status, 'evidence_type': reason, 'resolution_id': quarter['resolution_id'], 'quarter_source_file': reference['file'], 'quarter_source_row': reference['row'], 'canonical_source_file': exact[0][0] if exact else '', 'canonical_source_row': exact[0][1] if exact else '', 'earliest_stored_eligible_value': earliest['value'] if earliest else '', 'differs_from_earliest_stored_value': 'YES' if earliest and D(earliest['value']) != D(p['value']) else 'NO', 'later_eligible_canonical_vintage_exists': 'YES' if latest > available else 'NO', 'vintage_interpretation': 'ELIGIBLE_ON_SNAPSHOT_DATE;NOT_ORIGINAL_FILING_EQUIVALENCE'})
    summary = []
    for ticker in sorted(tickers):
        rows = [r for r in details if r['ticker'] == ticker]
        summary.append({'ticker': ticker, 'model_date': MODEL_DATE, 'parent_evidence_count': len(rows), 'vintage_status': 'PASS_KNOWABLE_AT_MODEL_DATE' if rows and all((r['vintage_status'] == 'PASS' for r in rows)) else 'REVIEW_REQUIRED' if rows else 'NO_SCOREABLE_EVIDENCE', 'failed_parent_count': sum((r['vintage_status'] != 'PASS' for r in rows)), 'parents_different_from_earliest_stored': sum((r['differs_from_earliest_stored_value'] == 'YES' for r in rows)), 'later_vintage_not_used_count': sum((r['later_eligible_canonical_vintage_exists'] == 'YES' for r in rows)), 'historical_as_filed_backtest_verified': 'NO'})
    return (details, summary)

"""Reconcile acquired SEC candidates to inline contexts without approving scores."""
import csv
import json
from collections import defaultdict
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path


AUDIT_FIELDS = ['model_date', 'ticker', 'cik', 'accession_number', 'canonical_concept',
                'taxonomy_concept', 'period_start', 'period_end', 'value', 'status', 'reason',
                'context_ids', 'inline_fact_ids', 'source_url', 'companyfacts_payload_sha256',
                'filing_payload_sha256']
PARENT_FIELDS = ['batch_id', 'model_date', 'ticker', 'cik', 'canonical_concept',
                 'mapping_rule_id', 'taxonomy_concepts', 'value', 'period_start', 'period_end',
                 'duration_days', 'duration_class', 'accession_number', 'form_type',
                 'report_period', 'accepted_timestamp_utc', 'model_available_date',
                 'unit_ref', 'xbrl_decimals', 'rounding_error_bound', 'context_ids',
                 'inline_fact_ids', 'source_documents', 'source_document_roles',
                 'filing_payload_sha256', 'companyfacts_payload_sha256', 'selection_status']


def _rows(path):
    with path.open(newline='', encoding='utf-8-sig') as handle:
        return list(csv.DictReader(handle))


def _write(path, rows, fields):
    with path.open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _decimal(value):
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _duration(days):
    for lower, upper, label in ((70, 110, 'QUARTER'), (150, 210, 'HALF_YEAR_YTD'),
                                (240, 300, 'NINE_MONTH_YTD'), (340, 380, 'FISCAL_YEAR')):
        if lower <= days <= upper:
            return label
    return 'OTHER_DURATION'


def select_facts(preparation_folder):
    folder = Path(preparation_folder)
    manifest = json.loads((folder / 'preparation.json').read_text(encoding='utf-8'))
    context_summary = json.loads((folder / 'inline_context_summary.json').read_text(encoding='utf-8'))
    day = manifest['model_date']
    if context_summary['model_date'] != day or context_summary['ready_to_score']:
        raise ValueError('Inline context summary does not match candidate preparation')
    if (folder / 'canonical_facts.csv').exists() or (folder / 'canonical_fact_audit.csv').exists():
        raise ValueError('Canonical outputs already exist; use a new preparation folder')
    targets = _rows(folder / 'filing_targets.csv')
    target_by_accession = {row['accession_number']: row for row in targets}
    if len(target_by_accession) != len(targets):
        raise ValueError('Duplicate filing target accession')
    extracted = {row['accession_number']: row for row in _rows(folder / 'inline_context_audit.csv')}
    if set(extracted) != set(target_by_accession):
        raise ValueError('Inline audit does not cover exactly the selected filings')
    inline_index = defaultdict(list)
    for row in _rows(folder / 'inline_facts.csv'):
        target = target_by_accession.get(row['accession_number'])
        if target is None or any(row.get(key) != target.get(key) for key in
                                 ('ticker', 'cik', 'model_date', 'model_available_date')):
            raise ValueError('Inline fact does not match a dated filing target')
        if row['model_available_date'] > day or row['filing_payload_sha256'] != extracted[row['accession_number']]['filing_payload_sha256']:
            raise ValueError('Inline fact violates cutoff or source lineage')
        value = _decimal(row['parsed_value'])
        if row['fact_type'] == 'NUMERIC' and value is not None:
            key = (row['ticker'], row['cik'], row['accession_number'],
                   row['taxonomy_concept'].split(':', 1)[-1], row['period_start'],
                   row['period_end'], value)
            inline_index[key].append(row)
    audits, verified = [], defaultdict(list)
    seen = set()
    for candidate in _rows(folder / 'candidate_facts.csv'):
        accession = candidate['accession_number']
        target = target_by_accession.get(accession)
        if target is None:
            continue  # Outside the governed historical filing window.
        if any(candidate.get(key) != target.get(key) for key in
               ('ticker', 'cik', 'model_date', 'model_available_date')):
            raise ValueError('Company Facts candidate does not match a dated filing target')
        if candidate['model_available_date'] > day:
            raise ValueError('Company Facts candidate violates model-date cutoff')
        logical = (candidate['ticker'], accession, candidate['canonical_concept'],
                   candidate['taxonomy_concept'], candidate['period_start'],
                   candidate['period_end'], str(candidate['value']))
        if logical in seen:
            continue
        seen.add(logical)
        audit = {field: '' for field in AUDIT_FIELDS}
        audit.update({key: candidate.get(key, '') for key in AUDIT_FIELDS if key in candidate})
        audit['source_url'] = target['source_url']
        audit['filing_payload_sha256'] = extracted[accession]['filing_payload_sha256']
        value = _decimal(candidate['value'])
        if extracted[accession]['status'] != 'EXTRACTED_CANDIDATE_CONTEXTS':
            audit['status'], audit['reason'] = 'REVIEW_FILING_NOT_EXTRACTED', extracted[accession]['status']
        elif value is None or candidate['unit'] != 'USD' or not candidate['period_start']:
            audit['status'], audit['reason'] = 'REVIEW_INVALID_CANDIDATE', 'VALUE_UNIT_OR_PERIOD'
        else:
            key = (candidate['ticker'], candidate['cik'], accession,
                   candidate['taxonomy_concept'], candidate['period_start'],
                   candidate['period_end'], value)
            matches = inline_index.get(key, [])
            valid = [row for row in matches if row['dimension_count'] == '0' and
                     row['consolidation_scope'] == 'CONSOLIDATED_DEFAULT' and
                     row['period_type'] == 'DURATION' and
                     row['entity_identifier'].zfill(10) == candidate['cik'].zfill(10) and
                     'usd' in row['unit_ref'].lower()]
            contexts = sorted({row['context_id'] for row in valid})
            if len(contexts) != 1:
                audit['status'] = 'REVIEW_MULTIPLE_CONTEXTS' if contexts else 'REVIEW_NO_EXACT_CONTEXT'
                audit['reason'] = 'MULTIPLE_DEFAULT_CONTEXTS' if contexts else 'NO_EXACT_DIMENSIONLESS_USD_CONTEXT'
            else:
                audit['status'] = 'CONTEXT_VERIFIED_CANDIDATE'
                audit['reason'] = 'EXACT_ACCESSION_CONCEPT_PERIOD_VALUE_AND_DEFAULT_CONTEXT'
                audit['context_ids'] = contexts[0]
                audit['inline_fact_ids'] = '|'.join(sorted({r['fact_id'] for r in valid if r['fact_id']}))
                selected = valid[0]
                cell = (candidate['ticker'], candidate['canonical_concept'], accession,
                        candidate['period_start'], candidate['period_end'])
                verified[cell].append((candidate, selected, audit))
        audits.append(audit)
    parents = []
    for cell, choices in sorted(verified.items()):
        priority = min(int(item[0]['mapping_priority']) for item in choices)
        finalists = [item for item in choices if int(item[0]['mapping_priority']) == priority]
        if len({_decimal(item[0]['value']) for item in finalists}) != 1:
            for _, _, audit in finalists:
                audit['status'], audit['reason'] = 'REVIEW_SAME_PRIORITY_CONFLICT', 'DIFFERENT_VALUES'
            continue
        candidate, inline, audit = finalists[0]
        for _, _, superseded in choices:
            if superseded is not audit:
                superseded['status'], superseded['reason'] = 'SUPERSEDED_MAPPING_PRIORITY', 'LOWER_PRIORITY_CONCEPT'
        target = target_by_accession[candidate['accession_number']]
        days = (date.fromisoformat(candidate['period_end']) - date.fromisoformat(candidate['period_start'])).days + 1
        if days <= 0 or _duration(days) == 'OTHER_DURATION':
            audit['status'], audit['reason'] = 'REVIEW_INCOMPARABLE_PERIOD', 'UNSUPPORTED_DURATION'
            continue
        decimals = inline.get('decimals', '')
        bound = (Decimal(10) ** -int(decimals) / 2) if decimals.lstrip('-').isdigit() else Decimal(0)
        parents.append({'batch_id': candidate['batch_id'], 'model_date': day,
                        'ticker': candidate['ticker'], 'cik': candidate['cik'],
                        'canonical_concept': candidate['canonical_concept'],
                        'mapping_rule_id': 'STANDARD-' + candidate['canonical_concept'].upper() + '-V0.1',
                        'taxonomy_concepts': 'us-gaap:' + candidate['taxonomy_concept'],
                        'value': str(candidate['value']), 'period_start': candidate['period_start'],
                        'period_end': candidate['period_end'], 'duration_days': str(days),
                        'duration_class': _duration(days), 'accession_number': candidate['accession_number'],
                        'form_type': target['form_type'], 'report_period': target['report_period'],
                        'accepted_timestamp_utc': target['accepted_timestamp_utc'],
                        'model_available_date': target['model_available_date'], 'unit_ref': inline['unit_ref'],
                        'xbrl_decimals': decimals, 'rounding_error_bound': str(bound),
                        'context_ids': audit['context_ids'], 'inline_fact_ids': audit['inline_fact_ids'],
                        'source_documents': target['primary_document'], 'source_document_roles': 'PRIMARY_DOCUMENT',
                        'filing_payload_sha256': audit['filing_payload_sha256'],
                        'companyfacts_payload_sha256': audit['companyfacts_payload_sha256'],
                        'selection_status': 'SELECTED_CONTEXT_VERIFIED_CANDIDATE'})
    _write(folder / 'canonical_facts.csv', parents, PARENT_FIELDS)
    _write(folder / 'canonical_fact_audit.csv', audits, AUDIT_FIELDS)
    result = {'model_date': day, 'candidate_count': len(audits), 'canonical_fact_count': len(parents),
              'review_count': sum(row['status'].startswith('REVIEW_') for row in audits),
              'ready_to_score': False}
    (folder / 'canonical_fact_summary.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    return result

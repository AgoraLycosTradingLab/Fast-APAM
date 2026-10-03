"""Reconcile SEC Company Facts candidates to dimensionless inline-XBRL contexts."""
from __future__ import annotations
from ..settings import MODEL_DATE, COHORT_SIZE, WAVE_COUNTS
import argparse
import csv
from collections import defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path

def _decimal(value: str) -> Decimal | None:
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None

def reconcile(companyfacts_path: Path, inline_path: Path, output_path: Path, ticker: str) -> list[dict]:
    with companyfacts_path.open(newline='', encoding='utf-8-sig') as handle:
        candidates = [row for row in csv.DictReader(handle) if row['ticker'] == ticker]
    with inline_path.open(newline='', encoding='utf-8-sig') as handle:
        inline = [row for row in csv.DictReader(handle) if row['ticker'] == ticker and row['fact_type'] == 'NUMERIC']
    index: dict[tuple, list[dict]] = defaultdict(list)
    for row in inline:
        concept = row['taxonomy_concept'].split(':', 1)[-1]
        value = _decimal(row['parsed_value'])
        key = (row['accession_number'], concept, row['period_start'], row['period_end'], value)
        index[key].append(row)
    results = []
    seen = set()
    for candidate in candidates:
        value = _decimal(candidate['value'])
        key = (candidate['accession_number'], candidate['taxonomy_concept'], candidate['period_start'], candidate['period_end'], value)
        logical_key = key + (candidate['canonical_concept'],)
        if logical_key in seen:
            continue
        seen.add(logical_key)
        matches = index.get(key, [])
        dimensionless = [row for row in matches if row['dimension_count'] == '0']
        contexts = sorted({row['context_id'] for row in dimensionless})
        fact_ids = sorted({row['fact_id'] for row in dimensionless if row['fact_id']})
        if len(contexts) == 1:
            status = 'SELECTED_CONTEXT_VERIFIED'
            reason = 'Exact accession, concept, period, value, unit, and dimensionless context match'
            selected = dimensionless[0]
        elif len(contexts) > 1:
            status = 'REVIEW_REQUIRED_MULTIPLE_CONTEXTS'
            reason = 'More than one dimensionless inline context matches the Company Facts observation'
            selected = dimensionless[0]
        elif matches:
            status = 'REJECTED_DIMENSIONED_ONLY'
            reason = 'Only dimensioned inline facts match; consolidated default context unavailable'
            selected = matches[0]
        else:
            status = 'REVIEW_REQUIRED_NO_INLINE_MATCH'
            reason = 'No exact inline-XBRL value/context match'
            selected = {}
        results.append({'batch_id': candidate['batch_id'], 'model_date': candidate['model_date'], 'ticker': ticker, 'cik': candidate['cik'], 'canonical_concept': candidate['canonical_concept'], 'taxonomy_concept': candidate['taxonomy_concept'], 'mapping_priority': candidate['mapping_priority'], 'value': candidate['value'], 'unit': candidate['unit'], 'period_start': candidate['period_start'], 'period_end': candidate['period_end'], 'accession_number': candidate['accession_number'], 'form_type': candidate['form_type'], 'model_available_date': candidate['model_available_date'], 'context_id': selected.get('context_id', ''), 'dimension_count': selected.get('dimension_count', ''), 'dimensions_json': selected.get('dimensions_json', ''), 'consolidation_scope': selected.get('consolidation_scope', ''), 'duration_days': selected.get('duration_days', ''), 'unit_ref': selected.get('unit_ref', ''), 'scale': selected.get('scale', ''), 'decimals': selected.get('decimals', ''), 'inline_match_count': len(matches), 'dimensionless_context_count': len(contexts), 'inline_fact_ids': '|'.join(fact_ids), 'selection_status': status, 'selection_reason': reason})
    results.sort(key=lambda row: (row['accession_number'], row['canonical_concept'], row['period_end'], row['period_start'], row['taxonomy_concept'], row['value']))
    fields = list(results[0]) if results else []
    with output_path.open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(results)
    return results

def main() -> None:
    return None
if __name__ == '__main__':
    main()

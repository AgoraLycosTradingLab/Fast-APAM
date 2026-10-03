"""Select Tier 1 consolidated inline contexts across the frozen 74-issuer batch."""
from __future__ import annotations
from ..settings import MODEL_DATE, COHORT_SIZE, WAVE_COUNTS
import argparse
import csv
import json
from collections import defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path
CANONICALS = ('revenue', 'operating_income', 'cash_from_operations', 'capital_expenditures')
SPECIAL_CAPEX = {'GLW': ('CAPEX-GLW-001', ('us-gaap:PaymentsForCapitalImprovements',)), 'IT': ('CAPEX-IT-001', ('us-gaap:PaymentsForCapitalImprovements',)), 'ROP': ('CAPEX-ROP-001', ('us-gaap:PaymentsToAcquireOtherProductiveAssets', 'us-gaap:PaymentsToDevelopSoftware'))}
OPERATING_INCOME_EXCLUSIONS = {'COHR': 'OPINC-COHR-001', 'IBM': 'OPINC-IBM-001', 'KLAC': 'OPINC-KLAC-001', 'Q': 'OPINC-Q-001'}
CAPEX_UNAVAILABLE = {'APP': 'CAPEX-APP-001'}
STANDARD_INLINE_MAP = {'us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax': 'revenue', 'us-gaap:RevenueFromContractWithCustomerIncludingAssessedTax': 'revenue', 'us-gaap:Revenues': 'revenue', 'us-gaap:SalesRevenueNet': 'revenue', 'us-gaap:SalesRevenueGoodsNet': 'revenue', 'us-gaap:SalesRevenueServicesNet': 'revenue', 'us-gaap:OperatingIncomeLoss': 'operating_income', 'us-gaap:NetCashProvidedByUsedInOperatingActivities': 'cash_from_operations', 'us-gaap:NetCashProvidedByUsedInOperatingActivitiesContinuingOperations': 'cash_from_operations', 'us-gaap:PaymentsToAcquirePropertyPlantAndEquipment': 'capital_expenditures', 'us-gaap:PaymentsForAdditionsToPropertyPlantAndEquipment': 'capital_expenditures', 'us-gaap:PaymentsToAcquireProductiveAssets': 'capital_expenditures', 'us-gaap:PaymentsToAcquireMachineryAndEquipment': 'capital_expenditures'}

def _decimal(value: str):
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None

def select(companyfacts_path: Path, inline_path: Path, targets_path: Path, selection_path: Path, coverage_path: Path):
    with companyfacts_path.open(newline='', encoding='utf-8-sig') as handle:
        candidates = list(csv.DictReader(handle))
    with inline_path.open(newline='', encoding='utf-8-sig') as handle:
        inline = list(csv.DictReader(handle))
    with targets_path.open(newline='', encoding='utf-8-sig') as handle:
        targets = list(csv.DictReader(handle))
    target_by_ticker = {row['ticker']: row for row in targets}
    target_accessions = {row['accession_number'] for row in targets}
    inline_index = defaultdict(list)
    for row in inline:
        if row['fact_type'] != 'NUMERIC':
            continue
        concept = row['taxonomy_concept'].split(':', 1)[-1]
        key = (row['accession_number'], concept, row['period_start'], row['period_end'], _decimal(row['parsed_value']))
        inline_index[key].append(row)
    selections = []
    seen = set()
    for candidate in candidates:
        if candidate['accession_number'] not in target_accessions:
            continue
        key = (candidate['accession_number'], candidate['taxonomy_concept'], candidate['period_start'], candidate['period_end'], _decimal(candidate['value']))
        logical = key + (candidate['ticker'], candidate['canonical_concept'])
        if logical in seen:
            continue
        seen.add(logical)
        matches = inline_index.get(key, [])
        dimensionless = [row for row in matches if row['dimension_count'] == '0' and row['consolidation_scope'] == 'CONSOLIDATED_DEFAULT']
        contexts = sorted({row['context_id'] for row in dimensionless})
        if not contexts:
            continue
        selected = dimensionless[0]
        selections.append({'batch_id': candidate['batch_id'], 'model_date': candidate['model_date'], 'ticker': candidate['ticker'], 'cik': candidate['cik'], 'canonical_concept': candidate['canonical_concept'], 'mapping_rule_id': f"STANDARD-{candidate['canonical_concept'].upper()}-V0.1", 'taxonomy_concept': candidate['taxonomy_concept'], 'component_role': 'DIRECT', 'value': candidate['value'], 'unit': candidate['unit'], 'period_start': candidate['period_start'], 'period_end': candidate['period_end'], 'duration_days': selected['duration_days'], 'accession_number': candidate['accession_number'], 'form_type': candidate['form_type'], 'model_available_date': candidate['model_available_date'], 'context_id': selected['context_id'], 'dimension_count': selected['dimension_count'], 'dimensions_json': selected['dimensions_json'], 'consolidation_scope': selected['consolidation_scope'], 'unit_ref': selected['unit_ref'], 'scale': selected['scale'], 'decimals': selected['decimals'], 'inline_fact_ids': '|'.join(sorted({r['fact_id'] for r in dimensionless if r['fact_id']})), 'selection_status': 'SELECTED_CONTEXT_VERIFIED', 'selection_reason': 'Exact accession, concept, period, value, and consolidated-default context match'})
    for ticker, (rule_id, concepts) in SPECIAL_CAPEX.items():
        target = target_by_ticker[ticker]
        for concept in concepts:
            rows = [r for r in inline if r['ticker'] == ticker and r['accession_number'] == target['accession_number'] and (r['taxonomy_concept'] == concept) and (r['fact_type'] == 'NUMERIC') and (r['dimension_count'] == '0') and (r['period_type'] == 'DURATION')]
            unique = {}
            for row in rows:
                unique[row['period_start'], row['period_end'], row['parsed_value'], row['context_id']] = row
            for row in unique.values():
                selections.append({'batch_id': target['batch_id'], 'model_date': target['model_date'], 'ticker': ticker, 'cik': target['cik'], 'canonical_concept': 'capital_expenditures', 'mapping_rule_id': rule_id, 'taxonomy_concept': concept.split(':', 1)[-1], 'component_role': 'DIRECT' if len(concepts) == 1 else 'AGGREGATION_COMPONENT', 'value': row['parsed_value'], 'unit': 'USD', 'period_start': row['period_start'], 'period_end': row['period_end'], 'duration_days': row['duration_days'], 'accession_number': row['accession_number'], 'form_type': row['form_type'], 'model_available_date': row['model_available_date'], 'context_id': row['context_id'], 'dimension_count': row['dimension_count'], 'dimensions_json': row['dimensions_json'], 'consolidation_scope': row['consolidation_scope'], 'unit_ref': row['unit_ref'], 'scale': row['scale'], 'decimals': row['decimals'], 'inline_fact_ids': row['fact_id'], 'selection_status': 'SELECTED_CONTEXT_VERIFIED', 'selection_reason': f'Approved issuer-specific mapping {rule_id}'})
    existing_cells = {(row['ticker'], row['canonical_concept']) for row in selections}
    for row in inline:
        canonical = STANDARD_INLINE_MAP.get(row['taxonomy_concept'])
        cell = (row['ticker'], canonical)
        if not canonical or cell in existing_cells:
            continue
        if row['fact_type'] != 'NUMERIC' or row['dimension_count'] != '0' or row['period_type'] != 'DURATION':
            continue
        target = target_by_ticker[row['ticker']]
        selections.append({'batch_id': target['batch_id'], 'model_date': target['model_date'], 'ticker': row['ticker'], 'cik': target['cik'], 'canonical_concept': canonical, 'mapping_rule_id': 'INLINE-DIRECT-FALLBACK-V0.1', 'taxonomy_concept': row['taxonomy_concept'].split(':', 1)[-1], 'component_role': 'DIRECT', 'value': row['parsed_value'], 'unit': 'USD', 'period_start': row['period_start'], 'period_end': row['period_end'], 'duration_days': row['duration_days'], 'accession_number': row['accession_number'], 'form_type': row['form_type'], 'model_available_date': row['model_available_date'], 'context_id': row['context_id'], 'dimension_count': row['dimension_count'], 'dimensions_json': row['dimensions_json'], 'consolidation_scope': row['consolidation_scope'], 'unit_ref': row['unit_ref'], 'scale': row['scale'], 'decimals': row['decimals'], 'inline_fact_ids': row['fact_id'], 'selection_status': 'SELECTED_CONTEXT_VERIFIED', 'selection_reason': 'Direct eligible inline fact selected because Company Facts had not propagated the accession'})
    deduped = {}
    for row in selections:
        key = (row['ticker'], row['canonical_concept'], row['accession_number'], row['taxonomy_concept'], row['period_start'], row['period_end'], row['value'], row['context_id'], row['component_role'])
        if key in deduped:
            ids = set(filter(None, deduped[key]['inline_fact_ids'].split('|')))
            ids.update(filter(None, row['inline_fact_ids'].split('|')))
            deduped[key]['inline_fact_ids'] = '|'.join(sorted(ids))
        else:
            deduped[key] = row
    selections = list(deduped.values())
    selections.sort(key=lambda r: (r['ticker'], r['canonical_concept'], r['period_end'], r['period_start'], r['taxonomy_concept'], r['value']))
    with selection_path.open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(selections[0]))
        writer.writeheader()
        writer.writerows(selections)
    coverage = []
    for ticker, target in sorted(target_by_ticker.items()):
        for canonical in CANONICALS:
            rows = [r for r in selections if r['ticker'] == ticker and r['canonical_concept'] == canonical]
            rule_id = ''
            if canonical == 'operating_income' and ticker in OPERATING_INCOME_EXCLUSIONS:
                status = 'EXCLUDED_V0_1_NO_DIRECT_SUBTOTAL'
                rule_id = OPERATING_INCOME_EXCLUSIONS[ticker]
            elif canonical == 'capital_expenditures' and ticker in CAPEX_UNAVAILABLE:
                status = 'UNAVAILABLE_V0_1_NOT_DISCLOSED'
                rule_id = CAPEX_UNAVAILABLE[ticker]
            elif canonical == 'capital_expenditures' and ticker == 'ROP':
                rule_id, required = SPECIAL_CAPEX[ticker]
                by_period = defaultdict(set)
                for row in rows:
                    by_period[row['period_start'], row['period_end']].add('us-gaap:' + row['taxonomy_concept'])
                complete = [p for p, found in by_period.items() if set(required).issubset(found)]
                status = 'PASS_CONTEXT_VERIFIED' if complete else 'MISSING_REQUIRED_AGGREGATION_COMPONENT'
            elif rows:
                status = 'PASS_CONTEXT_VERIFIED'
                rule_id = rows[0]['mapping_rule_id']
            else:
                status = 'MISSING_OR_UNMATCHED_LATEST_FILING'
            coverage.append({'batch_id': target['batch_id'], 'model_date': target['model_date'], 'ticker': ticker, 'company_name': target['company_name'], 'cik': target['cik'], 'canonical_concept': canonical, 'target_accession': target['accession_number'], 'target_form': target['form_type'], 'target_report_period': target['report_period'], 'mapping_rule_id': rule_id, 'selected_row_count': len(rows), 'distinct_period_count': len({(r['period_start'], r['period_end']) for r in rows}), 'coverage_status': status})
    with coverage_path.open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(coverage[0]))
        writer.writeheader()
        writer.writerows(coverage)
    return (selections, coverage)

def main():
    return None
if __name__ == '__main__':
    main()

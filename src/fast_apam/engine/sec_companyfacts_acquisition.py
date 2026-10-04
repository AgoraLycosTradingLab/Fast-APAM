"""Acquire Tier 1 Fast APAM candidate facts from SEC Company Facts.

The output is an accession-linked candidate layer. Company Facts does not expose
the complete inline-XBRL context/dimension payload, so every retained observation
is explicitly flagged for later inline-context verification before construction.
"""
from __future__ import annotations
import argparse
import csv
import gzip
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
SEC_COMPANYFACTS_URL = 'https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json'
ALLOWED_UNITS = {'USD'}
CONCEPT_MAP: dict[str, tuple[str, ...]] = {'revenue': ('RevenueFromContractWithCustomerExcludingAssessedTax', 'RevenueFromContractWithCustomerIncludingAssessedTax', 'Revenues', 'SalesRevenueNet', 'SalesRevenueGoodsNet', 'SalesRevenueServicesNet'), 'operating_income': ('OperatingIncomeLoss',), 'cash_from_operations': ('NetCashProvidedByUsedInOperatingActivities', 'NetCashProvidedByUsedInOperatingActivitiesContinuingOperations'), 'capital_expenditures': ('PaymentsToAcquirePropertyPlantAndEquipment', 'PaymentsForAdditionsToPropertyPlantAndEquipment', 'PaymentsToAcquireProductiveAssets', 'PaymentsToAcquireMachineryAndEquipment')}

def _http_bytes(url: str, user_agent: str, retries: int=4) -> bytes:
    headers = {'User-Agent': user_agent, 'Accept': 'application/json', 'Accept-Encoding': 'gzip'}
    for attempt in range(retries):
        try:
            with urlopen(Request(url, headers=headers), timeout=60) as response:
                payload = response.read()
                if response.headers.get('Content-Encoding') == 'gzip' or payload[:2] == b'\x1f\x8b':
                    payload = gzip.decompress(payload)
                return payload
        except (HTTPError, URLError, TimeoutError) as exc:
            if attempt == retries - 1:
                raise RuntimeError(f'SEC request failed after {retries} attempts: {url}') from exc
            time.sleep(2 ** attempt)
    raise AssertionError('unreachable')

def _load_eligible_filings(path: Path) -> tuple[list[dict], dict[str, dict]]:
    with path.open(newline='', encoding='utf-8-sig') as handle:
        all_rows = list(csv.DictReader(handle))
    eligible = [row for row in all_rows if row['eligible_on_model_date'] == 'Y']
    by_accession = {row['accession_number']: row for row in eligible}
    if len(by_accession) != len(eligible):
        raise ValueError('Eligible filing index contains duplicate accession numbers')
    return (eligible, by_accession)

def _candidate_facts(companyfacts: dict, filing_by_accession: dict[str, dict]) -> Iterable[dict]:
    facts = companyfacts.get('facts', {})
    for taxonomy, taxonomy_facts in facts.items():
        if taxonomy != 'us-gaap':
            continue
        for canonical, aliases in CONCEPT_MAP.items():
            for priority, concept in enumerate(aliases, start=1):
                concept_block = taxonomy_facts.get(concept)
                if not concept_block:
                    continue
                for unit, observations in concept_block.get('units', {}).items():
                    if unit not in ALLOWED_UNITS:
                        continue
                    for observation in observations:
                        accession = observation.get('accn', '')
                        filing = filing_by_accession.get(accession)
                        if not filing:
                            continue
                        yield {'batch_id': filing['batch_id'], 'snapshot_id': filing['snapshot_id'], 'model_date': filing['model_date'], 'ticker': filing['ticker'], 'company_name': filing['company_name'], 'cik': filing['cik'], 'target_flag': filing['target_flag'], 'canonical_concept': canonical, 'mapping_priority': priority, 'taxonomy': taxonomy, 'taxonomy_concept': concept, 'taxonomy_label': concept_block.get('label', ''), 'taxonomy_description': concept_block.get('description', ''), 'value': observation.get('val', ''), 'unit': unit, 'period_start': observation.get('start', ''), 'period_end': observation.get('end', ''), 'fiscal_year_tag': observation.get('fy', ''), 'fiscal_period_tag': observation.get('fp', ''), 'sec_frame': observation.get('frame', ''), 'accession_number': accession, 'form_type': observation.get('form', filing['form_type']), 'filed_date': observation.get('filed', filing['filed_date']), 'report_period': filing['report_period'], 'accepted_timestamp_utc': filing['accepted_timestamp_utc'], 'model_available_date': filing['model_available_date'], 'filing_source_url': filing['source_url'], 'source_type': 'SEC_COMPANYFACTS', 'source_view': 'AS_FILED', 'context_dimensions_status': 'UNAVAILABLE_IN_COMPANYFACTS', 'requires_inline_context_review': 'Y', 'candidate_status': 'ACQUIRED_UNVALIDATED_CONTEXT'}

def acquire(filing_index_path: Path, output_path: Path, coverage_path: Path, cache_dir: Path, user_agent: str, request_delay: float=0.12) -> tuple[list[dict], list[dict]]:
    eligible, filing_by_accession = _load_eligible_filings(filing_index_path)
    issuer_rows: dict[str, dict] = {}
    for filing in eligible:
        issuer_rows.setdefault(filing['cik'], filing)
    output: list[dict] = []
    errors: dict[str, str] = {}
    cache_dir.mkdir(parents=True, exist_ok=True)
    retrieved_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    for position, (cik, issuer) in enumerate(sorted(issuer_rows.items(), key=lambda item: item[1]['ticker'])):
        cache_path = cache_dir / f'CIK{cik}.json.gz'
        try:
            payload = _http_bytes(SEC_COMPANYFACTS_URL.format(cik=cik), user_agent)
            with gzip.open(cache_path, 'wb') as handle:
                handle.write(payload)
            companyfacts = json.loads(payload)
            issuer_accessions = {accn: filing for accn, filing in filing_by_accession.items() if filing['cik'] == cik}
            for fact in _candidate_facts(companyfacts, issuer_accessions):
                fact['retrieved_timestamp_utc'] = retrieved_at
                fact['companyfacts_payload_sha256'] = hashlib.sha256(payload).hexdigest()
                output.append(fact)
        except Exception as exc:
            errors[cik] = f'{type(exc).__name__}: {exc}'
        if position + 1 < len(issuer_rows):
            time.sleep(request_delay)
    output.sort(key=lambda row: (row['ticker'], row['canonical_concept'], row['period_end'], row['accession_number'], int(row['mapping_priority']), row['period_start'], str(row['value'])))
    output_fields = list(output[0]) if output else []
    with output_path.open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=output_fields)
        writer.writeheader()
        writer.writerows(output)
    coverage: list[dict] = []
    for cik, issuer in sorted(issuer_rows.items(), key=lambda item: item[1]['ticker']):
        issuer_facts = [row for row in output if row['cik'] == cik]
        for canonical in CONCEPT_MAP:
            concept_facts = [row for row in issuer_facts if row['canonical_concept'] == canonical]
            accessions = {row['accession_number'] for row in concept_facts}
            periods = {(row['period_start'], row['period_end']) for row in concept_facts}
            if cik in errors:
                status = 'DOWNLOAD_FAILED'
            elif not concept_facts:
                status = 'MISSING_STANDARD_TAG_CANDIDATE'
            else:
                status = 'ACQUIRED_REQUIRES_INLINE_CONTEXT_REVIEW'
            coverage.append({'batch_id': issuer['batch_id'], 'model_date': issuer['model_date'], 'ticker': issuer['ticker'], 'company_name': issuer['company_name'], 'cik': cik, 'target_flag': issuer['target_flag'], 'canonical_concept': canonical, 'candidate_fact_count': len(concept_facts), 'distinct_accession_count': len(accessions), 'distinct_period_count': len(periods), 'acquisition_status': status, 'error': errors.get(cik, ''), 'next_action': 'Inspect inline XBRL/custom tags' if not concept_facts else 'Resolve dimensions, scope, duration, duplicates, and mapping priority'})
    coverage_fields = list(coverage[0]) if coverage else []
    with coverage_path.open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=coverage_fields)
        writer.writeheader()
        writer.writerows(coverage)
    return (output, coverage)

def main() -> None:
    return None
if __name__ == '__main__':
    main()

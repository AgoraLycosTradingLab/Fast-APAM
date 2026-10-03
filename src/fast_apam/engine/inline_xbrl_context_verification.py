"""Extract inline-XBRL facts and contexts for controlled Fast APAM review targets."""
from __future__ import annotations
from ..settings import MODEL_DATE, COHORT_SIZE, WAVE_COUNTS
import argparse
import csv
import gzip
import hashlib
import json
import re
import time
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from lxml import html
FACT_TAGS = {'ix:nonfraction', 'ix:nonnumeric'}

def _http_bytes(url: str, user_agent: str, retries: int=4) -> bytes:
    headers = {'User-Agent': user_agent, 'Accept-Encoding': 'gzip, deflate'}
    for attempt in range(retries):
        try:
            with urlopen(Request(url, headers=headers), timeout=90) as response:
                payload = response.read()
                if response.headers.get('Content-Encoding') == 'gzip' or payload[:2] == b'\x1f\x8b':
                    payload = gzip.decompress(payload)
                return payload
        except (HTTPError, URLError, TimeoutError) as exc:
            if attempt == retries - 1:
                raise RuntimeError(f'Inline filing download failed: {url}') from exc
            time.sleep(2 ** attempt)
    raise AssertionError('unreachable')

def _tag(element) -> str:
    return str(element.tag).lower()

def _first_text(element, suffix: str) -> str:
    for child in element.iter():
        if _tag(child).endswith(suffix.lower()):
            return ''.join(child.itertext()).strip()
    return ''

def _context_record(element) -> dict:
    dimensions = []
    for child in element.iter():
        tag = _tag(child)
        if tag.endswith('explicitmember'):
            dimensions.append({'dimension': child.get('dimension', ''), 'member': ''.join(child.itertext()).strip()})
        elif tag.endswith('typedmember'):
            dimensions.append({'dimension': child.get('dimension', ''), 'member': ''.join(child.itertext()).strip()})
    start = _first_text(element, 'startdate')
    end = _first_text(element, 'enddate')
    instant = _first_text(element, 'instant')
    duration_days = ''
    if start and end:
        duration_days = (date.fromisoformat(end) - date.fromisoformat(start)).days + 1
    return {'context_id': element.get('id', ''), 'entity_identifier': _first_text(element, 'identifier'), 'period_start': start, 'period_end': end or instant, 'period_type': 'DURATION' if start else 'INSTANT' if instant else 'UNKNOWN', 'duration_days': duration_days, 'dimensions_json': json.dumps(dimensions, separators=(',', ':'), sort_keys=True), 'dimension_count': len(dimensions), 'consolidation_scope': 'CONSOLIDATED_DEFAULT' if not dimensions else 'DIMENSIONED'}

def _numeric_value(element, raw_text: str) -> str:
    if element.get('xsi:nil', '').lower() == 'true':
        return ''
    cleaned = raw_text.replace('−', '-').replace(',', '').replace('$', '').strip()
    if not cleaned or cleaned in {'—', '–', '-'}:
        return ''
    negative = cleaned.startswith('(') and cleaned.endswith(')')
    cleaned = cleaned.strip('() ')
    cleaned = re.sub('[^0-9.\\-+]', '', cleaned)
    try:
        value = Decimal(cleaned)
        scale = int(element.get('scale', '0') or 0)
        value *= Decimal(10) ** scale
        if negative:
            value = -value
        if element.get('sign') == '-':
            value = -abs(value)
        return format(value, 'f')
    except (InvalidOperation, ValueError):
        return ''

def extract_filing(payload: bytes, filing: dict, retrieved_at: str) -> list[dict]:
    tree = html.fromstring(payload)
    contexts = {element.get('id', ''): _context_record(element) for element in tree.iter() if _tag(element) == 'xbrli:context'}
    rows = []
    for element in tree.iter():
        tag = _tag(element)
        if tag not in FACT_TAGS:
            continue
        context = contexts.get(element.get('contextref', ''), {'context_id': element.get('contextref', ''), 'entity_identifier': '', 'period_start': '', 'period_end': '', 'period_type': 'UNKNOWN', 'duration_days': '', 'dimensions_json': '[]', 'dimension_count': '', 'consolidation_scope': 'CONTEXT_NOT_FOUND'})
        raw_text = ' '.join(' '.join(element.itertext()).split())
        is_numeric = tag == 'ix:nonfraction'
        row = {'batch_id': filing['batch_id'], 'model_date': filing['model_date'], 'ticker': filing['ticker'], 'cik': filing['cik'], 'accession_number': filing['accession_number'], 'form_type': filing['form_type'], 'report_period': filing['report_period'], 'accepted_timestamp_utc': filing['accepted_timestamp_utc'], 'model_available_date': filing['model_available_date'], 'fact_id': element.get('id', ''), 'fact_type': 'NUMERIC' if is_numeric else 'NONNUMERIC', 'taxonomy_concept': element.get('name', ''), 'context_id': context['context_id'], 'entity_identifier': context['entity_identifier'], 'period_start': context['period_start'], 'period_end': context['period_end'], 'period_type': context['period_type'], 'duration_days': context['duration_days'], 'dimensions_json': context['dimensions_json'], 'dimension_count': context['dimension_count'], 'consolidation_scope': context['consolidation_scope'], 'unit_ref': element.get('unitref', ''), 'scale': element.get('scale', ''), 'decimals': element.get('decimals', ''), 'format': element.get('format', ''), 'sign': element.get('sign', ''), 'raw_text': raw_text, 'parsed_value': _numeric_value(element, raw_text) if is_numeric else '', 'source_url': filing['source_url'], 'retrieved_timestamp_utc': retrieved_at, 'filing_payload_sha256': hashlib.sha256(payload).hexdigest()}
        rows.append(row)
    return rows

def run(targets_path: Path, output_path: Path, cache_dir: Path, user_agent: str) -> list[dict]:
    with targets_path.open(newline='', encoding='utf-8-sig') as handle:
        targets = list(csv.DictReader(handle))
    cache_dir.mkdir(parents=True, exist_ok=True)
    retrieved_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    rows: list[dict] = []
    for position, filing in enumerate(targets):
        cache_path = cache_dir / f"{filing['accession_number'].replace('-', '')}_{filing['primary_document']}"
        payload = _http_bytes(filing['source_url'], user_agent)
        cache_path.write_bytes(payload)
        rows.extend(extract_filing(payload, filing, retrieved_at))
        if position + 1 < len(targets):
            time.sleep(0.12)
    rows.sort(key=lambda r: (r['ticker'], r['accession_number'], r['taxonomy_concept'], r['context_id'], r['fact_id']))
    fields = list(rows[0]) if rows else []
    with output_path.open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    return rows

def main() -> None:
    return None
if __name__ == '__main__':
    main()

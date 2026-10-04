"""Download selected SEC filings and retain their inline contexts for review.

This stage records evidence only. Candidate issuer identities and facts remain
unapproved for financial construction and scoring.
"""
import csv
import hashlib
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from .credentials import sec_user_agent
from .engine.inline_xbrl_context_verification import _http_bytes, extract_filing


def verify_contexts(preparation_folder, transport=_http_bytes, progress=None):
    folder = Path(preparation_folder)
    manifest = json.loads((folder / 'preparation.json').read_text(encoding='utf-8'))
    if manifest['status'] not in {'CANDIDATES_ACQUIRED_NOT_SCORE_READY', 'INCOMPLETE'}:
        raise ValueError('Preparation has no completed candidate stage')
    if (folder / 'inline_facts.csv').exists() or (folder / 'inline_context_audit.csv').exists():
        raise ValueError('Inline outputs already exist; use a new preparation folder')
    with (folder / 'filing_targets.csv').open(newline='', encoding='utf-8-sig') as handle:
        targets = list(csv.DictReader(handle))
    with (folder / 'filing_index.csv').open(newline='', encoding='utf-8-sig') as handle:
        index = {row['accession_number']: row for row in csv.DictReader(handle)}
    if not targets:
        raise ValueError('No eligible inline filing targets to verify')
    # Validate every target before issuing a network request.
    for row in targets:
        source = index.get(row['accession_number'])
        if source is None or any(row.get(key) != source.get(key) for key in
                                 ('ticker', 'cik', 'model_date', 'source_url', 'model_available_date')):
            raise ValueError('Filing target does not match the acquisition index')
        if row['model_date'] != manifest['model_date'] or row['model_available_date'] > manifest['model_date']:
            raise ValueError('Filing target exceeds the model date')
        if row['eligible_on_model_date'] != 'Y' or row['index_status'] != 'CANDIDATE_IDENTITY_UNVERIFIED':
            raise ValueError('Filing target has invalid candidate status')
        if row['is_inline_xbrl'] != '1':
            raise ValueError('Filing target is not inline XBRL')
        url = urlparse(row['source_url'])
        expected = (f"/Archives/edgar/data/{int(row['cik'])}/"
                    f"{row['accession_number'].replace('-', '')}/{row['primary_document']}")
        if ((url.scheme, url.netloc, url.path, url.query, url.fragment) !=
                ('https', 'www.sec.gov', expected, '', '')):
            raise ValueError('Filing target has an unapproved SEC archive URL')
        if not re.fullmatch(r'[A-Za-z0-9_.-]+', row['primary_document']):
            raise ValueError('Filing target has an invalid document name')
    agent = sec_user_agent()
    audit = []
    facts_path = folder / 'inline_facts.csv'
    with facts_path.open('w', newline='', encoding='utf-8') as handle:
        writer = None
        for position, row in enumerate(targets, 1):
            if progress:
                progress(f"Verifying inline contexts {position}/{len(targets)}: {row['ticker']}")
            try:
                payload = transport(row['source_url'], agent)
                if not isinstance(payload, bytes):
                    raise ValueError('SEC filing response must be bytes')
                digest = hashlib.sha256(payload).hexdigest()
                rows = extract_filing(payload, row, datetime.now(timezone.utc).isoformat())
                raw = folder / 'raw' / (digest + '.html')
                raw.parent.mkdir(parents=True, exist_ok=True)
                if not raw.exists():
                    raw.write_bytes(payload)
                if rows:
                    if writer is None:
                        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
                        writer.writeheader()
                    writer.writerows(rows)
                audit.append({'ticker': row['ticker'], 'accession_number': row['accession_number'],
                              'model_date': row['model_date'], 'model_available_date': row['model_available_date'],
                              'source_url': row['source_url'], 'filing_payload_sha256': digest,
                              'inline_fact_count': len(rows),
                              'status': 'EXTRACTED_CANDIDATE_CONTEXTS' if rows else 'NO_INLINE_FACTS',
                              'reason': '' if rows else 'NO_INLINE_FACTS'})
            except Exception as error:
                # Provider errors may echo the private User-Agent; keep only the type.
                audit.append({'ticker': row['ticker'], 'accession_number': row['accession_number'],
                              'model_date': row['model_date'], 'model_available_date': row['model_available_date'],
                              'source_url': row['source_url'], 'filing_payload_sha256': '',
                              'inline_fact_count': 0, 'status': 'EXTRACTION_FAILED',
                              'reason': type(error).__name__})
            if position < len(targets):
                time.sleep(.15)
        if writer is None:
            # A header makes zero-result output distinguishable from a missing file.
            handle.write('model_date,ticker,accession_number,taxonomy_concept,context_id\n')
    with (folder / 'inline_context_audit.csv').open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(audit[0]))
        writer.writeheader()
        writer.writerows(audit)
    result = {'model_date': manifest['model_date'], 'target_count': len(targets),
              'extracted_count': sum(row['status'] == 'EXTRACTED_CANDIDATE_CONTEXTS' for row in audit),
              'failure_count': sum(row['status'] == 'EXTRACTION_FAILED' for row in audit),
              'inline_fact_count': sum(row['inline_fact_count'] for row in audit),
              'ready_to_score': False}
    (folder / 'inline_context_summary.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    return result

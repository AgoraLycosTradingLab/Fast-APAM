"""Offline validation of customer input syntax, not issuer or peer eligibility."""
import csv
import re
from datetime import date
from pathlib import Path


def check_setup(universe_path, model_date):
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', model_date):
        raise ValueError('Model date must use YYYY-MM-DD.')
    date.fromisoformat(model_date)
    tickers = []
    seen = set()
    with Path(universe_path).open(encoding='utf-8-sig', newline='') as source:
        reader = csv.DictReader(source, strict=True)
        if reader.fieldnames != ['ticker']:
            raise ValueError('Universe CSV must contain exactly one column named ticker. Do not place credentials in this file.')
        for line, row in enumerate(reader, start=2):
            if None in row:
                raise ValueError(f'Universe row {line} has extra columns.')
            symbol = (row.get('ticker') or '').strip().upper()
            if not re.fullmatch(r'[A-Z][A-Z0-9]*(?:[.-][A-Z0-9]+)*', symbol) or len(symbol) > 15:
                raise ValueError(f'Universe row {line} needs a ticker using letters, digits, dots or hyphens (maximum 15 characters).')
            if symbol in seen:
                raise ValueError(f'Universe row {line} duplicates an earlier ticker after case/whitespace normalization.')
            seen.add(symbol)
            tickers.append(symbol)
    if not tickers:
        raise ValueError('Universe CSV contains no tickers.')
    return {
        'setup_status': 'INPUT_FORMAT_VALID',
        'model_date': model_date,
        'requested_ticker_count': len(tickers),
        'requested_tickers': tickers,
        'data_source': 'SEC',
        'credential_required_for_this_check': False,
        'network_requests_made': False,
        'issuer_identity_verified': False,
        'dated_universe_eligibility_verified': False,
        'peer_coverage_validated': False,
        'ready_to_score': False,
        'next_step': 'Resolve dated issuer identities and membership, prepare reviewed financial inputs, and validate the governed peer cohort before scoring. Automatic preparation from this ticker file is not implemented yet.',
    }

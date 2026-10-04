"""Customer requests select outputs, never the normalization cohort."""
import csv
import hashlib
import io
import re
from pathlib import Path


def read_universe(path):
    payload = Path(path).read_bytes()
    reader = csv.DictReader(io.StringIO(payload.decode('utf-8-sig'), newline=''), strict=True)
    if not reader.fieldnames or len(reader.fieldnames) != 1 or reader.fieldnames[0].strip().casefold() != 'ticker':
        raise ValueError('Universe CSV must contain exactly one column named ticker. Do not place credentials in this file.')
    tickers, seen = [], set()
    for line, row in enumerate(reader, start=2):
        if None in row:
            raise ValueError(f'Universe row {line} has extra columns.')
        symbol = (row.get(reader.fieldnames[0]) or '').strip().upper()
        if not re.fullmatch(r'[A-Z][A-Z0-9]*(?:[.-][A-Z0-9]+)*', symbol) or len(symbol) > 15:
            raise ValueError(f'Universe row {line} needs a ticker using letters, digits, dots or hyphens (maximum 15 characters).')
        if symbol in seen:
            raise ValueError(f'Universe row {line} duplicates an earlier ticker after case/whitespace normalization.')
        seen.add(symbol)
        tickers.append(symbol)
    if not tickers:
        raise ValueError('Universe CSV contains no tickers.')
    return {'requested_tickers': tickers, 'input_sha256': hashlib.sha256(payload).hexdigest()}


def select_results(cohort_rows, request, model_date):
    if not cohort_rows:
        raise ValueError('Prepared cohort has no result rows')
    by_ticker = {row['ticker']: row for row in cohort_rows}
    if len(by_ticker) != len(cohort_rows):
        raise ValueError('Prepared cohort has duplicate result tickers')
    selected, missing = [], []
    for ticker in request['requested_tickers']:
        if ticker in by_ticker:
            row = dict(by_ticker[ticker])
            if row['model_date'] != model_date:
                raise ValueError('Requested stock result does not match the effective model date')
        else:
            missing.append(ticker)
            row = {field: '' for field in cohort_rows[0]}
            values = {
                'ticker': ticker, 'model_date': model_date, 'score_published': 'NO',
                'PROVISIONAL_FAST_STATUS': 'UNSCORED',
                'PROVISIONAL_DATA_STATUS': 'NOT_IN_PREPARED_COHORT',
                'gate_reason': 'NO_VALIDATED_INPUTS_IN_SELECTED_SNAPSHOT',
                'underlying_candidate_hold_reason': 'DATED_IDENTITY_FINANCIAL_INPUTS_AND_PEER_COVERAGE_REQUIRED',
                'status_reason': 'REQUESTED_STOCK_NOT_COVERED_BY_PREPARED_SNAPSHOT',
                'production_approved': 'NO', 'investability_status_calculated': 'NO',
            }
            row.update({key: value for key, value in values.items() if key in row})
        selected.append(row)
    scored = sum(row['score_published'] == 'YES' for row in selected)
    return selected, {
        'requested_tickers': list(request['requested_tickers']),
        'input_sha256': request['input_sha256'],
        'requested_count': len(selected), 'matched_count': len(selected) - len(missing),
        'scored_count': scored, 'unscored_count': len(selected) - scored,
        'not_in_prepared_cohort': missing,
        'normalization_scope': 'FULL_PREPARED_COHORT',
        'normalization_cohort_count': len(cohort_rows),
        'selection_changes_scores': False,
    }

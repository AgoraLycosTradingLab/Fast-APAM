"""Dated IVV holdings as a disclosed S&P 500 membership/sector proxy.

Fund holdings are not official index constituents or licensed GICS history.
This module supplies auditable peer *candidates*, never score approval.
"""
import csv
import hashlib
import io
import json
import re
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.request import Request, urlopen

from .market_date import resolve_model_date
from .universe import read_universe


IVV_CSV_URL = 'https://www.ishares.com/us/products/239726/ishares-core-s-p-500-etf/latest-holdings.csv'
FUND_NAME = 'iShares Core S&P 500 ETF'
REQUIRED_COLUMNS = {'Ticker', 'Name', 'Sector', 'Asset Class'}
SYMBOL = re.compile(r'[A-Z0-9][A-Z0-9.-]{0,14}\Z')
SECTOR_LABELS = {'Communication': 'Communication Services'}
KNOWN_SECTORS = {'Communication Services', 'Consumer Discretionary',
                 'Consumer Staples', 'Energy', 'Financials', 'Health Care',
                 'Industrials', 'Information Technology', 'Materials',
                 'Real Estate', 'Utilities'}
COHORT_FIELDS = ['model_date', 'ticker', 'company_name', 'sector', 'source_sector',
                 'holdings_as_of_date', 'proxy_age_days', 'source_sha256',
                 'membership_basis', 'classification_basis']
AUDIT_FIELDS = ['model_date', 'holdings_as_of_date', 'raw_ticker', 'ticker', 'company_name',
                'source_sector', 'asset_class', 'status', 'reason', 'source_sha256']


def _write(path, rows, fields):
    with path.open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def parse_holdings(payload):
    """Read sponsor metadata and table; fail on a changed or malformed format."""
    content = payload.decode('utf-8-sig')
    rows = list(csv.reader(io.StringIO(content)))
    if not rows or not rows[0] or rows[0][0].strip() != FUND_NAME:
        raise ValueError('Holdings file is not the expected IVV fund')
    dates = [row[1].strip() for row in rows[:12] if len(row) >= 2 and
             row[0].strip() == 'Fund Holdings as of']
    if len(dates) != 1:
        raise ValueError('Holdings file needs exactly one as-of date')
    try:
        as_of = datetime.strptime(dates[0], '%b %d, %Y').date()
    except ValueError as error:
        raise ValueError('Unrecognized IVV holdings as-of date') from error
    header_positions = [index for index, row in enumerate(rows) if REQUIRED_COLUMNS.issubset(row)]
    if len(header_positions) != 1:
        raise ValueError('Holdings file needs exactly one recognized table')
    start = header_positions[0]
    header = rows[start]
    holdings = []
    for row in rows[start + 1:]:
        if not row or not any(value.strip() for value in row):
            if holdings:
                break
            continue
        if len(row) != len(header):
            raise ValueError('Malformed IVV holdings table row')
        holdings.append(dict(zip(header, row)))
    if not holdings:
        raise ValueError('IVV holdings table is empty')
    return as_of, holdings


def _download_latest(url=IVV_CSV_URL):
    if url != IVV_CSV_URL:
        raise ValueError('Unapproved holdings source URL')
    request = Request(url, headers={'User-Agent': 'FastAPAM/0.1 (+https://github.com/AgoraLycosTradingLab/Fast-APAM)',
                                    'Accept': 'text/csv,text/plain'})
    with urlopen(request, timeout=60) as response:
        return response.read()


def _source(model_day, holdings_file, cache_dir, transport):
    if holdings_file is not None:
        payload = Path(holdings_file).read_bytes()
        as_of, holdings = parse_holdings(payload)
        return payload, as_of, holdings, 'LOCAL_DATED_IVV_CSV', str(Path(holdings_file).resolve())
    cache_dir.mkdir(parents=True, exist_ok=True)
    # A historical request must not depend on today's changing sponsor file.
    # The latest completed session checks the sponsor for a fresh archive.
    if model_day >= date.today() - timedelta(days=7):
        payload = transport(IVV_CSV_URL)
        as_of, _ = parse_holdings(payload)
        digest = hashlib.sha256(payload).hexdigest()
        archived = cache_dir / f'IVV_{as_of.isoformat()}_{digest}.csv'
        if not archived.exists():
            archived.write_bytes(payload)
    candidates = []
    for path in cache_dir.glob('IVV_*.csv'):
        match = re.fullmatch(r'IVV_(\d{4}-\d{2}-\d{2})_([0-9a-f]{64})\.csv', path.name)
        if not match:
            continue
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != match.group(2):
            raise ValueError('Cached holdings checksum mismatch')
        dated, rows = parse_holdings(raw)
        if dated.isoformat() != match.group(1):
            raise ValueError('Cached holdings date mismatch')
        if dated <= model_day:
            candidates.append((dated, raw, rows, path))
    if not candidates:
        raise ValueError('No archived IVV holdings file is dated on or before the model date')
    dated, raw, rows, path = max(candidates, key=lambda item: item[0])
    return raw, dated, rows, 'OFFICIAL_IVV_DOWNLOAD_ARCHIVE', str(path.resolve())


def build_proxy(universe_path, model_date, output, *, holdings_file=None,
                cache_dir='data/etf-holdings', transport=_download_latest,
                max_age_days=14, min_equity_holdings=400):
    resolution = resolve_model_date(model_date)
    day = date.fromisoformat(resolution['effective_model_date'])
    request = read_universe(universe_path)
    folder = Path(output)
    if folder.exists() and (not folder.is_dir() or any(folder.iterdir())):
        raise ValueError('Proxy output must be a new or empty folder')
    payload, as_of, holdings, source_type, source_path = _source(
        day, holdings_file, Path(cache_dir), transport)
    if as_of > day:
        raise ValueError('ETF holdings were published after the model date; look-ahead blocked')
    age = (day - as_of).days
    if age > max_age_days:
        raise ValueError(f'ETF holdings are {age} days old; limit is {max_age_days} days')
    digest = hashlib.sha256(payload).hexdigest()
    audit, cohort = [], []
    counts = Counter(row['Ticker'].strip().upper() for row in holdings
                     if row['Asset Class'].strip() == 'Equity')
    for row in holdings:
        raw_ticker = row['Ticker'].strip()
        ticker = raw_ticker.upper()
        asset_class = row['Asset Class'].strip()
        sector = row['Sector'].strip()
        name = row['Name'].strip()
        status = 'PEER_CANDIDATE'
        reason = ''
        if asset_class != 'Equity':
            status, reason = 'EXCLUDED_NON_EQUITY', asset_class
        elif not SYMBOL.fullmatch(ticker):
            status, reason = 'REVIEW_SYMBOL_FORMAT', 'DO_NOT_GUESS_SHARE_CLASS_ALIAS'
        elif not sector:
            status, reason = 'REVIEW_MISSING_SECTOR', 'NO_SPONSOR_SECTOR'
        elif SECTOR_LABELS.get(sector, sector) not in KNOWN_SECTORS:
            status, reason = 'REVIEW_UNKNOWN_SECTOR', 'UNRECOGNIZED_SPONSOR_SECTOR'
        elif counts[ticker] > 1:
            status, reason = 'REVIEW_DUPLICATE_TICKER', 'DUPLICATE_HOLDING_SYMBOL'
        if status == 'PEER_CANDIDATE':
            cohort.append({'model_date': day.isoformat(), 'ticker': ticker, 'company_name': name,
                           'sector': SECTOR_LABELS.get(sector, sector), 'source_sector': sector,
                           'holdings_as_of_date': as_of.isoformat(), 'proxy_age_days': age,
                           'source_sha256': digest, 'membership_basis': 'IVV_HOLDINGS_PROXY',
                           'classification_basis': 'IVV_SPONSOR_SECTOR_PROXY'})
        audit.append({'model_date': day.isoformat(), 'holdings_as_of_date': as_of.isoformat(),
                      'raw_ticker': raw_ticker, 'ticker': ticker if status == 'PEER_CANDIDATE' else '',
                      'company_name': name, 'source_sector': sector, 'asset_class': asset_class,
                      'status': status, 'reason': reason, 'source_sha256': digest})
    if len(cohort) < min_equity_holdings:
        raise ValueError(f'Only {len(cohort)} unambiguous equity holdings; minimum is {min_equity_holdings}')
    by_ticker = {row['ticker']: row for row in cohort}
    for ticker in request['requested_tickers']:
        if ticker not in by_ticker:
            audit.append({'model_date': day.isoformat(), 'holdings_as_of_date': as_of.isoformat(),
                          'raw_ticker': ticker, 'ticker': ticker, 'company_name': '',
                          'source_sector': '', 'asset_class': '', 'status': 'REQUESTED_NOT_IN_PROXY',
                          'reason': 'NOT_IN_DATED_IVV_EQUITY_HOLDINGS_OR_ALIAS_UNRESOLVED',
                          'source_sha256': digest})
    folder.mkdir(parents=True, exist_ok=True)
    cohort_path = folder / 'etf_proxy_cohort.csv'
    _write(cohort_path, cohort, COHORT_FIELDS)
    _write(folder / 'etf_proxy_audit.csv', audit, AUDIT_FIELDS)
    result = {'model_date': day.isoformat(), 'date_resolution': resolution,
              'holdings_as_of_date': as_of.isoformat(), 'proxy_age_days': age,
              'source_type': source_type, 'source_path': source_path,
              'source_url': IVV_CSV_URL if source_type == 'OFFICIAL_IVV_DOWNLOAD_ARCHIVE' else '',
              'source_sha256': digest, 'cohort_size': len(cohort),
              'cohort_sha256': hashlib.sha256(cohort_path.read_bytes()).hexdigest(),
              'requested_ticker_count': len(request['requested_tickers']),
              'requested_in_proxy_count': sum(ticker in by_ticker for ticker in request['requested_tickers']),
              'sector_counts': dict(Counter(row['sector'] for row in cohort)),
              'membership_basis': 'IVV_HOLDINGS_PROXY_NOT_OFFICIAL_SP500',
              'classification_basis': 'IVV_SPONSOR_SECTOR_NOT_LICENSED_GICS',
              'ready_to_score': False}
    (folder / 'etf_proxy_manifest.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    return result

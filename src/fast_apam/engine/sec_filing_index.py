"""Build a point-in-time SEC filing index for a frozen Fast APAM roster.

This module deliberately stops at filing metadata. It does not acquire XBRL facts,
construct quarters, normalize peers, or calculate scores.
"""
from __future__ import annotations
import argparse
import csv
import gzip
import json
import time
from dataclasses import dataclass
from datetime import date, datetime, time as clock_time, timedelta, timezone
from pathlib import Path
from typing import Iterable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo
SEC_SUBMISSIONS_URL = 'https://data.sec.gov/submissions/CIK{cik}.json'
SEC_ARCHIVE_URL = 'https://www.sec.gov/Archives/edgar/data/{cik}/{accession}/{document}'
EASTERN = ZoneInfo('America/New_York')
UTC = timezone.utc
ALLOWED_FORMS = {'10-Q', '10-K', '10-Q/A', '10-K/A'}

@dataclass(frozen=True)
class FilingAvailability:
    accepted_eastern: datetime
    buffer_trading_day: date
    model_available_date: date

def _nth_weekday(year: int, month: int, weekday: int, n: int) -> date:
    d = date(year, month, 1)
    return d + timedelta(days=(weekday - d.weekday()) % 7 + 7 * (n - 1))

def _last_weekday(year: int, month: int, weekday: int) -> date:
    if month == 12:
        d = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        d = date(year, month + 1, 1) - timedelta(days=1)
    return d - timedelta(days=(d.weekday() - weekday) % 7)

def _observed(d: date) -> date:
    if d.weekday() == 5:
        return d - timedelta(days=1)
    if d.weekday() == 6:
        return d + timedelta(days=1)
    return d

def _easter(year: int) -> date:
    """Gregorian Easter date (Anonymous Gregorian algorithm)."""
    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = (h + l - 7 * m + 114) % 31 + 1
    return date(year, month, day)

def nyse_holidays(year: int) -> set[date]:
    """Regular NYSE full-day holidays for modern Fast APAM test years.

    The pilot covers 2023 onward. Extraordinary exchange closures must be added
    explicitly before extending this calendar to affected historical periods.
    """
    holidays = {_observed(date(year, 1, 1)), _nth_weekday(year, 1, 0, 3), _nth_weekday(year, 2, 0, 3), _easter(year) - timedelta(days=2), _last_weekday(year, 5, 0), _observed(date(year, 7, 4)), _nth_weekday(year, 9, 0, 1), _nth_weekday(year, 11, 3, 4), _observed(date(year, 12, 25))}
    if year >= 2022:
        holidays.add(_observed(date(year, 6, 19)))
    return holidays

def is_nyse_trading_day(d: date) -> bool:
    return d.weekday() < 5 and d not in nyse_holidays(d.year)

def next_trading_day(d: date, *, include_current: bool=False) -> date:
    candidate = d if include_current else d + timedelta(days=1)
    while not is_nyse_trading_day(candidate):
        candidate += timedelta(days=1)
    return candidate

def parse_sec_timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)

def calculate_availability(accepted_utc: datetime) -> FilingAvailability:
    """Apply the approved one-complete-NYSE-session processing buffer.

    A filing accepted before 09:30 Eastern on a trading day uses that session as
    its full buffer day. A filing accepted at/after 09:30, or on a non-trading
    day, uses the next trading session. It becomes eligible the session after
    the buffer day. This reproduces the approved Microsoft timing fixture.
    """
    local = accepted_utc.astimezone(EASTERN)
    before_open = local.timetz().replace(tzinfo=None) < clock_time(9, 30)
    if is_nyse_trading_day(local.date()) and before_open:
        buffer_day = local.date()
    else:
        buffer_day = next_trading_day(local.date())
    return FilingAvailability(local, buffer_day, next_trading_day(buffer_day))

def _http_json(url: str, user_agent: str, retries: int=4) -> dict:
    headers = {'User-Agent': user_agent, 'Accept': 'application/json', 'Accept-Encoding': 'gzip'}
    for attempt in range(retries):
        try:
            with urlopen(Request(url, headers=headers), timeout=45) as response:
                payload = response.read()
                if response.headers.get('Content-Encoding') == 'gzip' or payload[:2] == b'\x1f\x8b':
                    payload = gzip.decompress(payload)
                return json.loads(payload)
        except (HTTPError, URLError, TimeoutError) as exc:
            if attempt == retries - 1:
                raise RuntimeError(f'SEC request failed after {retries} attempts: {url}') from exc
            time.sleep(2 ** attempt)
    raise AssertionError('unreachable')

def _recent_filings(submission: dict) -> Iterable[dict]:
    recent = submission.get('filings', {}).get('recent', {})
    keys = list(recent)
    count = len(recent.get('accessionNumber', []))
    for i in range(count):
        yield {key: recent[key][i] if i < len(recent[key]) else '' for key in keys}

def build_index(roster_path: Path, output_path: Path, register_path: Path, model_date: date, history_start: date, user_agent: str, request_delay: float=0.12) -> tuple[list[dict], list[dict]]:
    with roster_path.open(newline='', encoding='utf-8-sig') as handle:
        roster = list(csv.DictReader(handle))
    results: list[dict] = []
    issuer_summaries: list[dict] = []
    retrieved_at = datetime.now(UTC).replace(microsecond=0).isoformat()
    for position, issuer in enumerate(roster):
        cik = issuer['cik'].zfill(10)
        submission = _http_json(SEC_SUBMISSIONS_URL.format(cik=cik), user_agent)
        legal_name = submission.get('name', issuer['company_name'])
        fiscal_year_end = submission.get('fiscalYearEnd', '')
        issuer_rows: list[dict] = []
        for filing in _recent_filings(submission):
            form = filing.get('form', '')
            if form not in ALLOWED_FORMS or not filing.get('acceptanceDateTime'):
                continue
            filed_date = date.fromisoformat(filing['filingDate'])
            if filed_date < history_start:
                continue
            accepted_utc = parse_sec_timestamp(filing['acceptanceDateTime'])
            availability = calculate_availability(accepted_utc)
            accession = filing['accessionNumber']
            primary_document = filing.get('primaryDocument', '')
            eligible = availability.model_available_date <= model_date
            exclusion_reason = '' if eligible else 'MODEL_AVAILABLE_AFTER_CUTOFF'
            row = {'batch_id': issuer['batch_id'], 'snapshot_id': issuer['snapshot_id'], 'model_date': model_date.isoformat(), 'ticker': issuer['ticker'], 'company_name': issuer['company_name'], 'legal_name': legal_name, 'cik': cik, 'target_flag': issuer['target_flag'], 'fiscal_year_end_mmdd': fiscal_year_end, 'accession_number': accession, 'form_type': form, 'is_amendment': 'Y' if form.endswith('/A') else 'N', 'filed_date': filing['filingDate'], 'report_period': filing.get('reportDate', ''), 'accepted_timestamp_utc': accepted_utc.isoformat(), 'accepted_timestamp_eastern': availability.accepted_eastern.isoformat(), 'buffer_trading_day': availability.buffer_trading_day.isoformat(), 'model_available_date': availability.model_available_date.isoformat(), 'eligible_on_model_date': 'Y' if eligible else 'N', 'exclusion_reason': exclusion_reason, 'primary_document': primary_document, 'source_url': SEC_ARCHIVE_URL.format(cik=str(int(cik)), accession=accession.replace('-', ''), document=primary_document), 'is_xbrl': str(filing.get('isXBRL', '')), 'is_inline_xbrl': str(filing.get('isInlineXBRL', '')), 'retrieved_timestamp_utc': retrieved_at, 'source_view': 'AS_FILED', 'index_status': 'ELIGIBLE' if eligible else 'EXCLUDED_LOOKAHEAD'}
            issuer_rows.append(row)
            results.append(row)
        eligible_rows = [r for r in issuer_rows if r['eligible_on_model_date'] == 'Y']
        eligible_rows.sort(key=lambda r: (r['model_available_date'], r['accepted_timestamp_utc'], r['accession_number']))
        latest = eligible_rows[-1] if eligible_rows else None
        history_risk = len(eligible_rows) < 9
        issuer_summaries.append({'ticker': issuer['ticker'], 'cik': cik, 'legal_name': legal_name, 'fiscal_year_end_mmdd': fiscal_year_end, 'eligible_filing_count': len(eligible_rows), 'excluded_lookahead_count': len(issuer_rows) - len(eligible_rows), 'latest': latest, 'history_risk': history_risk, 'status': 'NO_ELIGIBLE_FILINGS' if not eligible_rows else 'FILING_INDEX_COMPLETE_HISTORY_RISK' if history_risk else 'FILING_INDEX_COMPLETE'})
        if position + 1 < len(roster):
            time.sleep(request_delay)
    results.sort(key=lambda r: (r['ticker'], r['accepted_timestamp_utc'], r['accession_number']))
    fieldnames = list(results[0]) if results else []
    with output_path.open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)
    _update_register(register_path, issuer_summaries)
    return (results, issuer_summaries)

def _update_register(register_path: Path, summaries: list[dict]) -> None:
    with register_path.open(newline='', encoding='utf-8-sig') as handle:
        reader = csv.DictReader(handle)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)
    by_cik = {summary['cik']: summary for summary in summaries}
    if 'eligible_filing_count' not in fieldnames:
        fieldnames.extend(['eligible_filing_count', 'excluded_lookahead_count', 'fiscal_year_end_mmdd'])
    for row in rows:
        summary = by_cik[row['cik'].zfill(10)]
        latest = summary['latest']
        row['acquisition_status'] = summary['status']
        row['eligible_filing_count'] = str(summary['eligible_filing_count'])
        row['excluded_lookahead_count'] = str(summary['excluded_lookahead_count'])
        row['fiscal_year_end_mmdd'] = summary['fiscal_year_end_mmdd']
        row['exception_count'] = '1' if summary['history_risk'] else '0'
        if latest:
            row['latest_eligible_accession'] = latest['accession_number']
            row['latest_eligible_form'] = latest['form_type']
            row['accepted_at'] = latest['accepted_timestamp_utc']
            row['processing_buffer'] = f"FULL_NYSE_SESSION:{latest['buffer_trading_day']}"
            row['model_available_date'] = latest['model_available_date']
            row['latest_fiscal_period_end'] = latest['report_period']
            row['notes'] = 'Filing index complete; fewer than nine eligible periodic filings, so historical continuity requires review.' if summary['history_risk'] else 'Filing index complete; raw XBRL fact extraction not started.'
    with register_path.open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

def main() -> None:
    return None
if __name__ == '__main__':
    main()

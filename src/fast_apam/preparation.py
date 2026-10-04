"""Acquire auditable SEC candidates from a customer list; never publish scores.

Current SEC symbols are discovery hints, not historical identity or peer evidence.
Financial candidates require inline-context verification before construction.
"""
import csv
import hashlib
import json
import re
import time
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from .acquisition import download
from .credentials import sec_user_agent
from .customer_setup import check_setup
from .engine.sec_filing_index import (
    ALLOWED_FORMS, EASTERN, SEC_ARCHIVE_URL, SEC_SUBMISSIONS_URL,
    _recent_filings, calculate_availability, parse_sec_timestamp,
)
from .engine.sec_companyfacts_acquisition import SEC_COMPANYFACTS_URL, _candidate_facts
from .engine.historical_filing_targets import build_targets

TICKERS_URL = 'https://www.sec.gov/files/company_tickers.json'
ISSUER_FIELDS = ['ticker', 'cik', 'company_name', 'model_date', 'identity_status',
                 'source_url', 'source_sha256', 'retrieved_timestamp_utc']
EXCEPTION_FIELDS = ['ticker', 'stage', 'reason', 'detail']


def _write_csv(path, rows, empty_fields):
    fields = list(rows[0]) if rows else empty_fields
    with path.open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


class SecSession:
    """Allowlisted JSON retrieval with immutable evidence and private identification."""
    def __init__(self, folder, transport=download, delay=.2):
        self.folder, self.transport, self.delay = folder, transport, max(.15, delay)
        self.agent = None
        self.sources = []
        self.last_request = None

    def get(self, url):
        parsed = urlparse(url)
        allowed = (url == TICKERS_URL or (
            parsed.scheme == 'https' and parsed.netloc == 'data.sec.gov' and
            (re.fullmatch(r'/submissions/CIK\d{10}(?:-submissions-\d+)?\.json', parsed.path) or
             re.fullmatch(r'/api/xbrl/companyfacts/CIK\d{10}\.json', parsed.path)) and
            not parsed.query and not parsed.fragment))
        if not allowed:
            raise ValueError('Unapproved SEC JSON endpoint')
        if self.agent is None:
            self.agent = sec_user_agent()
        # Throttle every HTTP attempt, including failed ones and archive pages.
        if self.last_request is not None:
            time.sleep(max(0, self.delay - (time.monotonic() - self.last_request)))
        self.last_request = time.monotonic()
        payload = self.transport(url, self.agent)
        document = json.loads(payload)
        if not isinstance(document, dict):
            raise ValueError('SEC response must be a JSON object')
        digest = hashlib.sha256(payload).hexdigest()
        path = self.folder / 'raw' / (digest + '.json')
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_bytes(payload)
        evidence = {'source_url': url, 'source_sha256': digest,
                    'retrieved_timestamp_utc': datetime.now(timezone.utc).isoformat(),
                    'file': 'raw/' + path.name}
        self.sources.append(evidence)
        return document, evidence


def _all_filings(session, cik, submission, history_start, model_day):
    """SEC recent history alone is insufficient: retrieve overlapping older pages."""
    filings = list(_recent_filings(submission))
    for page in submission.get('filings', {}).get('files', []):
        if date.fromisoformat(page['filingTo']) < history_start:
            continue
        if date.fromisoformat(page['filingFrom']) > model_day:
            continue
        name = page['name']
        if not re.fullmatch(r'CIK' + re.escape(cik) + r'-submissions-\d+\.json', name):
            raise ValueError('Invalid SEC submissions archive filename')
        archived, _ = session.get('https://data.sec.gov/submissions/' + name)
        filings.extend(_recent_filings({'filings': {'recent': archived}}))
    by_accession = {}
    for filing in filings:
        accession = filing.get('accessionNumber', '')
        if accession in by_accession and by_accession[accession] != filing:
            raise ValueError('Conflicting filing metadata for one accession')
        by_accession[accession] = filing
    return list(by_accession.values())


def _filing_row(issuer, submission, filing, day, observed):
    accession = filing['accessionNumber']
    document = filing.get('primaryDocument', '')
    if not re.fullmatch(r'\d{10}-\d{2}-\d{6}', accession):
        raise ValueError('Invalid accession')
    if not re.fullmatch(r'[A-Za-z0-9_.-]+', document) or document in {'.', '..'}:
        raise ValueError('Invalid primary document')
    accepted = parse_sec_timestamp(filing['acceptanceDateTime'])
    availability = calculate_availability(accepted)
    filed = date.fromisoformat(filing['filingDate'])
    period = date.fromisoformat(filing['reportDate'])
    if period > filed or filed > accepted.astimezone(EASTERN).date():
        raise ValueError('Inconsistent filing dates')
    eligible = availability.model_available_date <= day
    return {
        'batch_id': 'CUSTOMER_DISCOVERY', 'snapshot_id': 'CUSTOMER_' + day.isoformat(),
        'model_date': day.isoformat(), 'ticker': issuer['ticker'],
        'company_name': issuer['company_name'], 'legal_name': submission.get('name', ''),
        'cik': issuer['cik'], 'target_flag': 'Y',
        'fiscal_year_end_mmdd': submission.get('fiscalYearEnd', ''),
        'accession_number': accession, 'form_type': filing['form'],
        'is_amendment': 'Y' if filing['form'].endswith('/A') else 'N',
        'filed_date': filed.isoformat(), 'report_period': period.isoformat(),
        'accepted_timestamp_utc': accepted.isoformat(),
        'accepted_timestamp_eastern': availability.accepted_eastern.isoformat(),
        'buffer_trading_day': availability.buffer_trading_day.isoformat(),
        'model_available_date': availability.model_available_date.isoformat(),
        'eligible_on_model_date': 'Y' if eligible else 'N',
        'exclusion_reason': '' if eligible else 'MODEL_AVAILABLE_AFTER_CUTOFF',
        'primary_document': document,
        'source_url': SEC_ARCHIVE_URL.format(cik=str(int(issuer['cik'])),
            accession=accession.replace('-', ''), document=document),
        'is_xbrl': str(filing.get('isXBRL', '')),
        'is_inline_xbrl': str(filing.get('isInlineXBRL', '')),
        'retrieved_timestamp_utc': observed, 'source_view': 'AS_FILED',
        'index_status': 'CANDIDATE_IDENTITY_UNVERIFIED' if eligible else 'EXCLUDED_LOOKAHEAD',
    }


def prepare(universe_path, model_date, output, history_start=None,
            transport=download, progress=None):
    setup = check_setup(universe_path, model_date)
    model_date = setup['model_date']
    if progress:
        progress('Requested date: ' + setup['date_resolution']['requested_date'] +
                 '; effective model date: ' + model_date)
    day = date.fromisoformat(model_date)
    if day > datetime.now(EASTERN).date():
        raise ValueError('Preparation cannot use a future model date')
    start = date.fromisoformat(history_start) if history_start else date(day.year - 3, 1, 1)
    if start < date(2023, 1, 1) or start > day:
        raise ValueError('History start must be between 2023-01-01 and the model date (supported pilot calendar)')
    folder = Path(output)
    if folder.exists() and (not folder.is_dir() or any(folder.iterdir())):
        raise ValueError('Preparation output must be a new or empty folder')
    agent = sec_user_agent()
    folder.mkdir(parents=True, exist_ok=True)
    session = SecSession(folder, transport)
    session.agent = agent
    issuers, index, candidates, exceptions = [], [], [], []
    failures = 0

    def issue(ticker, stage, reason, detail=''):
        exceptions.append(dict(ticker=ticker, stage=stage, reason=reason, detail=detail))

    target_summary = {'issuer_count': 0, 'selected_filing_count': 0,
                      'superseded_vintages_excluded': 0, 'status_counts': {}, 'form_counts': {}}

    def save(status):
        _write_csv(folder / 'issuer_candidates.csv', issuers, ISSUER_FIELDS)
        _write_csv(folder / 'filing_index.csv', index,
                   ['model_date', 'ticker', 'accession_number', 'eligible_on_model_date'])
        _write_csv(folder / 'candidate_facts.csv', candidates,
                   ['model_date', 'ticker', 'canonical_concept', 'candidate_status'])
        _write_csv(folder / 'preparation_exceptions.csv', exceptions, EXCEPTION_FIELDS)
        report = {
            'status': status, 'model_date': model_date, 'history_start': start.isoformat(),
            'date_resolution': setup['date_resolution'],
            'requested_ticker_count': len(setup['requested_tickers']),
            'issuer_candidate_count': len(issuers), 'filing_count': len(index),
            'eligible_filing_count': sum(r['eligible_on_model_date'] == 'Y' for r in index),
            'candidate_fact_count': len(candidates), 'acquisition_failures': failures,
            'exception_count': len(exceptions), 'ready_to_score': False,
            'filing_targets': target_summary,
            'universe_sha256': setup['universe_sha256'],
            'sources': session.sources,
            'remaining_gates': ['Dated identity, membership and sector/peer evidence',
                'Inline context verification and approved issuer mappings',
                'Standalone-quarter and TTM construction with controls',
                'Combined peer coverage validation before normalization and scoring'],
        }
        (folder / 'preparation.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
        return report

    save('IN_PROGRESS')
    try:
        tickers, evidence = session.get(TICKERS_URL)
        mapping = {}
        for item in tickers.values():
            symbol = str(item['ticker']).upper()
            cik = str(item['cik_str']).zfill(10)
            if not re.fullmatch(r'\d{10}', cik) or int(cik) <= 0:
                raise ValueError('Invalid SEC issuer identifier')
            mapping.setdefault(symbol, {})[cik] = item
    except Exception as error:
        failures += 1
        issue('', 'TICKER_DISCOVERY', 'ACQUISITION_FAILED', type(error).__name__)
        return save('INCOMPLETE')

    for position, ticker in enumerate(setup['requested_tickers'], 1):
        if progress:
            progress(f'Preparing {position}/{len(setup["requested_tickers"])}: {ticker}')
        matches = mapping.get(ticker, {})  # Never guess share-class aliases.
        if len(matches) != 1:
            issue(ticker, 'IDENTITY', 'UNKNOWN_TICKER' if not matches else 'AMBIGUOUS_TICKER')
            continue
        cik, company = next(iter(matches.items()))
        issuer = dict(ticker=ticker, cik=cik, company_name=company['title'], model_date=model_date,
                      identity_status='CURRENT_SEC_MATCH_ONLY',
                      **{key: evidence[key] for key in ['source_url', 'source_sha256', 'retrieved_timestamp_utc']})
        issuers.append(issuer)
        issue(ticker, 'IDENTITY', 'DATED_IDENTITY_AND_PEER_EVIDENCE_REQUIRED')
        try:
            submission, sub_evidence = session.get(SEC_SUBMISSIONS_URL.format(cik=cik))
            if str(submission.get('cik', '')).zfill(10) != cik:
                raise ValueError('SEC submissions identity mismatch')
            filings = _all_filings(session, cik, submission, start, day)
            issuer_index = []
            for filing in filings:
                if filing.get('form') not in ALLOWED_FORMS:
                    continue
                try:
                    if date.fromisoformat(filing['filingDate']) < start:
                        continue
                    issuer_index.append(_filing_row(issuer, submission, filing, day,
                                                   sub_evidence['retrieved_timestamp_utc']))
                except (KeyError, ValueError, TypeError):
                    failures += 1
                    issue(ticker, 'FILING_INDEX', 'INVALID_OR_MISSING_FILING_METADATA')
            index.extend(issuer_index)
            eligible = {r['accession_number']: r for r in issuer_index if r['eligible_on_model_date'] == 'Y'}
            if not eligible:
                issue(ticker, 'FILING_INDEX', 'NO_ELIGIBLE_US_PERIODIC_FILINGS')
                continue
            facts, fact_evidence = session.get(SEC_COMPANYFACTS_URL.format(cik=cik))
            if str(facts.get('cik', '')).zfill(10) != cik:
                raise ValueError('SEC Company Facts identity mismatch')
            retained = 0
            for fact in _candidate_facts(facts, eligible):
                try:
                    if not (date.fromisoformat(fact['period_start']) <= date.fromisoformat(fact['period_end']) <= day):
                        raise ValueError('Invalid or future period')
                except (ValueError, TypeError):
                    issue(ticker, 'CANDIDATE_FACTS', 'INVALID_OR_FUTURE_FACT_PERIOD')
                    continue
                fact['retrieved_timestamp_utc'] = fact_evidence['retrieved_timestamp_utc']
                fact['companyfacts_payload_sha256'] = fact_evidence['source_sha256']
                candidates.append(fact)
                retained += 1
            issue(ticker, 'CANDIDATE_FACTS', 'INLINE_CONTEXT_VERIFICATION_REQUIRED' if retained else 'NO_STANDARD_FACT_CANDIDATES')
        except Exception as error:
            failures += 1
            # Do not persist exception messages: providers can echo request headers.
            issue(ticker, 'SEC_ACQUISITION', 'ACQUISITION_FAILED', type(error).__name__)
        finally:
            save('IN_PROGRESS')
    reviewable = {row['ticker'] for row in index if
                  row['eligible_on_model_date'] == 'Y' and row['is_inline_xbrl'] == '1' and
                  row['index_status'] == 'CANDIDATE_IDENTITY_UNVERIFIED'}
    if reviewable:
        target_summary.update(build_targets(folder / 'filing_index.csv',
                                           folder / 'filing_targets.csv',
                                           folder / 'filing_targets_audit.csv',
                                           allowed_statuses=frozenset({'CANDIDATE_IDENTITY_UNVERIFIED'})))
    else:
        _write_csv(folder / 'filing_targets.csv', [],
                   ['model_date', 'ticker', 'accession_number', 'history_sequence_status'])
        _write_csv(folder / 'filing_targets_audit.csv', [],
                   ['model_date', 'ticker', 'target_history_status', 'review_note'])
    for issuer in issuers:
        if issuer['ticker'] not in reviewable:
            issue(issuer['ticker'], 'FILING_TARGETS', 'NO_ELIGIBLE_INLINE_FILING')
    return save('INCOMPLETE' if failures else 'CANDIDATES_ACQUIRED_NOT_SCORE_READY')

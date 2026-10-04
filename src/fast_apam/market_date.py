"""Resolve customer dates to completed NYSE cash-equity sessions.

Bundled calendar: 2023-2028, including the 2025 Carter closure.
Sources and update requirements are recorded in docs/market-dates.md.
This does not change the financial engine's filing processing buffer.
"""
import re
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo
from .engine.sec_filing_index import nyse_holidays

EASTERN = ZoneInfo('America/New_York')
CALENDAR_VERSION = 'NYSE-2023-2028-v1'
FIRST_DAY = date(2023, 1, 1)
LAST_DAY = date(2028, 12, 31)
EXTRA_CLOSURES = {date(2025, 1, 9)}
EARLY_CLOSES = {date.fromisoformat(value) for value in (
    '2023-07-03', '2023-11-24',
    '2024-07-03', '2024-11-29', '2024-12-24',
    '2025-07-03', '2025-11-28', '2025-12-24',
    '2026-11-27', '2026-12-24',
    '2027-11-26', '2028-07-03', '2028-11-24',
)}


def session_close(day):
    if not FIRST_DAY <= day <= LAST_DAY:
        raise ValueError('Market calendar supports 2023-2028; update the calendar before using other dates.')
    if day.weekday() >= 5 or day in nyse_holidays(day.year) or day in EXTRA_CLOSURES:
        return None
    return datetime.combine(day, time(13 if day in EARLY_CLOSES else 16), EASTERN)


def resolve_model_date(requested, *, now=None):
    now = now if now is not None else datetime.now(EASTERN)
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError('Date resolution requires a timezone-aware clock.')
    local_now = now.astimezone(EASTERN)
    if requested == 'latest':
        day = local_now.date()
    else:
        if not isinstance(requested, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', requested):
            raise ValueError('Model date must use YYYY-MM-DD or latest.')
        day = date.fromisoformat(requested)
        if day > local_now.date():
            raise ValueError('Cannot use a future model date; use latest for the most recent completed session.')
    requested_day = day
    skipped = []
    while True:
        close = session_close(day)
        if close is not None and close <= local_now:
            break
        reason = ('WEEKEND' if day.weekday() >= 5 else
                  'MARKET_HOLIDAY' if close is None else 'SESSION_NOT_CLOSED')
        skipped.append({'date': day.isoformat(), 'reason': reason})
        day -= timedelta(days=1)
    return {
        'requested_date': requested,
        'requested_calendar_date': requested_day.isoformat(),
        'effective_model_date': day.isoformat(),
        'adjusted': day != requested_day,
        'adjustment_reason': skipped[0]['reason'] if skipped else 'NONE',
        'skipped_dates': skipped,
        'session_close_eastern': close.isoformat(),
        'resolved_at_eastern': local_now.isoformat(),
        'calendar_version': CALENDAR_VERSION,
    }

"""Select an audited ETF peer batch and reuse SEC candidate acquisition."""
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

from .etf_proxy import parse_holdings
from .preparation import prepare


def prepare_cohort_batch(proxy_folder, output, sector, batch_number=1,
                         batch_size=25, *, history_start=None, plan_only=False,
                         acquisition=prepare, progress=None):
    proxy = Path(proxy_folder)
    manifest = json.loads((proxy / 'etf_proxy_manifest.json').read_text(encoding='utf-8'))
    cohort_file = proxy / 'etf_proxy_cohort.csv'
    payload = cohort_file.read_bytes()
    if hashlib.sha256(payload).hexdigest() != manifest.get('cohort_sha256'):
        raise ValueError('ETF cohort checksum mismatch; rebuild the proxy')
    source = Path(manifest['source_path'])
    raw = source.read_bytes()
    if hashlib.sha256(raw).hexdigest() != manifest['source_sha256']:
        raise ValueError('ETF source checksum mismatch')
    as_of, _ = parse_holdings(raw)
    if as_of.isoformat() != manifest['holdings_as_of_date']:
        raise ValueError('ETF source date mismatch')
    with cohort_file.open(newline='', encoding='utf-8-sig') as handle:
        rows = list(csv.DictReader(handle))
    if not rows or len(rows) != manifest['cohort_size']:
        raise ValueError('ETF cohort count mismatch')
    if len({row['ticker'] for row in rows}) != len(rows):
        raise ValueError('ETF cohort contains duplicate tickers')
    if dict(Counter(row['sector'] for row in rows)) != manifest['sector_counts']:
        raise ValueError('ETF sector counts mismatch')
    for row in rows:
        if (row['model_date'] != manifest['model_date'] or
                row['holdings_as_of_date'] != as_of.isoformat() or
                row['source_sha256'] != manifest['source_sha256'] or
                row['membership_basis'] != 'IVV_HOLDINGS_PROXY' or
                row['classification_basis'] != 'IVV_SPONSOR_SECTOR_PROXY'):
            raise ValueError('ETF cohort lineage mismatch')
    selected_sector = [row for row in rows if row['sector'] == sector]
    if not selected_sector:
        raise ValueError('Requested sector has no ETF peer candidates')
    if not isinstance(batch_size, int) or not 1 <= batch_size <= 50:
        raise ValueError('Batch size must be between 1 and 50')
    count = (len(selected_sector) + batch_size - 1) // batch_size
    if not isinstance(batch_number, int) or not 1 <= batch_number <= count:
        raise ValueError(f'Batch number must be between 1 and {count}')
    start = (batch_number - 1) * batch_size
    chosen = selected_sector[start:start + batch_size]
    folder = Path(output)
    if folder.exists() and (not folder.is_dir() or any(folder.iterdir())):
        raise ValueError('Cohort batch output must be a new or empty folder')
    folder.mkdir(parents=True, exist_ok=True)
    universe = folder / 'batch_universe.csv'
    with universe.open('w', newline='', encoding='utf-8') as handle:
        writer = csv.writer(handle)
        writer.writerow(['ticker'])
        writer.writerows([[row['ticker']] for row in chosen])
    with (folder / 'batch_selection_audit.csv').open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]) + ['batch_status'])
        writer.writeheader()
        for row in rows:
            status = ('SELECTED_FOR_SEC_ACQUISITION' if row in chosen else
                      'OTHER_BATCH_SAME_SECTOR' if row['sector'] == sector else
                      'OTHER_SECTOR')
            writer.writerow(dict(row, batch_status=status))
    result = {'model_date': manifest['model_date'], 'sector': sector,
              'batch_number': batch_number, 'batch_count': count,
              'batch_size': batch_size, 'selected_ticker_count': len(chosen),
              'selected_tickers': [row['ticker'] for row in chosen],
              'proxy_cohort_size': len(rows), 'proxy_cohort_sha256': manifest['cohort_sha256'],
              'holdings_as_of_date': as_of.isoformat(),
              'holdings_source_sha256': manifest['source_sha256'],
              'batch_universe_sha256': hashlib.sha256(universe.read_bytes()).hexdigest(),
              'status': 'BATCH_PLANNED' if plan_only else 'SEC_ACQUISITION_IN_PROGRESS',
              'ready_to_score': False}
    report = folder / 'cohort_batch.json'
    report.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    if not plan_only:
        try:
            acquired = acquisition(universe, manifest['model_date'], folder / 'sec_candidates',
                                   history_start=history_start, progress=progress)
            result['sec_preparation_status'] = acquired['status']
            result['issuer_candidate_count'] = acquired['issuer_candidate_count']
            result['candidate_fact_count'] = acquired['candidate_fact_count']
            result['status'] = ('SEC_CANDIDATES_ACQUIRED_NOT_SCORE_READY' if
                                acquired['status'] == 'CANDIDATES_ACQUIRED_NOT_SCORE_READY'
                                else 'SEC_ACQUISITION_INCOMPLETE')
        except Exception as error:
            result['status'] = 'SEC_ACQUISITION_FAILED'
            result['error_type'] = type(error).__name__
            report.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
            raise
        report.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    return result

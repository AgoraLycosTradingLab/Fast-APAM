"""Offline validation of customer input syntax, not issuer or peer eligibility."""
from .market_date import resolve_model_date
from .universe import read_universe


def check_setup(universe_path, model_date):
    resolution = resolve_model_date(model_date)
    model_date = resolution['effective_model_date']
    request = read_universe(universe_path)
    tickers = request['requested_tickers']
    return {
        'setup_status': 'INPUT_FORMAT_VALID',
        'model_date': model_date,
        'date_resolution': resolution,
        'requested_ticker_count': len(tickers),
        'requested_tickers': tickers,
        'universe_sha256': request['input_sha256'],
        'data_source': 'SEC',
        'credential_required_for_this_check': False,
        'network_requests_made': False,
        'issuer_identity_verified': False,
        'dated_universe_eligibility_verified': False,
        'peer_coverage_validated': False,
        'ready_to_score': False,
        'next_step': 'Use prepare-data to acquire SEC candidates from this file. Dated identities, membership, inline contexts, financial construction and peer coverage still require verification before scoring; automatic ticker-to-score preparation is incomplete.',
    }

"""Private, command-scoped SEC identification; no credential files are written."""
import getpass
import os
import sys
import warnings


def sec_user_agent():
    value = os.environ.get('APAM_SEC_USER_AGENT', '').strip()
    if not value:
        if not sys.stdin.isatty():
            raise ValueError('Set APAM_SEC_USER_AGENT through your environment for unattended downloads, or run in an interactive terminal for hidden entry.')
        try:
            # Refuse getpass's visible-input fallback when a terminal cannot hide entry.
            with warnings.catch_warnings():
                warnings.simplefilter('error', getpass.GetPassWarning)
                value = getpass.getpass('SEC organization and contact email (hidden, not saved): ').strip()
        except (getpass.GetPassWarning, EOFError, KeyboardInterrupt):
            raise ValueError('Private entry unavailable or cancelled. Configure APAM_SEC_USER_AGENT through your environment.') from None
    if not value or any(ord(c) < 32 or ord(c) == 127 for c in value):
        raise ValueError('SEC identification must be nonempty and contain no control characters.')
    return value

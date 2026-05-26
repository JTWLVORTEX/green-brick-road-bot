"""
Configuration loader for Green Brick Road bot.
Loads all secrets and config from .env file.
Validates that required values exist - fails loudly if anything
is missing so we catch problems at startup, not mid-run.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).parent.parent
load_dotenv(PROJECT_ROOT / '.env')


def _required(key: str) -> str:
    """Get an env var, raise clearly if missing."""
    value = os.getenv(key)
    if not value:
        raise ValueError(
            f"Missing required environment variable: {key}\n"
            f"Check your .env file at {PROJECT_ROOT / '.env'}"
        )
    return value


# Google Places
GOOGLE_PLACES_API_KEY = _required('GOOGLE_PLACES_API_KEY')

# Google Sheets
GOOGLE_SHEET_ID = _required('GOOGLE_SHEET_ID')
GOOGLE_OAUTH_CREDENTIALS_PATH = PROJECT_ROOT / _required('GOOGLE_OAUTH_CREDENTIALS_PATH')
GOOGLE_OAUTH_TOKEN_PATH = PROJECT_ROOT / _required('GOOGLE_OAUTH_TOKEN_PATH')

# Apollo
APOLLO_API_KEY = _required('APOLLO_API_KEY')

# Sanity check: confirm OAuth credentials file exists
if not GOOGLE_OAUTH_CREDENTIALS_PATH.exists():
    raise FileNotFoundError(
        f"OAuth credentials file not found at {GOOGLE_OAUTH_CREDENTIALS_PATH}\n"
        f"Make sure you copied your downloaded OAuth JSON to this location."
    )

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

# Hunter.io
HUNTER_API_KEY = _required('HUNTER_API_KEY')

# --- Railway support: write OAuth JSON from env vars to files ---
# On Railway, the credential files don't exist on disk. Instead the
# JSON contents are provided via env vars. Write them to the expected
# file paths so the rest of the code works unchanged. Locally, these
# env vars are absent and the existing local files are used.
def _write_env_json_to_file(env_var_name, destination):
    value = os.getenv(env_var_name)
    if not value:
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(value, encoding="utf-8")

_write_env_json_to_file("GOOGLE_OAUTH_CREDENTIALS_JSON", GOOGLE_OAUTH_CREDENTIALS_PATH)
_write_env_json_to_file("GOOGLE_OAUTH_TOKEN_JSON", GOOGLE_OAUTH_TOKEN_PATH)
# --- end Railway support ---

# Sanity check: confirm OAuth credentials file exists
if not GOOGLE_OAUTH_CREDENTIALS_PATH.exists():
    raise FileNotFoundError(
        f"OAuth credentials file not found at {GOOGLE_OAUTH_CREDENTIALS_PATH}\n"
        f"Make sure you copied your downloaded OAuth JSON to this location."
    )

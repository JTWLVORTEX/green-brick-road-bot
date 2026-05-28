"""
Google Sheets API client.
Reads existing leads (for dedup) and appends new ones.
Handles OAuth flow on first run.
"""
import os
from pathlib import Path
from typing import List, Dict, Set
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from src.config import (
    GOOGLE_SHEET_ID,
    GOOGLE_OAUTH_CREDENTIALS_PATH,
    GOOGLE_OAUTH_TOKEN_PATH,
)

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
SHEET_RANGE = 'Sheet1!A:K'  # 11 columns: A through K

# Schema column order must match Google Sheet exactly
SCHEMA_COLUMNS = [
    'name', 'email', 'company', 'domain', 'role', 'location',
    'source', 'date_found', 'status', 'notes', 'story_score',
]


def _get_credentials() -> Credentials:
    """Get valid OAuth credentials, triggering browser auth if needed."""
    creds = None
    token_path = Path(GOOGLE_OAUTH_TOKEN_PATH)

    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # Never attempt a browser flow on Railway (no display)
            if os.getenv("RAILWAY_ENVIRONMENT"):
                raise RuntimeError(
                    "Google OAuth token is missing or invalid on Railway. "
                    "Regenerate token.json locally by running the bot on your "
                    "computer, then paste its contents into the Railway variable "
                    "GOOGLE_OAUTH_TOKEN_JSON."
                )
            flow = InstalledAppFlow.from_client_secrets_file(
                str(GOOGLE_OAUTH_CREDENTIALS_PATH), SCOPES
            )
            creds = flow.run_local_server(port=0)
        token_path.parent.mkdir(parents=True, exist_ok=True)
        with open(token_path, 'w') as token:
            token.write(creds.to_json())
    return creds


def _get_service():
    return build('sheets', 'v4', credentials=_get_credentials())


def get_existing_emails() -> Set[str]:
    """
    Read all existing emails from the sheet.
    Returns a set of lowercased emails for dedup checks.
    """
    service = _get_service()
    result = service.spreadsheets().values().get(
        spreadsheetId=GOOGLE_SHEET_ID,
        range=SHEET_RANGE,
    ).execute()

    rows = result.get('values', [])
    if not rows:
        return set()

    headers = rows[0]
    try:
        email_col_idx = headers.index('Email')
    except ValueError:
        print("WARNING: No 'Email' column header in sheet")
        return set()

    emails = set()
    for row in rows[1:]:
        if len(row) > email_col_idx:
            email = row[email_col_idx].strip().lower()
            if email:
                emails.add(email)
    return emails


def append_leads(leads: List[Dict]) -> int:
    """
    Append new leads to the sheet. Skips duplicates.

    Args:
        leads: List of dicts with keys matching SCHEMA_COLUMNS

    Returns:
        Number of leads actually appended (after dedup)
    """
    if not leads:
        return 0

    existing_emails = get_existing_emails()
    new_leads = [
        lead for lead in leads
        if lead.get('email', '').strip()
        and lead.get('email', '').strip().lower() not in existing_emails
    ]

    if not new_leads:
        print("  No new leads to append (all duplicates or empty)")
        return 0

    rows = [[lead.get(col, '') for col in SCHEMA_COLUMNS] for lead in new_leads]

    service = _get_service()
    service.spreadsheets().values().append(
        spreadsheetId=GOOGLE_SHEET_ID,
        range=SHEET_RANGE,
        valueInputOption='USER_ENTERED',
        insertDataOption='INSERT_ROWS',
        body={'values': rows},
    ).execute()
    return len(new_leads)


if __name__ == "__main__":
    print("Testing Sheets connection...")
    print("(First run will open a browser for OAuth - please authorize)")
    emails = get_existing_emails()
    print(f"Found {len(emails)} existing emails in sheet")
    print(f"Sample (first 3): {list(emails)[:3]}")

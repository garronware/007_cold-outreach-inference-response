"""
Shared Google OAuth2 helper for Gmail and Sheets APIs.

Handles credential loading, token refresh, and the initial OAuth flow.
Token is cached in token.json after first authorization.
"""

from __future__ import annotations

import os

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

BASE_DIR = os.path.join(os.path.dirname(__file__), "..")
CREDENTIALS_FILE = os.path.join(BASE_DIR, "gmail-0Auth-credentials.json")
TOKEN_FILE = os.path.join(BASE_DIR, "token.json")

# Scopes needed across all tools
SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.labels",
    "https://www.googleapis.com/auth/gmail.settings.basic",
    "https://www.googleapis.com/auth/spreadsheets",
]


def get_credentials() -> Credentials:
    """
    Get valid Google OAuth2 credentials.

    On first run, opens a browser for authorization.
    Subsequent runs use the cached token.json.
    """
    creds = None

    # Try loading existing token
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    # Refresh or get new credentials
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CREDENTIALS_FILE):
                raise FileNotFoundError(
                    f"Credentials file not found: {CREDENTIALS_FILE}\n"
                    "Download it from Google Cloud Console > APIs & Services > Credentials"
                )
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)

        # Cache the token
        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())

    return creds

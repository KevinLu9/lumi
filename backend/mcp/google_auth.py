"""Shared Google OAuth for Lumi's Google modules (Calendar, Gmail, …).

One consent covers every scope below; the token caches to backend/.google_token.json
so the calendar and gmail tools work without re-authenticating. This is NOT a tool
module (registry skips it) — it's the auth helper the Google tool modules import.

Setup (once, from the repo root):
  1. Create an OAuth client (type "Desktop app") in Google Cloud Console and enable
     the Calendar API and Gmail API.
  2. Put GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET in .env.
  3. Run:  python -m backend.mcp.google_auth   (opens a browser to grant access)
"""

import os

from dotenv import load_dotenv

load_dotenv()

# All scopes requested in the single consent. Add to this list (and re-run auth)
# when introducing a new Google module, e.g. tasks or gmail.send.
SCOPES = [
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/gmail.readonly",
]

TOKEN_PATH = os.path.join(os.path.dirname(__file__), ".google_token.json")


def _client_config() -> dict:
    return {
        "installed": {
            "client_id": os.environ["GOOGLE_CLIENT_ID"],
            "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"],
        }
    }


class NotConnectedError(RuntimeError):
    """Raised when there is no usable cached Google token."""


def get_credentials():
    """Return valid cached credentials, refreshing if needed. Raises
    NotConnectedError if the user hasn't run the one-time auth yet."""
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request

    creds = None
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        _write(creds)
    if not creds or not creds.valid:
        raise NotConnectedError(
            "Google account isn't connected. Run `python -m backend.mcp.google_auth` once."
        )
    return creds


def service(api: str, version: str):
    """Build a Google API client for the given service, e.g. service('calendar', 'v3')."""
    from googleapiclient.discovery import build

    return build(api, version, credentials=get_credentials(), cache_discovery=False)


def _write(creds) -> None:
    tmp = TOKEN_PATH + ".tmp"
    with open(tmp, "w") as f:
        f.write(creds.to_json())
    os.replace(tmp, TOKEN_PATH)


def authorize() -> None:
    """Run the one-time interactive consent flow and cache the token."""
    import sys

    missing = [k for k in ("GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET") if not os.environ.get(k)]
    if missing:
        print(f"Error: missing env vars: {', '.join(missing)}. Add them to .env and re-run.")
        sys.exit(1)
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError:
        print("Missing dependency. Run: .venv/bin/pip install google-auth-oauthlib")
        sys.exit(1)

    flow = InstalledAppFlow.from_client_config(_client_config(), SCOPES)
    creds = flow.run_local_server(port=0)
    _write(creds)
    print(f"\nAuthenticated. Token cached at: {TOKEN_PATH}")
    print("Calendar and Gmail tools are ready.")


if __name__ == "__main__":
    authorize()

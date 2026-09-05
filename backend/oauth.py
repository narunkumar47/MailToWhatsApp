import os
from pathlib import Path

from google_auth_oauthlib.flow import Flow


# Allow HTTP for local development.
# DO NOT use this setting in production.
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"


# Project root
BASE_DIR = Path(__file__).resolve().parent.parent

WEB_CREDENTIALS_FILE = BASE_DIR / "web_credentials.json"


# Gmail permission
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly"
]


# Google OAuth redirect URI
REDIRECT_URI = "https://mailtowhatsapp.onrender.com/auth/callback"

def create_google_flow():
    """Create a Google OAuth flow for connecting Gmail."""

    flow = Flow.from_client_secrets_file(
        str(WEB_CREDENTIALS_FILE),
        scopes=SCOPES
    )

    flow.redirect_uri = REDIRECT_URI

    return flow
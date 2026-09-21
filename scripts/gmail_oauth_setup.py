"""
One-time local script: get a Gmail API refresh token for groundfit.in@gmail.com.

Prereqs (Google Cloud Console → same project as GroundFit):
  1) Enable "Gmail API"
  2) Credentials → Create OAuth client ID → type "Desktop app"
     (or Web with redirect http://localhost:8090/)
  3) OAuth consent screen → add scope gmail.send + add your Gmail as test user

Run (from repo root, venv on):
  pip install google-auth-oauthlib
  python scripts/gmail_oauth_setup.py

Sign in as groundfit.in@gmail.com when the browser opens.
Copy GMAIL_REFRESH_TOKEN into .env and Render.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Allow importing nothing from app — keep this script standalone
try:
    from google_auth_oauthlib.flow import InstalledAppFlow
except ImportError:
    print("Install: pip install google-auth-oauthlib")
    sys.exit(1)

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]
REPO = Path(__file__).resolve().parents[1]


def _load_dotenv() -> dict[str, str]:
    env_path = REPO / ".env"
    out: dict[str, str] = {}
    if not env_path.exists():
        return out
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def main() -> None:
    env = _load_dotenv()
    client_id = (
        os.environ.get("GMAIL_OAUTH_CLIENT_ID")
        or env.get("GMAIL_OAUTH_CLIENT_ID")
        or env.get("GOOGLE_CLIENT_ID")
        or ""
    ).strip()
    client_secret = (
        os.environ.get("GMAIL_OAUTH_CLIENT_SECRET")
        or env.get("GMAIL_OAUTH_CLIENT_SECRET")
        or env.get("GOOGLE_CLIENT_SECRET")
        or ""
    ).strip()

    if not client_id or not client_secret:
        print("Missing GMAIL_OAUTH_CLIENT_ID / GMAIL_OAUTH_CLIENT_SECRET")
        print("(or GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET in .env)")
        sys.exit(1)

    # Desktop-style client config for InstalledAppFlow
    client_config = {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"],
        }
    }

    print("Opening browser — sign in as groundfit.in@gmail.com and allow gmail.send")
    flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
    creds = flow.run_local_server(port=8090, prompt="consent", access_type="offline")

    if not creds.refresh_token:
        print("No refresh_token returned. Revoke app access at")
        print("  https://myaccount.google.com/permissions")
        print("then re-run with prompt=consent.")
        sys.exit(1)

    print("\n=== Add these to .env and Render ===\n")
    print("EMAIL_ENABLED=true")
    print("EMAIL_PROVIDER=gmail")
    print(f"GMAIL_SENDER=groundfit.in@gmail.com")
    print(f"SMTP_FROM=GroundFit <groundfit.in@gmail.com>")
    print(f"GMAIL_OAUTH_CLIENT_ID={client_id}")
    print(f"GMAIL_OAUTH_CLIENT_SECRET={client_secret}")
    print(f"GMAIL_REFRESH_TOKEN={creds.refresh_token}")
    print("\n(Optional) save full token JSON for backup:")
    out = REPO / "scripts" / "gmail_token.json"
    out.write_text(creds.to_json(), encoding="utf-8")
    print(f"Wrote {out} — do NOT commit this file.")


if __name__ == "__main__":
    main()

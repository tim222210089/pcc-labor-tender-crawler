from __future__ import annotations

import argparse
import json
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow


SCOPES = ["https://www.googleapis.com/auth/drive"]


def main() -> int:
    parser = argparse.ArgumentParser(description="Create GOOGLE_DRIVE_OAUTH_CONFIG for GitHub Actions.")
    parser.add_argument("client_json", help="Downloaded OAuth desktop client JSON path")
    parser.add_argument("--email", required=True, help="Google account email used for Drive uploads")
    parser.add_argument("--output", default="google_drive_oauth_config.json", help="output JSON path")
    args = parser.parse_args()

    flow = InstalledAppFlow.from_client_secrets_file(args.client_json, SCOPES)
    credentials = flow.run_local_server(port=0, prompt="consent", access_type="offline")
    if not credentials.refresh_token:
        raise RuntimeError("Google did not return a refresh_token. Re-run and approve the consent prompt.")

    config = {
        "client_id": credentials.client_id,
        "client_secret": credentials.client_secret,
        "refresh_token": credentials.refresh_token,
        "email": args.email,
    }
    output_path = Path(args.output)
    output_path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {output_path}")
    print("Paste the full file contents into the GitHub secret GOOGLE_DRIVE_OAUTH_CONFIG.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

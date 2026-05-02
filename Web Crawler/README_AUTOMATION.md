# PCC Labor Tender Automation

This folder contains the PCC labor tender crawler and the GitHub Actions automation support files.

## GitHub Secrets

Create these repository secrets under `Settings > Secrets and variables > Actions`.

- `GOOGLE_SERVICE_ACCOUNT_JSON`: the full Google service account JSON key.
- `GOOGLE_DRIVE_FOLDER_ID`: the Drive folder ID where Excel files should be uploaded.
- `LINE_CHANNEL_ACCESS_TOKEN`: LINE Messaging API channel access token.
- `LINE_USER_ID`: your LINE user ID. The bot can push only to users who added the official account.
- `GMAIL_NOTIFY_TO`: email address for failure and weekly summary messages.
- `GMAIL_CLIENT_OR_SERVICE_CONFIG`: Gmail notification configuration JSON.

## Gmail Config Options

Use Gmail API OAuth refresh token:

```json
{
  "type": "gmail_oauth",
  "client_id": "YOUR_CLIENT_ID",
  "client_secret": "YOUR_CLIENT_SECRET",
  "refresh_token": "YOUR_REFRESH_TOKEN",
  "sender": "your-address@gmail.com"
}
```

Or use SMTP with an app password:

```json
{
  "type": "smtp",
  "host": "smtp.gmail.com",
  "port": 587,
  "use_tls": true,
  "username": "your-address@gmail.com",
  "password": "YOUR_APP_PASSWORD",
  "sender": "your-address@gmail.com"
}
```

## Local Checks

```powershell
python -m pip install -r requirements.txt
python -m unittest -v
python export_pcc_labor_tenders.py --date today --output pcc_labor_tenders_today.xlsx
```

## Manual GitHub Actions Run

After pushing the files and adding secrets, open the `Daily PCC Labor Tender Crawler` workflow in GitHub Actions and run it with `workflow_dispatch`.

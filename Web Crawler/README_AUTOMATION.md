# PCC Labor Tender Automation

This folder contains the PCC labor tender crawler and the GitHub Actions automation support files.

## GitHub Secrets

Create these repository secrets under `Settings > Secrets and variables > Actions`.

- `GOOGLE_DRIVE_OAUTH_CONFIG`: recommended for a personal Google Drive folder. JSON with `client_id`, `client_secret`, and `refresh_token`.
- `GOOGLE_SERVICE_ACCOUNT_JSON`: fallback service account JSON key. This works only when the account can write to storage, such as a Shared Drive; personal My Drive uploads should use `GOOGLE_DRIVE_OAUTH_CONFIG`.
- `GOOGLE_DRIVE_FOLDER_ID`: the Drive folder ID where Excel files should be uploaded.
- `LINE_CHANNEL_ACCESS_TOKEN`: LINE Messaging API channel access token.
- `LINE_USER_ID`: your LINE user ID. The bot can push only to users who added the official account.
- `GMAIL_NOTIFY_TO`: email address for failure and weekly summary messages.
- `GMAIL_CLIENT_OR_SERVICE_CONFIG`: Gmail notification configuration JSON.

## Gmail Config Options

## Google Drive OAuth Config

Use a personal Google OAuth refresh token for uploads to your own My Drive:

```json
{
  "client_id": "YOUR_CLIENT_ID",
  "client_secret": "YOUR_CLIENT_SECRET",
  "refresh_token": "YOUR_REFRESH_TOKEN",
  "email": "your-address@gmail.com"
}
```

`GOOGLE_DRIVE_OAUTH_CONFIG` takes priority over `GOOGLE_SERVICE_ACCOUNT_JSON` when both are present.

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

## External Scheduler

GitHub Actions native schedules can be delayed. For more reliable morning delivery, use cron-job.org to trigger the existing `workflow_dispatch` endpoint:

- Daily LINE Excel: Monday to Friday `06:45` Asia/Taipei
- Monday Gmail summary: Monday `07:00` Asia/Taipei

See `CRON_JOB_ORG_SETUP.md` for the GitHub token scope, request URL, headers, JSON bodies, and verification checklist.

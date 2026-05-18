# PCC Crawler Automation Context Summary

Use this file when opening a new Codex window/thread.

## Project

- Local repo root: `C:\Users\tim\Desktop\codex code`
- Main folder: `C:\Users\tim\Desktop\codex code\Web Crawler`
- GitHub repo: `https://github.com/tim222210089/pcc-labor-tender-crawler`
- Workflow file: `.github/workflows/daily-pcc-crawler.yml`
- Main automation script: `Web Crawler/run_daily_workflow.py`

## Current Workflow

The automation is already working end to end:

```text
GitHub Actions
-> PCC crawler
-> Excel output
-> Google Drive crawler folder
-> LINE latest Excel link
-> Gmail weekly summary / failure notification
```

Confirmed working:

- GitHub Actions manual run succeeded.
- Google Drive received the generated Excel.
- LINE received `PCC 勞務標案 Excel 已更新` with the Drive link.
- Gmail weekly summary test succeeded.

## Schedule

GitHub Actions uses UTC cron.

Current local fix in progress:

- On `2026-05-05 09:44` Taiwan time, GitHub API showed no schedule run for `2026-05-05`.
- The workflow was still `active`, `master` was the default branch, and remote `master` contained the `08:07` schedule.
- Latest schedule runs were still only run `8` and `9` from `2026-05-04`, both on commit `9674ec8`, before the `08:07` commit.
- The workflow has been aligned with the external scheduler plan:
  - GitHub native fallback daily cron: `45 22 * * 0-4` (`06:45` Asia/Taipei weekdays)
  - GitHub native fallback Monday summary cron: `0 23 * * 0` (`07:00` Asia/Taipei Monday)
  - External scheduler target: cron-job.org daily `06:45` weekdays and Monday summary `07:00` Asia/Taipei
  - Setup guide: `Web Crawler/CRON_JOB_ORG_SETUP.md`
  - output file: `pcc_labor_tenders_YYYY-MM-DD.xlsx` using Taipei date
  - `run_daily_workflow.py --skip-if-drive-file-exists` skips LINE when the same file name already exists in Drive
- Validation after this change:
  - `python -m py_compile .\run_daily_workflow.py .\test_run_daily_workflow.py`
  - `python -m unittest -v`
  - result: `Ran 12 tests OK`

Previously deployed schedule:

- Weekdays, Taiwan time `08:07`
  - UTC cron: `7 0 * * 1-5`
- Monday Gmail weekly summary, Taiwan time `08:22`
  - UTC cron: `22 0 * * 1`

Reason for `08:07` instead of `08:00`:

- On `2026-05-04`, the scheduled GitHub Actions run arrived around Taiwan time `11:56` / `12:11`.
- The workflow was originally scheduled at the top of the hour.
- GitHub schedule events can be delayed during high load, especially around the top of the hour.
- The schedule was moved off the exact hour to reduce delay risk.

Latest schedule commit:

- `01b6f23 Avoid top-of-hour crawler schedule`

## GitHub Secrets

Configured repository secrets:

```text
GOOGLE_DRIVE_OAUTH_CONFIG
GOOGLE_DRIVE_FOLDER_ID
GOOGLE_SERVICE_ACCOUNT_JSON
LINE_CHANNEL_ACCESS_TOKEN
LINE_USER_ID
GMAIL_CLIENT_OR_SERVICE_CONFIG
GMAIL_NOTIFY_TO
```

Important Drive detail:

- Service account upload failed because service accounts do not have personal My Drive storage quota.
- The workflow now prefers `GOOGLE_DRIVE_OAUTH_CONFIG` for Google Drive upload.
- `GOOGLE_SERVICE_ACCOUNT_JSON` remains as fallback only.

## Local Sensitive Files

These files are ignored and should not be committed:

```text
oauth_client*.json
google_drive_oauth_config.json
service account JSON files
```

They can be deleted locally after confirming the GitHub Secrets are set.

## Validation Commands

Use this Python executable on this Windows machine:

```powershell
& "C:\Users\tim\AppData\Local\Programs\Python\Python312\python.exe" -m unittest -v
```

Known successful result:

```text
Ran 11 tests
OK
```

## If Future Runs Are Late

First check actual GitHub Actions run times:

```powershell
$uri = 'https://api.github.com/repos/tim222210089/pcc-labor-tender-crawler/actions/workflows/daily-pcc-crawler.yml/runs?per_page=20'
$data = Invoke-RestMethod -Uri $uri -Headers @{ 'User-Agent' = 'codex-debug' }
$data.workflow_runs | Select-Object run_number,event,conclusion,created_at,run_started_at,updated_at,html_url | Format-Table -AutoSize
```

If GitHub still delays scheduled runs significantly:

- Keep the current workflow logic.
- Consider using an external scheduler to trigger `workflow_dispatch`.

## Do Not Break

When editing the workflow:

- Keep `workflow_dispatch`.
- Update both the cron string and the human-facing Taipei-time comment.
- If changing the Monday weekly summary cron, also update the `github.event.schedule` comparison in the `Decide weekly summary` step.

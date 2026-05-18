# cron-job.org Setup for PCC Crawler

This setup uses cron-job.org only as the scheduler. GitHub Actions still runs the existing workflow through `workflow_dispatch`.

## 1. Create GitHub Token

Create a fine-grained personal access token:

- Resource owner: `tim222210089`
- Repository access: only `pcc-labor-tender-crawler`
- Repository permissions: `Actions` = `Read and write`
- Expiration: 90 or 180 days

GitHub API requirement: the workflow dispatch endpoint needs `Actions: write` for fine-grained tokens.

## 2. Request Settings

Use these values for the cron-job.org daily job:

- URL: `https://api.github.com/repos/tim222210089/pcc-labor-tender-crawler/actions/workflows/daily-pcc-crawler.yml/dispatches`
- Method: `POST`
- Timezone: `Asia/Taipei`
- Headers:
  - `Accept: application/vnd.github+json`
  - `Authorization: Bearer YOUR_GITHUB_FINE_GRAINED_TOKEN`
  - `X-GitHub-Api-Version: 2022-11-28`
  - `Content-Type: application/json`

## 3. Daily LINE Job

- Name: `PCC Daily Excel`
- Schedule: Monday to Friday at `06:45`
- Body:

```json
{"ref":"master","inputs":{}}
```

Expected result:

- cron-job.org request succeeds.
- GitHub Actions shows a new `workflow_dispatch` run.
- LINE receives the Excel link.

## 4. Weekly Summary Job

The weekly Gmail summary is no longer used. Disable or delete the cron-job.org job named `PCC Weekly Summary` if it still exists.

## 5. GitHub Native Fallback

The workflow keeps a GitHub native weekday fallback schedule for now:

Keep:

- `workflow_dispatch`
- Weekday `06:45` Asia/Taipei fallback schedule
- Taipei-date output filename
- `--skip-if-drive-file-exists`

This keeps the daily automation running even if cron-job.org is unavailable. The Drive duplicate check prevents duplicate LINE sends for the same date.

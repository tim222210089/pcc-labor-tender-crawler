# cron-job.org Setup for PCC Crawler

This setup uses cron-job.org only as the scheduler. GitHub Actions still runs the existing workflow through `workflow_dispatch`.

## 1. Create GitHub Token

Create a fine-grained personal access token:

- Resource owner: `tim222210089`
- Repository access: only `pcc-labor-tender-crawler`
- Repository permissions: `Actions` = `Read and write`
- Expiration: 90 or 180 days

GitHub API requirement: the workflow dispatch endpoint needs `Actions: write` for fine-grained tokens.

## 2. Common Request Settings

Use these values for both cron-job.org jobs:

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
{"ref":"master","inputs":{"send_weekly_summary":"false"}}
```

Expected result:

- cron-job.org request succeeds.
- GitHub Actions shows a new `workflow_dispatch` run.
- LINE receives the Excel link.

## 4. Monday Gmail Summary Job

- Name: `PCC Weekly Summary`
- Schedule: Monday at `07:00`
- Body:

```json
{"ref":"master","inputs":{"send_weekly_summary":"true"}}
```

Expected result:

- cron-job.org request succeeds.
- GitHub Actions shows a new `workflow_dispatch` run.
- Gmail receives the weekly summary.

## 5. After Both Jobs Are Verified

Remove the `schedule:` block from `.github/workflows/daily-pcc-crawler.yml`.

Keep:

- `workflow_dispatch`
- Taipei-date output filename
- `--skip-if-drive-file-exists`

This prevents delayed GitHub native schedules from running after cron-job.org has already triggered the same daily file.

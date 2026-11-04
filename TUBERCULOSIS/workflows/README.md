# n8n workflows (WF-01 .. WF-06)

Importable n8n workflows. They only call the FastAPI backend; business rules, role checks and the
audit log stay in the API. All workflows are exported inactive (`active: false`). Nothing here has
been executed against a live n8n instance (not available locally); JSON structure and node wiring
were checked programmatically only.

| File | Trigger | What it does |
|---|---|---|
| `WF-01-import-metadata-batches.json` | daily 02:00 + manual | Imports metadata/image batches from `IMPORT_SOURCE_URL`; without it, creates 3 flagged DEMO cases (no images). Calls `POST /cases` and `POST /cases/{id}/image`. |
| `WF-02-quality-control.json` | hourly | `GET /ops/qc` (duplicates by SHA-256, cases without image, failed QC); logs `wf_qc_findings` / `wf_qc_clean` via `POST /ops/events`. |
| `WF-03-schedule-inferences.json` | every 15 min + header-auth webhook `tb-run-pending` | Lists `status=image_uploaded` cases and runs `POST /cases/{id}/inference` for each. |
| `WF-04-operational-alerts.json` | every 30 min | Alerts on technical failures and cases pending review (counts only, no ids) via email or webhook. |
| `WF-05-management-report.json` | Mondays 07:00 | Exports `management.pdf` (last 7 days) and distributes it via email or webhook. |
| `WF-06-events-model-monitoring.json` | daily 06:00 | Digest of the last 24 h of audit events. Model performance is logged only when `scientific.available` is true (reference labels exist); otherwise a "skipped" event is logged. |

HTTP nodes use retry on fail (3 tries, 2 s wait) and failures of per-item calls do not stop the batch.

## Import

1. n8n UI: Workflows > Import from file, for each JSON. Or CLI: `n8n import:workflow --separate --input=workflows/`.
2. Create the credentials by name (placeholders in the JSON use id `REPLACE_WITH_CREDENTIAL_ID`):
   - `TB SMTP` (SMTP) - only if `ALERT_CHANNEL=email` (WF-04, WF-05).
   - `TB webhook header auth` (Header Auth) - protects the WF-03 on-demand webhook.
3. Set the environment variables below on the n8n process and allow env access in nodes
   (`N8N_BLOCK_ENV_ACCESS_IN_NODE=false`).
4. Activate workflows after a manual test run.

## Service token

The backend has a `service` role (case read/create/upload, run inference, dashboard, report export,
audit read, `POST /ops/events`; no review, no user management). Generate a long-lived token:

```bash
cd backend && python -m app.service_token --days 90     # prints the token once
```

Store it only as `N8N_API_TOKEN`. Revoke by deactivating the `n8n-service@system.local` user.

## Environment variables

| Variable | Required | Meaning |
|---|---|---|
| `TB_API_URL` | yes | Backend base URL, e.g. `http://backend:8000` |
| `N8N_API_TOKEN` | yes | Bearer token from `app.service_token` |
| `IMPORT_SOURCE_URL` / `IMPORT_SOURCE_TOKEN` | no | Authorized source returning a JSON array of `{institution, notes, image_url?}`. Empty = demo data. |
| `ALERT_CHANNEL` | no | `email` or anything else (= webhook). Default webhook. |
| `ALERT_WEBHOOK_URL` | for webhook | Slack/Teams/generic endpoint; WF-04 posts `{text}`, WF-05 posts the PDF as multipart `file`. |
| `ALERT_EMAIL_FROM` / `ALERT_EMAIL_TO` | for email | Sender and recipients. |
| `ALERT_PENDING_REVIEW_MAX` | no | Default 10 |
| `ALERT_FAILURES_MAX` | no | Default 0 |

## Backend endpoints added for these workflows

`GET /ops/pending-review`, `GET /ops/qc`, `POST /ops/events` (audit module `ops`, events `wf_*`).
Tests: `backend/tests/test_ops.py`.

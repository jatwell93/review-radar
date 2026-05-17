# n8n Workflow Setup

## Import
1. n8n Cloud → Workflows → Import from file → select `weekly-reanalysis-workflow.json`

## Required Credentials
Create these in n8n Cloud Settings → Credentials:

| Name | Type | Fields |
|------|------|--------|
| Review Radar N8N Secret | HTTP Header Auth | Name: `X-N8N-Secret` / Value: your N8N_WEBHOOK_SECRET from Render |
| Review Radar SMTP | SMTP | Host/port/username/password for SendGrid, Gmail, etc. |

## Required Environment Variable
n8n Cloud Settings → Variables:
- `RENDER_API_BASE_URL` = `https://review-radar-api.onrender.com` (your Render service URL)

## Email From Address
Update the `fromEmail` field in the "Send Weekly Report" node to your verified sender address.
**This is a deploy-time activation blocker** — the workflow will fail to send if this is left as the placeholder value.

## Schedule
Default: weekly, Monday 8am UTC. Edit the Schedule Trigger node to change.

## Manual Test
Open the workflow → click "Test workflow" to trigger immediately for all eligible users.

## Node typeVersion Compatibility
The typeVersions in the JSON are pinned to n8n Cloud at plan creation time. After importing, check each node for yellow version-mismatch warning icons. If present, open the node and click "Update" to match the installed version. Do not activate the workflow with version mismatches — parameter mapping may be silently wrong.

## Duplicate Run Risk
If the workflow is manually triggered while the weekly schedule is also active, eligible users will receive multiple emails in one week and multiple analysis rows will be inserted. To test safely: keep the workflow inactive (toggle off) until manual testing is complete, then activate once verified. n8n's execution history serves as the audit trail for identifying duplicate runs.

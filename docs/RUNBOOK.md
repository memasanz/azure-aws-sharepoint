# Runbook: cut over from ROPC to the secretless APIM path (Sprint B4)

Operational guide to move the production Lambda off the username/password (ROPC)
credential and retire it. Assumes Sprints B0–B3 are green.

## Pre-cutover checklist

- [ ] Azure side deployed (`infra/azure/main.bicep`) and APIM provisioned.
- [ ] `identity-pool-id` and `allowed-cognito-sub` named values set to real values.
- [ ] Managed identity granted **read** on the target site/library
      (`scripts/grant_selected_read.py` or the portal).
- [ ] B2 negative tests pass against the live endpoint (`tests/`).
- [ ] Monitoring deployed (`infra/azure/monitoring.bicep`).

## Cutover steps

1. **Deploy the reader Lambda** (`lambda/reader/`) alongside the existing one,
   pointing at the APIM `readEndpoint`. Do **not** delete the ROPC Lambda yet.
2. **Shadow test** in non-prod: confirm the reader returns the same content the
   ROPC path returns for the same folders.
3. **Flip traffic** to the reader Lambda (alias/router or config switch).
4. **Watch** the APIM `failed-requests` alert and gateway logs for 401/403 spikes.
5. **Soak** for an agreed window (e.g., 24–48h) with rollback ready.
6. **Decommission ROPC**:
   - Remove the username/password from wherever it's stored.
   - Disable/delete the old Lambda and its Graph app/user credential.
   - Confirm the SharePoint user/password can no longer authenticate.

## Rollback

- Re-point the router to the ROPC Lambda (kept intact until soak passes).
- No Azure changes needed to roll back; the APIM path is additive.

## Steady-state operations

| Task | How |
|---|---|
| Grant access to a new directory | Owner uses the portal (`portal/`) |
| Review / revoke access | Portal grants list, or `scripts/recertify_grants.py` |
| Recertify quarterly | `python scripts/recertify_grants.py --db <grants.db> --max-age-days 90` |
| Rotate the trust pin | Update `allowed-cognito-sub` named value; redeploy |
| Investigate failures | APIM gateway logs in the Log Analytics workspace |

## Notes

- Graph/SharePoint audit shows access as **APIM's managed identity** (spec §9).
  Capture per-caller context from APIM gateway logs if finer attribution is needed.
- Whole-site grants remain **out of scope** (spec §13.6) — directory/library only.

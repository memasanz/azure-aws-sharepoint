# Self-Service Access Portal (Sprint B3)

The UI SharePoint never gave you: lets a site **Owner** sign in and grant the
**pinned APIM managed identity** read access to a site they own — no admin, no
ticket, no secret (spec §13).

```
portal/
  backend/   FastAPI — pins the MI target, enforces read-only, records/revokes grants
  frontend/  React + MSAL (PKCE) — sign in, find owned sites, grant / revoke
```

## Guardrails (enforced in code)

1. **Pinned target** — backend only ever grants to `APIM_MI_APP_ID`.
2. **Read-only** — only the `read` role is requested.
3. **Ownership** — grants run as the signed-in user; Graph rejects (403) unless
   they own the site.
4. **Audit + revoke** — every grant is recorded in SQLite and is revocable.

## Run the backend

```bash
cd backend
python -m venv .venv && . .venv/Scripts/activate      # (Windows: .venv\Scripts\Activate.ps1)
pip install -r requirements.txt
cp .env.example .env      # fill APIM_MI_APP_ID + TENANT_ID
uvicorn app.main:app --reload --port 8000
```

> `APIM_MI_APP_ID` is the APIM managed identity's **application (client) id**.
> Resolve it from the Bicep `apimPrincipalId` output:
> `az ad sp show --id <apimPrincipalId> --query appId -o tsv`

## Run the frontend

```bash
cd frontend
npm install
# set VITE_CLIENT_ID, VITE_TENANT_ID, VITE_API_BASE (e.g. in .env.local)
npm run dev      # http://localhost:5173
```

## Entra app registration (portal)

- Platform: **SPA**, redirect URI `http://localhost:5173`.
- Delegated Graph permissions: `User.Read`, `Sites.Read.All`, `Sites.Selected`.
- Public client (PKCE) — **no client secret**.

## Gate (SPRINT-PLAN Sprint 3)

- ✅ Owner grants read via the portal; the reader Lambda then reads that site.
- ✅ Non-owners get a clear 403; no other app/role can be targeted.
- ✅ Grants are listed and revocable.

# Azure side — deploy guide

The Azure side is fully deployable on its own (the AWS side can follow). It
stands up API Management with a **system-assigned managed identity** and the
`validate-jwt → managed-identity → Graph` policy.

## Prerequisites

- Azure CLI (`az`) logged in: `az login`
- A resource group: `az group create -n rg-sharepoint-bridge -l eastus`
- Bicep (bundled with recent `az`)

## 1. Deploy APIM + policy

```bash
az deployment group create \
  --resource-group rg-sharepoint-bridge \
  --template-file main.bicep \
  --parameters main.bicepparam
```

> `identityPoolId` may stay as the placeholder for now — the gateway deploys
> fine. Update it (redeploy) once the AWS Cognito pool exists so `validate-jwt`
> checks the right `aud`.

Note the outputs: **`apimPrincipalId`**, **`gatewayUrl`**, **`readEndpoint`**.

> APIM (Developer SKU) can take ~30–45 min to provision the first time.

## 2. Grant the managed identity read on a SharePoint site

Run as a SharePoint admin or site Owner (uses your `az login`, no secret):

```bash
pip install -r ../../scripts/requirements.txt
python ../../scripts/grant_selected_read.py \
  --mi-principal-id <apimPrincipalId> \
  --site-hostname contoso.sharepoint.com \
  --site-path /sites/Engineering
```

Record the printed **site id** — the reader Lambda uses it as `SITE_ID`.

## 3. Smoke test (once the AWS side mints a token)

```bash
curl -H "Authorization: Bearer <cognito-jwt>" \
  "<readEndpoint>?siteId=<site-id>&path=SomeFolder"
```

Expect `200` + a Graph JSON listing for a valid token; `401` for an invalid one.

## What deploys here

| Resource | Purpose |
|---|---|
| `Microsoft.ApiManagement/service` | Gateway + **system-assigned managed identity** |
| `.../namedValues/identity-pool-id` | JWT `aud` the policy validates |
| `.../apis` `sharepoint` + operation `read-folder` | `GET /sharepoint/read` |
| `.../apis/policies` | validate-jwt → managed-identity → Graph (`apim/policy.xml`) |

Hardening (`sub` pinning, rate limits, logging) is added in Sprint B2; monitoring
in Sprint B4 (`monitoring.bicep`).

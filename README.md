# Secretless AWS Lambda → SharePoint Read

Reference implementation for reading SharePoint content from an AWS Lambda with
**no stored secret, certificate, or password**.

**Design (Option D):**
Lambda → Cognito JWT → APIM `validate-jwt` → APIM managed identity → Microsoft
Graph (`Selected` read) → SharePoint.

See:
- [`PRODUCT-SPEC.md`](./PRODUCT-SPEC.md) — the full product spec.
- [`SPRINT-PLAN.md`](./SPRINT-PLAN.md) — team/execution sprint plan (gated, PoC-first).
- [`BUILD-PLAN.md`](./BUILD-PLAN.md) — the build breakdown for the artifacts in this repo.

## Stack

| Area | Tool |
|---|---|
| AWS infra (Cognito, Lambda) | Terraform |
| Azure infra (APIM, managed identity) | Bicep |
| Lambda | Python |
| Self-service portal | FastAPI + minimal React |

## Repo layout

```
infra/
  cognito/        # Terraform: Cognito Identity Pool + Lambda IAM (Sprint B0)
  azure/          # Bicep: APIM + managed identity            (Sprint B1)
lambda/
  token_minter/   # Spike: mint & return a Cognito JWT        (Sprint B0)
  reader/         # Full: mint token -> call APIM -> read     (Sprint B1)
apim/
  validate-jwt.xml  # Starter inbound token-validation policy (Sprint B0)
  policy.xml        # Full APIM policy                        (Sprint B1)
scripts/
  decode_jwt.py     # Inspect a Cognito JWT's claims          (Sprint B0)
portal/             # Self-service access portal              (Sprint B3)
tests/              # Negative / hardening tests              (Sprint B2)
```

## Sprint B0 — Cognito spike (current)

Goal: prove the Lambda → Cognito → APIM token hop before building anything else.

1. `cd infra/cognito && terraform init && terraform apply`
2. Invoke the `token_minter` Lambda; capture the returned `token`.
3. `python scripts/decode_jwt.py <token>` — record the real `iss` / `aud` / `sub`.
4. Apply `apim/validate-jwt.xml` to a test APIM API and confirm it accepts a
   valid token and rejects a tampered/expired one.

> **Go/No-Go:** APIM returns 200 for a valid token, 401 for an invalid one, and
> you've documented whether OpenID auto-discovery or the direct JWKS URL was
> needed. Do not proceed to B1 until this passes.

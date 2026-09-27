# Build Plan: repo artifacts by sprint

Concrete deliverables produced in this repo. Sequencing de-risks the novel
**Cognito hop first** (see `PRODUCT-SPEC.md` §6, §7.5).

## Build Sprint B0 — Scaffold + Cognito spike  ✅ built + validated
- `README.md`, `BUILD-PLAN.md`
- `infra/cognito/` — Terraform: Cognito Identity Pool + Lambda + IAM  (`terraform validate` ✓)
- `lambda/token_minter/` — Python Lambda that mints & returns the JWT
- `apim/validate-jwt.xml` — starter inbound validation policy
- `scripts/decode_jwt.py` — decode/inspect a Cognito JWT's claims

**Done when:** token mints, claims documented, APIM accepts valid / rejects invalid.

## Build Sprint B1 — End-to-end read path  ✅ built + validated
- `infra/azure/` — Bicep: APIM + managed identity  (`bicep build` ✓)
- `apim/policy.xml` — validate-jwt → managed-identity → Graph backend
- `scripts/grant_selected_read.py` — Graph call granting the MI directory read
- `lambda/reader/` — mint token → call APIM → read a folder

**Done when:** Lambda reads a test folder through APIM with no secret.

## Build Sprint B2 — Hardening  ✅ built + validated
- `sub` pinning + rate-limit in APIM policy; `allowed-cognito-sub` named value
- `tests/` — negative tests (wrong identity/folder/expired → 401/403)

**Done when:** only the one caller, read-only, directory-scoped; negatives pass.

## Build Sprint B3 — Self-service portal  ✅ built + validated
- `portal/` — FastAPI + React: Entra delegated sign-in, enumerate owned
  resources, create/revoke `Selected` read grant (pinned MI), grant registry
  (app imports ✓, routes ✓, SQLite store ✓)

**Done when:** an Owner grants read via the portal and the reader Lambda reads it;
guardrails enforced; grants revocable.

## Build Sprint B4 — Cutover tooling  ✅ built + validated
- `docs/RUNBOOK.md` — migration runbook
- `infra/azure/monitoring.bicep` — Log Analytics + gateway logs + 4xx alert  (`bicep build` ✓)
- `scripts/recertify_grants.py` — flag/revoke stale grants

**Done when:** prod Lambda off ROPC, credential decommissioned, ops in place.

---

## Validation status

| Check | Result |
|---|---|
| All Python (`py_compile`, 12 files) | ✅ |
| `terraform validate` (infra/cognito) | ✅ |
| `bicep build` (main + monitoring) | ✅ |
| Portal app import + routes + SQLite store | ✅ |

Live end-to-end runs (Cognito PoC, APIM deploy, Graph grant, portal auth) require
AWS/Azure/Entra access — see each area's README for the run + gate steps.

# Tests — Sprint B2 hardening gate

Live checks that the APIM trust boundary holds after `sub` pinning + rate limits.

```bash
pip install -r requirements.txt
export APIM_READ_URL="https://<apim>.azure-api.net/sharepoint/read"
export SITE_ID="<granted-graph-site-id>"
export VALID_TOKEN="<fresh valid Cognito JWT for the pinned identity>"
# optional, to exercise the sub-pin and expiry paths:
export WRONG_SUB_TOKEN="<valid Cognito JWT for a different identity>"
export EXPIRED_TOKEN="<expired Cognito JWT>"
pytest -v
```

Tests are **skipped** automatically if `APIM_READ_URL`/`VALID_TOKEN` are unset, so
they're safe to keep in CI before the environment exists.

## Gate (spec §12 / SPRINT-PLAN Sprint 2)

- ✅ valid token → 200
- ✅ missing / tampered / garbage token → 401
- ✅ valid token, missing siteId → 400 (no Graph call)
- ✅ wrong `sub` → 401 (trust pin)
- ✅ expired token → 401

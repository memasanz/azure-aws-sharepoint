"""Configuration for the self-service access portal.

Secretless: the portal uses the signed-in user's delegated Microsoft Graph token
(acquired by the React SPA via MSAL + PKCE). There is NO client secret here.

The one identity the portal is ever allowed to grant to — the APIM managed
identity's application — is pinned server-side so the browser can never target an
arbitrary app (guardrail, spec §13.5).
"""

import os


class Settings:
    # The ONLY app the portal may grant access to (APIM MI application/client id).
    apim_mi_app_id: str = os.environ.get("APIM_MI_APP_ID", "REPLACE_WITH_APIM_MI_APP_ID")
    apim_mi_display_name: str = os.environ.get("APIM_MI_DISPLAY_NAME", "APIM SharePoint Reader")

    # The only role the portal may ever grant.
    allowed_role: str = "read"

    # Grant registry (audit).
    grant_db_path: str = os.environ.get("GRANT_DB_PATH", "grants.db")

    # CORS origin for the React dev server / hosted SPA.
    frontend_origin: str = os.environ.get("FRONTEND_ORIGIN", "http://localhost:5173")

    # Entra tenant (for informational endpoints; token is validated by audience).
    tenant_id: str = os.environ.get("TENANT_ID", "")


settings = Settings()

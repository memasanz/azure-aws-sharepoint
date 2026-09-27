"""Thin Microsoft Graph client using the signed-in user's delegated token.

All calls are made AS THE USER. A Selected grant therefore only succeeds when the
user is actually an Owner of the target site/library (Graph enforces this) — which
is exactly the ownership guardrail from spec §13.5.
"""

import requests

GRAPH = "https://graph.microsoft.com/v1.0"
_TIMEOUT = 30


def _headers(user_token: str) -> dict:
    return {"Authorization": f"Bearer {user_token}", "Content-Type": "application/json"}


def search_sites(user_token: str, query: str = "*") -> list[dict]:
    """List sites the user can see (they can only successfully GRANT on ones they own)."""
    resp = requests.get(
        f"{GRAPH}/sites",
        headers=_headers(user_token),
        params={"search": query},
        timeout=_TIMEOUT,
    )
    resp.raise_for_status()
    return [
        {"id": s["id"], "displayName": s.get("displayName", s.get("name", "")),
         "webUrl": s.get("webUrl", "")}
        for s in resp.json().get("value", [])
    ]


def list_libraries(user_token: str, site_id: str) -> list[dict]:
    """List document libraries (drives) in a site, for directory-level scoping."""
    resp = requests.get(
        f"{GRAPH}/sites/{site_id}/drives",
        headers=_headers(user_token),
        timeout=_TIMEOUT,
    )
    resp.raise_for_status()
    return [
        {"id": d["id"], "name": d.get("name", ""), "webUrl": d.get("webUrl", "")}
        for d in resp.json().get("value", [])
    ]


def grant_read(user_token: str, site_id: str, app_id: str, display_name: str) -> dict:
    """Create a Selected READ grant for the pinned app on the site.

    Succeeds only if the signed-in user is an Owner (Graph returns 403 otherwise).
    """
    body = {
        "roles": ["read"],
        "grantedToIdentities": [
            {"application": {"id": app_id, "displayName": display_name}}
        ],
    }
    resp = requests.post(
        f"{GRAPH}/sites/{site_id}/permissions",
        headers=_headers(user_token),
        json=body,
        timeout=_TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()


def revoke(user_token: str, site_id: str, permission_id: str) -> None:
    resp = requests.delete(
        f"{GRAPH}/sites/{site_id}/permissions/{permission_id}",
        headers=_headers(user_token),
        timeout=_TIMEOUT,
    )
    resp.raise_for_status()

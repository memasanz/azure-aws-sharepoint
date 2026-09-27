"""Self-service access portal API (Sprint B3).

Lets a SharePoint site Owner sign in (React SPA, MSAL + PKCE, no secret) and grant
the pinned APIM managed identity READ access to a site/library they own. Guardrails
(spec §13.5) are enforced here:

  1. Target is hard-pinned to the one APIM MI (settings.apim_mi_app_id).
  2. Only the `read` role is ever requested.
  3. Ownership is enforced by Graph (the delegated grant fails unless the user owns it).
  4. Every grant is recorded and is revocable.
"""

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests

from .auth import get_current_user
from .config import settings
from . import graph, store

app = FastAPI(title="SharePoint Access Self-Service Portal")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup() -> None:
    store.init_db()


class GrantRequest(BaseModel):
    siteId: str
    resourceDescription: str | None = None


def _handle_graph_error(exc: requests.HTTPError):
    status = exc.response.status_code if exc.response is not None else 502
    if status == 403:
        raise HTTPException(
            status_code=403,
            detail="You must be an Owner of this site to grant access.",
        )
    raise HTTPException(status_code=status, detail=f"Graph error: {exc}")


@app.get("/api/config")
def get_config():
    """Non-secret config the SPA needs (pinned target, allowed role)."""
    return {
        "grantsTo": settings.apim_mi_display_name,
        "allowedRole": settings.allowed_role,
    }


@app.get("/api/me")
def me(user: dict = Depends(get_current_user)):
    return {"name": user["name"], "upn": user["upn"], "oid": user["oid"]}


@app.get("/api/sites")
def sites(search: str = "*", user: dict = Depends(get_current_user)):
    try:
        return graph.search_sites(user["token"], search)
    except requests.HTTPError as exc:
        _handle_graph_error(exc)


@app.get("/api/sites/{site_id}/libraries")
def libraries(site_id: str, user: dict = Depends(get_current_user)):
    try:
        return graph.list_libraries(user["token"], site_id)
    except requests.HTTPError as exc:
        _handle_graph_error(exc)


@app.post("/api/grants")
def create_grant(req: GrantRequest, user: dict = Depends(get_current_user)):
    # Guardrails: pinned target + read-only, enforced server-side.
    try:
        result = graph.grant_read(
            user["token"],
            req.siteId,
            settings.apim_mi_app_id,
            settings.apim_mi_display_name,
        )
    except requests.HTTPError as exc:
        _handle_graph_error(exc)

    store.record_grant(
        permission_id=result.get("id", ""),
        site_id=req.siteId,
        resource_desc=req.resourceDescription or req.siteId,
        role=settings.allowed_role,
        granted_to=settings.apim_mi_display_name,
        granted_by=user["upn"] or user["name"],
    )
    return {"permissionId": result.get("id"), "roles": result.get("roles")}


@app.get("/api/grants")
def get_grants(include_revoked: bool = False):
    return store.list_grants(include_revoked)


@app.delete("/api/grants/{permission_id}")
def revoke_grant(permission_id: str, siteId: str, user: dict = Depends(get_current_user)):
    try:
        graph.revoke(user["token"], siteId, permission_id)
    except requests.HTTPError as exc:
        _handle_graph_error(exc)
    store.mark_revoked(permission_id)
    return {"status": "revoked", "permissionId": permission_id}

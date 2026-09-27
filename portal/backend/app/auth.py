"""Extract the caller from the delegated Graph bearer token.

The SPA acquires a delegated Microsoft Graph token (MSAL + PKCE) and sends it to
this backend, which uses it as-is to call Graph on the user's behalf. Because the
token is a real Entra-issued Graph token, the actual authorization is enforced by
Graph itself — a Selected grant only succeeds if the signed-in user is genuinely
an Owner of the resource (spec §13: ownership-scoped, enforced server-side).

NOTE: For brevity this decodes the JWT to surface the user's name/oid for the
audit log; it does not re-verify the signature (Graph does that on every call).
A production deployment should also validate the token's signature/audience here.
"""

import base64
import json

from fastapi import Header, HTTPException


def _decode_claims(token: str) -> dict:
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        return json.loads(base64.urlsafe_b64decode(payload))
    except Exception:  # noqa: BLE001
        raise HTTPException(status_code=401, detail="Malformed bearer token")


def get_bearer_token(authorization: str = Header(default="")) -> str:
    if not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    return authorization.split(" ", 1)[1].strip()


def get_current_user(authorization: str = Header(default="")) -> dict:
    token = get_bearer_token(authorization)
    claims = _decode_claims(token)
    return {
        "oid": claims.get("oid") or claims.get("sub"),
        "name": claims.get("name", "unknown"),
        "upn": claims.get("preferred_username") or claims.get("upn", ""),
        "token": token,
    }

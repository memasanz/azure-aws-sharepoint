"""Grant the APIM managed identity a read-only `Selected` permission on a
SharePoint site (Sprint B1) — no client secret required.

Auth: uses your signed-in Azure CLI / developer credential (az login), so the
person running it must be a SharePoint admin or site Owner (spec §7.4). No
secret is stored anywhere.

What it does:
  1. Resolves the APIM managed identity's application (appId) from its principal
     (object) id.
  2. Creates a Selected permission grant:  APIM-MI-app -> read -> site.

Site-level read is the well-supported baseline used to prove the read path.
Sprint B2 tightens this to a specific library/folder (least privilege).

Usage:
  pip install -r requirements.txt   # azure-identity, requests
  python grant_selected_read.py \
      --mi-principal-id <apimPrincipalId output> \
      --site-hostname contoso.sharepoint.com \
      --site-path /sites/Engineering
"""

import argparse
import sys

import requests
from azure.identity import DefaultAzureCredential

GRAPH = "https://graph.microsoft.com/v1.0"


def _token() -> str:
    cred = DefaultAzureCredential(exclude_interactive_browser_credential=False)
    return cred.get_token("https://graph.microsoft.com/.default").token


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def resolve_app_id(token: str, principal_id: str) -> tuple[str, str]:
    """Return (appId, displayName) for the managed identity's service principal."""
    resp = requests.get(
        f"{GRAPH}/servicePrincipals/{principal_id}",
        headers=_headers(token),
        timeout=30,
    )
    resp.raise_for_status()
    sp = resp.json()
    return sp["appId"], sp.get("displayName", "APIM managed identity")


def resolve_site_id(token: str, hostname: str, site_path: str) -> str:
    """Return the Graph site id for hostname:/sites/Name."""
    resp = requests.get(
        f"{GRAPH}/sites/{hostname}:{site_path}",
        headers=_headers(token),
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["id"]


def grant_read(token: str, site_id: str, app_id: str, display_name: str) -> dict:
    body = {
        "roles": ["read"],
        "grantedToIdentities": [
            {"application": {"id": app_id, "displayName": display_name}}
        ],
    }
    resp = requests.post(
        f"{GRAPH}/sites/{site_id}/permissions",
        headers=_headers(token),
        json=body,
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--mi-principal-id", required=True,
                    help="APIM managed identity object/principal id (Bicep output apimPrincipalId).")
    ap.add_argument("--site-hostname", required=True,
                    help="e.g. contoso.sharepoint.com")
    ap.add_argument("--site-path", required=True,
                    help="e.g. /sites/Engineering")
    args = ap.parse_args()

    token = _token()
    app_id, display_name = resolve_app_id(token, args.mi_principal_id)
    site_id = resolve_site_id(token, args.site_hostname, args.site_path)

    print(f"Granting READ to app {app_id} ({display_name}) on site {site_id} ...")
    result = grant_read(token, site_id, app_id, display_name)
    print("Grant created:")
    print(f"  permission id : {result.get('id')}")
    print(f"  roles         : {result.get('roles')}")
    print(f"  site id       : {site_id}   <- pass to the reader Lambda as SITE_ID")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Reader Lambda (Sprint B1).

The production shape of the AWS side: mint a short-lived Cognito JWT, then call
the APIM endpoint to read a SharePoint folder. No secret, cert, or password.

Environment:
  IDENTITY_POOL_ID         Cognito Identity Pool ID
  DEVELOPER_PROVIDER_NAME  Cognito developer provider name
  DEVELOPER_IDENTIFIER     Stable developer identifier (default aws-sharepoint-reader)
  APIM_READ_URL            e.g. https://<apim>.azure-api.net/sharepoint/read
  SITE_ID                  Graph site id (from grant_selected_read.py output)
  DEFAULT_PATH             Default folder path to read (optional)

Event overrides (optional): {"siteId": "...", "path": "Folder/Sub"}
"""

import json
import os
import urllib.parse
import urllib.request

import boto3

_cognito = boto3.client("cognito-identity")

_POOL_ID = os.environ["IDENTITY_POOL_ID"]
_DEV_PROVIDER = os.environ["DEVELOPER_PROVIDER_NAME"]
_DEV_IDENTIFIER = os.environ.get("DEVELOPER_IDENTIFIER", "aws-sharepoint-reader")
_APIM_READ_URL = os.environ["APIM_READ_URL"]
_SITE_ID = os.environ.get("SITE_ID", "")
_DEFAULT_PATH = os.environ.get("DEFAULT_PATH", "")


def _mint_token() -> str:
    resp = _cognito.get_open_id_token_for_developer_identity(
        IdentityPoolId=_POOL_ID,
        Logins={_DEV_PROVIDER: _DEV_IDENTIFIER},
        TokenDuration=900,
    )
    return resp["Token"]


def handler(event, context):
    event = event or {}
    site_id = event.get("siteId") or _SITE_ID
    path = event.get("path", _DEFAULT_PATH)
    if not site_id:
        return {"statusCode": 400, "body": "siteId is required (env SITE_ID or event.siteId)"}

    token = _mint_token()

    query = urllib.parse.urlencode({"siteId": site_id, "path": path})
    req = urllib.request.Request(
        f"{_APIM_READ_URL}?{query}",
        headers={"Authorization": f"Bearer {token}"},
        method="GET",
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
            return {"statusCode": resp.status, "body": payload}
    except urllib.error.HTTPError as exc:
        return {"statusCode": exc.code, "body": exc.read().decode("utf-8")}


if __name__ == "__main__":
    print(json.dumps(handler({}, None), indent=2, default=str))

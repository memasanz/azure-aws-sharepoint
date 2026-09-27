"""Token-minter Lambda (Sprint B0 spike).

Mints a short-lived, Cognito-signed OpenID JWT using the Lambda's own IAM role
(GetOpenIdTokenForDeveloperIdentity) and returns it. No secret, cert, or password
is involved. In later sprints the Lambda sends this token to APIM instead of
returning it.

Token claims to expect (verify with scripts/decode_jwt.py):
  iss = https://cognito-identity.amazonaws.com
  aud = <identity pool id>
  sub = <stable Cognito identity id>   (pinned by APIM in Sprint B2)
"""

import os

import boto3

_cognito = boto3.client("cognito-identity")

_POOL_ID = os.environ["IDENTITY_POOL_ID"]
_DEV_PROVIDER = os.environ["DEVELOPER_PROVIDER_NAME"]
_DEV_IDENTIFIER = os.environ.get("DEVELOPER_IDENTIFIER", "aws-sharepoint-reader")


def handler(event, context):
    """Return a Cognito OpenID token for the pinned developer identity."""
    resp = _cognito.get_open_id_token_for_developer_identity(
        IdentityPoolId=_POOL_ID,
        Logins={_DEV_PROVIDER: _DEV_IDENTIFIER},
        TokenDuration=900,
    )

    return {
        "identityId": resp["IdentityId"],
        "token": resp["Token"],
    }

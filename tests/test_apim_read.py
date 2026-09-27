"""Negative + positive tests for the hardened APIM endpoint (Sprint B2).

These hit a LIVE APIM instance, so they're skipped unless APIM_READ_URL is set.
They verify the trust boundary: only a valid, correctly-scoped Cognito token for
the pinned identity gets through; everything else is rejected.

Env:
  APIM_READ_URL   e.g. https://<apim>.azure-api.net/sharepoint/read
  SITE_ID         a granted Graph site id
  VALID_TOKEN     a freshly minted, valid Cognito JWT for the pinned identity
  WRONG_SUB_TOKEN (optional) a valid Cognito JWT for a DIFFERENT identity
  EXPIRED_TOKEN   (optional) an expired Cognito JWT

Run:
  pip install -r requirements.txt
  APIM_READ_URL=... SITE_ID=... VALID_TOKEN=... pytest -v
"""

import os
import urllib.parse

import pytest
import requests

READ_URL = os.environ.get("APIM_READ_URL")
SITE_ID = os.environ.get("SITE_ID", "")
VALID_TOKEN = os.environ.get("VALID_TOKEN")
WRONG_SUB_TOKEN = os.environ.get("WRONG_SUB_TOKEN")
EXPIRED_TOKEN = os.environ.get("EXPIRED_TOKEN")

pytestmark = pytest.mark.skipif(
    not (READ_URL and VALID_TOKEN),
    reason="Set APIM_READ_URL and VALID_TOKEN to run live APIM tests.",
)


def _get(token: str | None, site_id: str = SITE_ID, path: str = "") -> requests.Response:
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    query = urllib.parse.urlencode({"siteId": site_id, "path": path})
    return requests.get(f"{READ_URL}?{query}", headers=headers, timeout=30)


def test_valid_token_is_accepted():
    resp = _get(VALID_TOKEN)
    assert resp.status_code == 200, resp.text


def test_missing_token_is_rejected():
    assert _get(None).status_code == 401


def test_tampered_token_is_rejected():
    tampered = VALID_TOKEN[:-4] + ("aaaa" if VALID_TOKEN[-4:] != "aaaa" else "bbbb")
    assert _get(tampered).status_code == 401


def test_garbage_token_is_rejected():
    assert _get("not.a.jwt").status_code == 401


def test_missing_site_id_is_bad_request():
    # Valid token but no siteId -> policy returns 400 (not 200, not a Graph call)
    assert _get(VALID_TOKEN, site_id="").status_code == 400


@pytest.mark.skipif(not WRONG_SUB_TOKEN, reason="Set WRONG_SUB_TOKEN to test sub pinning.")
def test_wrong_subject_is_rejected():
    # Valid signature/issuer/audience but a DIFFERENT sub -> 401 from the sub pin.
    assert _get(WRONG_SUB_TOKEN).status_code == 401


@pytest.mark.skipif(not EXPIRED_TOKEN, reason="Set EXPIRED_TOKEN to test expiry.")
def test_expired_token_is_rejected():
    assert _get(EXPIRED_TOKEN).status_code == 401

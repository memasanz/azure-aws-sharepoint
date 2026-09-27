"""Decode a Cognito JWT and print its header + claims (NO signature verification).

Spike helper only — use it to record the real iss / aud / sub / exp values that
the APIM validate-jwt policy must expect and pin.

Usage:
    python scripts/decode_jwt.py <token>
    echo <token> | python scripts/decode_jwt.py
"""

import base64
import json
import sys


def _b64url_decode(segment: str) -> bytes:
    padding = "=" * (-len(segment) % 4)
    return base64.urlsafe_b64decode(segment + padding)


def decode(token: str) -> None:
    parts = token.strip().split(".")
    if len(parts) != 3:
        raise SystemExit("Not a JWT: expected 3 dot-separated segments.")

    header = json.loads(_b64url_decode(parts[0]))
    claims = json.loads(_b64url_decode(parts[1]))

    print("=== Header ===")
    print(json.dumps(header, indent=2))
    print("\n=== Claims ===")
    print(json.dumps(claims, indent=2))

    print("\n=== Pin these in apim/validate-jwt.xml ===")
    print(f"  iss (issuer)   : {claims.get('iss')}")
    print(f"  aud (audience) : {claims.get('aud')}")
    print(f"  sub (subject)  : {claims.get('sub')}   <- pin in Sprint B2")


if __name__ == "__main__":
    raw = sys.argv[1] if len(sys.argv) > 1 else sys.stdin.read()
    decode(raw)

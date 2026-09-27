"""Recertify Selected grants (Sprint B4).

Reads the portal's grant registry (grants.db) and flags grants older than a
threshold for periodic review (spec §13.5 / §9). Optionally revokes the stale
ones via Microsoft Graph.

Auth for --revoke: your signed-in Azure CLI / developer credential (az login).
No secret is stored.

Usage:
  pip install -r requirements.txt        # (azure-identity, requests) for --revoke
  python recertify_grants.py --db ../portal/backend/grants.db --max-age-days 90
  python recertify_grants.py --db ../portal/backend/grants.db --max-age-days 90 --revoke
"""

import argparse
import sqlite3
import sys
from datetime import datetime, timezone


def _load_active_grants(db_path: str) -> list[dict]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT * FROM grants WHERE revoked_at IS NULL ORDER BY granted_at"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def _age_days(iso_ts: str) -> int:
    granted = datetime.fromisoformat(iso_ts)
    if granted.tzinfo is None:
        granted = granted.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - granted).days


def _revoke(site_id: str, permission_id: str, db_path: str) -> None:
    import requests
    from azure.identity import DefaultAzureCredential

    token = DefaultAzureCredential(
        exclude_interactive_browser_credential=False
    ).get_token("https://graph.microsoft.com/.default").token

    resp = requests.delete(
        f"https://graph.microsoft.com/v1.0/sites/{site_id}/permissions/{permission_id}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    resp.raise_for_status()

    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            "UPDATE grants SET revoked_at = ? WHERE permission_id = ?",
            (datetime.now(timezone.utc).isoformat(), permission_id),
        )
        conn.commit()
    finally:
        conn.close()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", required=True, help="Path to the portal grants.db.")
    ap.add_argument("--max-age-days", type=int, default=90)
    ap.add_argument("--revoke", action="store_true", help="Revoke stale grants (needs az login).")
    args = ap.parse_args()

    grants = _load_active_grants(args.db)
    stale = [g for g in grants if _age_days(g["granted_at"]) >= args.max_age_days]

    print(f"Active grants: {len(grants)} | stale (>= {args.max_age_days}d): {len(stale)}")
    for g in stale:
        age = _age_days(g["granted_at"])
        print(f"  [{age:>4}d] {g['resource_desc']}  ->  {g['granted_to']}  "
              f"(by {g['granted_by']}, perm {g['permission_id']})")

    if args.revoke and stale:
        for g in stale:
            print(f"Revoking {g['permission_id']} on {g['site_id']} ...")
            _revoke(g["site_id"], g["permission_id"], args.db)
        print(f"Revoked {len(stale)} stale grant(s).")
    elif stale:
        print("\nRe-run with --revoke to remove the stale grants above.")

    return 0


if __name__ == "__main__":
    sys.exit(main())

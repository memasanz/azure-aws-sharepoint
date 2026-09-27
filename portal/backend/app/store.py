"""SQLite grant registry (audit trail) for the self-service portal.

Records every grant so they can be listed, reviewed, and revoked (spec §13.5).
"""

import sqlite3
from contextlib import closing
from datetime import datetime, timezone

from .config import settings

_SCHEMA = """
CREATE TABLE IF NOT EXISTS grants (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    permission_id TEXT NOT NULL,
    site_id       TEXT NOT NULL,
    resource_desc TEXT NOT NULL,
    role          TEXT NOT NULL,
    granted_to    TEXT NOT NULL,
    granted_by    TEXT NOT NULL,
    granted_at    TEXT NOT NULL,
    revoked_at    TEXT
);
"""


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(settings.grant_db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with closing(_conn()) as conn:
        conn.executescript(_SCHEMA)
        conn.commit()


def record_grant(permission_id: str, site_id: str, resource_desc: str,
                 role: str, granted_to: str, granted_by: str) -> None:
    with closing(_conn()) as conn:
        conn.execute(
            "INSERT INTO grants (permission_id, site_id, resource_desc, role, "
            "granted_to, granted_by, granted_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (permission_id, site_id, resource_desc, role, granted_to, granted_by,
             datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()


def list_grants(include_revoked: bool = False) -> list[dict]:
    query = "SELECT * FROM grants"
    if not include_revoked:
        query += " WHERE revoked_at IS NULL"
    query += " ORDER BY granted_at DESC"
    with closing(_conn()) as conn:
        return [dict(row) for row in conn.execute(query).fetchall()]


def mark_revoked(permission_id: str) -> None:
    with closing(_conn()) as conn:
        conn.execute(
            "UPDATE grants SET revoked_at = ? WHERE permission_id = ? AND revoked_at IS NULL",
            (datetime.now(timezone.utc).isoformat(), permission_id),
        )
        conn.commit()

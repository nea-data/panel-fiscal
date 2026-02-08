from typing import Optional, Dict
from auth.db import get_connection


def get_usage_extras(user_id: int, period: str) -> Dict[str, int]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT extra_cuit_queries, extra_bank_extracts
        FROM usage_extras
        WHERE user_id = ? AND period = ?
        LIMIT 1
    """, (user_id, period))
    row = cur.fetchone()
    if not row:
        return {"extra_cuit": 0, "extra_bank": 0}
    return {"extra_cuit": int(row["extra_cuit_queries"]), "extra_bank": int(row["extra_bank_extracts"])}


def grant_usage_extras(
    user_id: int,
    period: str,
    extra_cuit: int = 0,
    extra_bank: int = 0,
    granted_by: str = "",
    note: str = ""
) -> None:
    if extra_cuit < 0 or extra_bank < 0:
        raise ValueError("Extras no pueden ser negativos")

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO usage_extras (user_id, period, extra_cuit_queries, extra_bank_extracts, granted_by, note)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(user_id, period) DO UPDATE SET
            extra_cuit_queries = excluded.extra_cuit_queries,
            extra_bank_extracts = excluded.extra_bank_extracts,
            granted_by = excluded.granted_by,
            note = excluded.note
    """, (user_id, period, int(extra_cuit), int(extra_bank), granted_by or None, note or None))

    conn.commit()

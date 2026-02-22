from typing import Dict
from auth.db import get_connection


# =====================================================
# Get usage extras
# =====================================================
def get_usage_extras(user_id: int, period: str) -> Dict[str, int]:
    conn = get_connection()

    with conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT extra_cuit_queries, extra_bank_extracts
                FROM usage_extras
                WHERE user_id = %s AND period = %s
                LIMIT 1
            """, (user_id, period))

            row = cur.fetchone()

    conn.close()

    if not row:
        return {"extra_cuit": 0, "extra_bank": 0}

    return {
        "extra_cuit": int(row["extra_cuit_queries"] or 0),
        "extra_bank": int(row["extra_bank_extracts"] or 0),
    }


# =====================================================
# Grant usage extras
# =====================================================
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

    with conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO usage_extras (
                    user_id,
                    period,
                    extra_cuit_queries,
                    extra_bank_extracts,
                    granted_by,
                    note
                )
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (user_id, period)
                DO UPDATE SET
                    extra_cuit_queries = EXCLUDED.extra_cuit_queries,
                    extra_bank_extracts = EXCLUDED.extra_bank_extracts,
                    granted_by = EXCLUDED.granted_by,
                    note = EXCLUDED.note
            """, (
                user_id,
                period,
                int(extra_cuit),
                int(extra_bank),
                granted_by or None,
                note or None
            ))

    conn.close()

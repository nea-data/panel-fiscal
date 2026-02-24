from auth.db import get_connection


# =====================================================
# Incrementar uso CUIT
# =====================================================
def increment_cuit_usage(user_id: int, amount: int, period: str):
    conn = get_connection()

    with conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO usage (user_id, period, cuit_queries, bank_extracts)
                VALUES (%s, %s, %s, 0)
                ON CONFLICT (user_id, period)
                DO UPDATE
                SET cuit_queries = usage.cuit_queries + EXCLUDED.cuit_queries
            """, (user_id, period, amount))

    conn.close()


# =====================================================
# Incrementar uso Extractores
# =====================================================
def increment_bank_usage(user_id: int, amount: int, period: str):
    conn = get_connection()

    with conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO usage (user_id, period, cuit_queries, bank_extracts)
                VALUES (%s, %s, 0, %s)
                ON CONFLICT (user_id, period)
                DO UPDATE
                SET bank_extracts = usage.bank_extracts + EXCLUDED.bank_extracts
            """, (user_id, period, amount))

    conn.close()

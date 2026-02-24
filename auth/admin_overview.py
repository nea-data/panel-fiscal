from datetime import datetime
from auth.db import get_connection


def get_admin_clients_overview():
    conn = get_connection()

    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    u.id,
                    u.email,
                    u.name,
                    u.role,
                    u.status,

                    s.start_date,
                    s.end_date,
                    s.status AS subscription_status,

                    p.code AS plan_code,
                    p.name AS plan_name,
                    p.max_cuit_queries,
                    p.max_bank_extracts

                FROM users u

                LEFT JOIN LATERAL (
                    SELECT *
                    FROM subscriptions
                    WHERE user_id = u.id
                    ORDER BY end_date DESC
                    LIMIT 1
                ) s ON TRUE

                LEFT JOIN plans p
                    ON p.id = s.plan_id

                ORDER BY u.created_at DESC
            """)

            rows = cur.fetchall()
            results = []

            for r in rows:
                row = dict(r)

                # Calcular días restantes
                days_left = None
                if row.get("end_date"):
                    delta = row["end_date"] - datetime.utcnow()
                    days_left = max(0, delta.days)

                row["days_left"] = days_left

                results.append(row)

            return results

    finally:
        conn.close()

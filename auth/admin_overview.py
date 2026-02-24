from datetime import datetime, timezone
from auth.db import get_connection


def get_admin_clients_overview(period=None):
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

            now = datetime.now(timezone.utc)

            for r in rows:
                row = dict(r)

                # ==========================
                # Cálculo robusto días restantes
                # ==========================
                days_left = None
                end_date = row.get("end_date")

                if isinstance(end_date, datetime):
                    try:
                        delta = end_date - now
                        days_left = max(0, delta.days)
                    except Exception:
                        days_left = None

                row["days_left"] = days_left

                results.append(row)

            return results

    finally:
        conn.close()

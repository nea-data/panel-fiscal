from datetime import datetime, timezone
import pandas as pd
from auth.db import get_connection
from auth.service import get_usage_status


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
                    u.created_at,
                    u.last_login_at,

                    s.start_date,
                    s.end_date,
                    s.status AS subscription_status,

                    p.code AS plan_code,
                    p.name AS plan_name

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

    finally:
        conn.close()

    results = []
    now = datetime.now(timezone.utc)

    for r in rows:
        row = dict(r)

        # =========================
        # DÍAS RESTANTES
        # =========================
        days_left = None
        end_date = row.get("end_date")

        if isinstance(end_date, datetime):
            delta = end_date - now
            days_left = max(0, delta.days)

        row["days_left"] = days_left

        # =========================
        # ESTADO DE SUSCRIPCIÓN
        # =========================
        if not row.get("plan_code"):
            subscription_state = "SIN_PLAN"
        elif days_left is None:
            subscription_state = "INACTIVA"
        elif days_left <= 0:
            subscription_state = "VENCIDO"
        elif days_left <= 5:
            subscription_state = "POR_VENCER"
        else:
            subscription_state = "ACTIVO"

        row["subscription_state"] = subscription_state

        # =========================
        # USO
        # =========================
        try:
            usage = get_usage_status(row["id"])

            row["cuit_display"] = usage["cuit_display"]
            row["bank_display"] = usage["bank_display"]
            row["last_activity"] = usage.get("last_activity")

            total_cuit = usage.get("total_cuit", 0)
            total_bank = usage.get("total_bank", 0)

            row["cuit_usage_pct"] = (
                int((usage["cuit_used"] / total_cuit) * 100)
                if total_cuit > 0 else 0
            )

            row["bank_usage_pct"] = (
                int((usage["bank_used"] / total_bank) * 100)
                if total_bank > 0 else 0
            )

        except Exception:
            row["cuit_display"] = "-"
            row["bank_display"] = "-"
            row["last_activity"] = None
            row["cuit_usage_pct"] = 0
            row["bank_usage_pct"] = 0

        results.append(row)

    return results

from datetime import datetime, timedelta
from typing import Optional
from auth.db import get_connection



# =====================================================
# PLANES
# =====================================================

def get_plan_by_code(plan_code: str) -> Optional[dict]:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM plans WHERE code = %s LIMIT 1",
                (plan_code,)
            )
            row = cur.fetchone()
            return dict(row) if row else None
    finally:
        conn.close()


def get_active_subscription(user_id: int) -> Optional[dict]:
    conn = get_connection()

    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT s.*,
                       p.code AS plan_code,
                       p.name AS plan_name,
                       p.max_cuit_queries,
                       p.max_bank_extracts
                FROM subscriptions s
                JOIN plans p ON p.id = s.plan_id
                WHERE s.user_id = %s
                  AND s.status = 'active'
                ORDER BY s.end_date DESC
                LIMIT 1
            """, (user_id,))

            row = cur.fetchone()

            if not row:
                return None

            sub = dict(row)

            # 🔥 VALIDACIÓN DEFINITIVA EN PYTHON
            end_date = sub.get("end_date")

            if not end_date:
                return None

            if end_date < datetime.utcnow():
                return None

            return sub

    finally:
        conn.close()


def is_subscription_active(user_id: int) -> bool:
    return get_active_subscription(user_id) is not None


# =====================================================
# DÍAS RESTANTES
# =====================================================

def days_until_expiration(user_id: int) -> Optional[int]:
    sub = get_active_subscription(user_id)
    if not sub:
        return None

    end_dt = sub["end_date"]
    now_dt = datetime.utcnow()
    delta = end_dt - now_dt
    return max(0, delta.days)


# =====================================================
# CREAR SUSCRIPCIÓN
# =====================================================

def create_subscription(
    user_id: int,
    plan_code: str,
    days: Optional[int] = None,
    changed_by: str = ""
) -> None:

    plan = get_plan_by_code(plan_code)
    if not plan:
        raise ValueError("Plan inexistente")

    # 🔥 Lógica automática de duración
    if days is None:
        if plan_code == "FREE":
            days = 7
        else:
            days = 30

    conn = get_connection()

    try:
        with conn:
            with conn.cursor() as cur:

                # Desactiva suscripciones activas previas
                cur.execute("""
                    UPDATE subscriptions
                    SET status = 'expired'
                    WHERE user_id = %s
                      AND status = 'active'
                """, (user_id,))

                start = datetime.utcnow()
                end = start + timedelta(days=days)

                cur.execute("""
                    INSERT INTO subscriptions
                    (user_id, plan_id, status, start_date, end_date, changed_by)
                    VALUES (%s, %s, 'active', %s, %s, %s)
                """, (
                    user_id,
                    plan["id"],
                    start,
                    end,
                    changed_by or None
                ))

    finally:
        conn.close()


# =====================================================
# RENOVAR
# =====================================================

def renew_subscription(user_id: int, days: int = 30, changed_by: str = "") -> None:

    active = get_active_subscription(user_id)

    if not active:
        # Si no tiene activa → crear FREE por defecto
        create_subscription(user_id, "FREE", days=7, changed_by=changed_by)
        return

    conn = get_connection()

    try:
        with conn:
            with conn.cursor() as cur:

                base_end = active["end_date"]
                new_end = base_end + timedelta(days=days)

                cur.execute("""
                    UPDATE subscriptions
                    SET end_date = %s,
                        changed_by = %s
                    WHERE id = %s
                """, (
                    new_end,
                    changed_by or None,
                    active["id"]
                ))

    finally:
        conn.close()


# =====================================================
# CAMBIAR PLAN
# =====================================================

def change_plan(user_id: int, new_plan_code: str, changed_by: str = "") -> None:

    plan = get_plan_by_code(new_plan_code)
    if not plan:
        raise ValueError("Plan inexistente")

    active = get_active_subscription(user_id)

    if not active:
        create_subscription(user_id, new_plan_code, changed_by=changed_by)
        return

    conn = get_connection()

    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE subscriptions
                    SET plan_id = %s,
                        changed_by = %s
                    WHERE id = %s
                """, (
                    plan["id"],
                    changed_by or None,
                    active["id"]
                ))

    finally:
        conn.close()


# =====================================================
# SUSPENDER
# =====================================================

def suspend_subscription(user_id: int, changed_by: str = "") -> None:

    active = get_active_subscription(user_id)
    if not active:
        return

    conn = get_connection()

    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE subscriptions
                    SET status = 'suspended',
                        changed_by = %s
                    WHERE id = %s
                """, (
                    changed_by or None,
                    active["id"]
                ))

    finally:
        conn.close()

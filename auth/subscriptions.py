from datetime import datetime, timedelta, timezone
from typing import Optional, Any
from auth.db import get_connection


# =====================================================
# HELPERS DE FECHA (UTC AWARE)
# =====================================================

def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _to_aware_utc(dt: Any) -> Optional[datetime]:
    """
    Convierte cualquier datetime a timezone-aware en UTC.
    Maneja naive, aware, string ISO y None.
    """
    if dt is None:
        return None

    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt.replace("Z", "+00:00"))
        except Exception:
            return None

    if not isinstance(dt, datetime):
        return None

    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)

    return dt.astimezone(timezone.utc)


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
                ORDER BY s.end_date DESC NULLS LAST
                LIMIT 1
            """, (user_id,))

            row = cur.fetchone()
            if not row:
                return None

            sub = dict(row)

            end_date = _to_aware_utc(sub.get("end_date"))
            if end_date is None:
                return None

            if end_date <= _utc_now():
                return None

            sub["end_date"] = end_date
            sub["start_date"] = _to_aware_utc(sub.get("start_date"))

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

    end_dt = _to_aware_utc(sub.get("end_date"))
    if end_dt is None:
        return None

    delta = end_dt - _utc_now()
    return max(0, int(delta.total_seconds() // 86400))


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

    if days is None:
        days = 7 if plan_code == "FREE" else 30

    conn = get_connection()

    try:
        with conn:
            with conn.cursor() as cur:

                # Expirar activas previas
                cur.execute("""
                    UPDATE subscriptions
                    SET status = 'expired'
                    WHERE user_id = %s
                      AND status = 'active'
                """, (user_id,))

                start = _utc_now()
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
        create_subscription(user_id, "FREE", days=7, changed_by=changed_by)
        return

    conn = get_connection()

    try:
        with conn:
            with conn.cursor() as cur:

                base_end = _to_aware_utc(active.get("end_date"))
                now = _utc_now()

                if base_end is None or base_end < now:
                    base_end = now

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

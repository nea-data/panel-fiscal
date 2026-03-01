# auth/subscriptions.py
from __future__ import annotations
from datetime import datetime, timedelta, timezone
from typing import Optional
import pandas as pd
from psycopg2.extras import RealDictCursor # Agregado para consistencia
from auth.db import get_connection

# =====================================================
# PLANES
# =====================================================

def get_plan_by_code(plan_code: str) -> Optional[dict]:
    conn = get_connection()
    try:
        # Implementamos RealDictCursor para simplificar el retorno
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM plans WHERE code = %s LIMIT 1",
                (plan_code,),
            )
            return cur.fetchone()
    finally:
        conn.close()

def _to_utc_aware(dt_value) -> Optional[datetime]:
    """Normaliza a datetime timezone-aware en UTC."""
    if dt_value is None:
        return None
    if isinstance(dt_value, str):
        try:
            dt_value = pd.to_datetime(dt_value, utc=True).to_pydatetime()
        except Exception:
            return None
    if not isinstance(dt_value, datetime):
        return None
    if dt_value.tzinfo is None:
        return dt_value.replace(tzinfo=timezone.utc)
    return dt_value.astimezone(timezone.utc)

# =====================================================
# CONSULTAS DE ESTADO
# =====================================================

def get_active_subscription(user_id: int) -> Optional[dict]:
    if user_id is None:
        return None

    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
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
                """,
                (user_id,),
            )

            row = cur.fetchone()
            if not row:
                return None

            sub = row
            end_date = _to_utc_aware(sub.get("end_date"))
            
            if not end_date or end_date <= datetime.now(timezone.utc):
                return None

            sub["end_date"] = end_date
            sub["start_date"] = _to_utc_aware(sub.get("start_date"))
            return sub
    finally:
        conn.close()

def is_subscription_active(user_id: int) -> bool:
    """Utilizado por guard.py para el control de acceso."""
    return get_active_subscription(user_id) is not None

def days_until_expiration(user_id: int) -> Optional[int]:
    sub = get_active_subscription(user_id)
    if not sub:
        return None
    end_dt = sub["end_date"]
    now_dt = datetime.now(timezone.utc)
    delta = end_dt - now_dt
    return max(0, int(delta.total_seconds() // 86400))

# =====================================================
# GESTIÓN (ADMIN)
# =====================================================

def create_subscription(
    user_id: int,
    plan_code: str,
    days: Optional[int] = None,
    changed_by: str = "",
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
                # 1. 'Devengamos' la suscripción anterior (limpieza de registros)
                cur.execute(
                    "UPDATE subscriptions SET status = 'expired' WHERE user_id = %s AND status = 'active'",
                    (user_id,),
                )

                start = datetime.now(timezone.utc)
                end = start + timedelta(days=days)

                # 2. Insertamos la nueva suscripción activa
                cur.execute(
                    """
                    INSERT INTO subscriptions 
                    (user_id, plan_id, status, start_date, end_date, changed_by)
                    VALUES (%s, %s, 'active', %s, %s, %s)
                    """,
                    (user_id, plan["id"], start, end, changed_by or None),
                )
    finally:
        conn.close()

def renew_subscription(user_id: int, days: int = 30, changed_by: str = "") -> None:
    active = get_active_subscription(user_id)
    if not active:
        # Si no tiene nada, le damos el alta inicial
        create_subscription(user_id, "FREE", days=7, changed_by=changed_by)
        return

    conn = get_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                base_end = _to_utc_aware(active["end_date"]) or datetime.now(timezone.utc)
                new_end = base_end + timedelta(days=days)

                cur.execute(
                    "UPDATE subscriptions SET end_date = %s, changed_by = %s WHERE id = %s",
                    (new_end, changed_by or None, active["id"]),
                )
    finally:
        conn.close()

def suspend_subscription(user_id: int, changed_by: str = "") -> None:
    active = get_active_subscription(user_id)
    if not active:
        return

    conn = get_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE subscriptions SET status = 'suspended', changed_by = %s WHERE id = %s",
                    (changed_by or None, active["id"]),
                )
    finally:
        conn.close()

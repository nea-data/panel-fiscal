from datetime import datetime, timedelta
from typing import Optional, Dict

from auth.db import get_connection


def _now_iso() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")


def _parse_dt(value: str) -> datetime:
    # value esperado: "YYYY-MM-DD HH:MM:SS"
    return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")


def get_plan_by_code(plan_code: str) -> Optional[dict]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM plans WHERE code = ? LIMIT 1", (plan_code,))
    row = cur.fetchone()
    return dict(row) if row else None


def get_active_subscription(user_id: int) -> Optional[dict]:
    """
    Devuelve suscripción activa si:
    - status='active'
    - end_date >= ahora
    """
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT s.*, p.code AS plan_code, p.name AS plan_name,
               p.max_cuit_queries, p.max_bank_extracts
        FROM subscriptions s
        JOIN plans p ON p.id = s.plan_id
        WHERE s.user_id = ?
          AND s.status = 'active'
          AND datetime(s.end_date) >= datetime('now')
        ORDER BY datetime(s.end_date) DESC
        LIMIT 1
    """, (user_id,))

    row = cur.fetchone()
    return dict(row) if row else None


def is_subscription_active(user_id: int) -> bool:
    return get_active_subscription(user_id) is not None


def days_until_expiration(user_id: int) -> Optional[int]:
    sub = get_active_subscription(user_id)
    if not sub:
        return None
    end_dt = _parse_dt(sub["end_date"])
    now_dt = datetime.utcnow()
    delta = end_dt - now_dt
    # redondeo hacia abajo (días completos restantes)
    return max(0, delta.days)


def create_subscription(user_id: int, plan_code: str, days: int = 30, changed_by: str = "") -> int:
    """
    Crea una nueva suscripción activa desde AHORA por 'days' días.
    """
    plan = get_plan_by_code(plan_code)
    if not plan:
        raise ValueError("Plan inexistente")

    conn = get_connection()
    cur = conn.cursor()

    start = datetime.utcnow()
    end = start + timedelta(days=days)

    cur.execute("""
        INSERT INTO subscriptions (user_id, plan_id, status, start_date, end_date, changed_by)
        VALUES (?, ?, 'active', ?, ?, ?)
    """, (
        user_id,
        plan["id"],
        start.strftime("%Y-%m-%d %H:%M:%S"),
        end.strftime("%Y-%m-%d %H:%M:%S"),
        changed_by or None
    ))
    conn.commit()
    return cur.lastrowid


def renew_subscription(user_id: int, days: int = 30, changed_by: str = "") -> None:
    """
    Renueva 30 días.
    Regla:
    - Si hay suscripción activa -> extiende desde end_date
    - Si no hay activa -> crea nueva desde ahora
    """
    active = get_active_subscription(user_id)

    conn = get_connection()
    cur = conn.cursor()

    if not active:
        # Si no hay activa, creamos con el último plan usado si existe,
        # o FREE por defecto.
        cur.execute("""
            SELECT s.plan_id, p.code AS plan_code
            FROM subscriptions s
            JOIN plans p ON p.id = s.plan_id
            WHERE s.user_id = ?
            ORDER BY datetime(s.end_date) DESC
            LIMIT 1
        """, (user_id,))
        last = cur.fetchone()
        plan_code = last["plan_code"] if last else "FREE"
        create_subscription(user_id, plan_code, days=days, changed_by=changed_by)
        return

    # Extiende desde end_date (no desde ahora)
    base_end = _parse_dt(active["end_date"])
    new_end = base_end + timedelta(days=days)

    cur.execute("""
        UPDATE subscriptions
        SET end_date = ?,
            changed_by = ?
        WHERE id = ?
    """, (
        new_end.strftime("%Y-%m-%d %H:%M:%S"),
        changed_by or None,
        active["id"]
    ))
    conn.commit()


def change_plan(user_id: int, new_plan_code: str, changed_by: str = "") -> None:
    """
    Cambia el plan en la suscripción activa (si hay).
    Si no hay activa, crea una suscripción nueva por 30 días con ese plan.
    """
    plan = get_plan_by_code(new_plan_code)
    if not plan:
        raise ValueError("Plan inexistente")

    active = get_active_subscription(user_id)

    conn = get_connection()
    cur = conn.cursor()

    if not active:
        create_subscription(user_id, new_plan_code, days=30, changed_by=changed_by)
        return

    cur.execute("""
        UPDATE subscriptions
        SET plan_id = ?,
            changed_by = ?
        WHERE id = ?
    """, (plan["id"], changed_by or None, active["id"]))
    conn.commit()


def suspend_subscription(user_id: int, changed_by: str = "") -> None:
    """
    Suspende la suscripción activa (si existe).
    """
    active = get_active_subscription(user_id)
    if not active:
        return

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE subscriptions
        SET status = 'suspended',
            changed_by = ?
        WHERE id = ?
    """, (changed_by or None, active["id"]))
    conn.commit()

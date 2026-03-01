# auth/service.py
from __future__ import annotations
from typing import Optional, Tuple, Dict, Any
from psycopg2.extras import RealDictCursor
from auth.db import get_connection
from auth.limits import (
    can_run_mass_cuit,
    can_run_bank_extract,
    get_current_period,
    get_effective_limits,
)
from auth.subscriptions import days_until_expiration

# =====================================================
# Asegurar que exista la fila de uso (Asiento de apertura de consumo)
# =====================================================
def _ensure_usage_row(user_id: int, period: str) -> None:
    conn = get_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id FROM usage WHERE user_id = %s AND period = %s",
                    (user_id, period),
                )
                if cur.fetchone() is None:
                    cur.execute(
                        """
                        INSERT INTO usage (user_id, period, cuit_queries, bank_extracts, fiscal_checks, last_activity)
                        VALUES (%s, %s, 0, 0, 0, CURRENT_TIMESTAMP)
                        """,
                        (user_id, period),
                    )
    finally:
        conn.close()

# =====================================================
# CONSUMO ATÓMICO (Source of Truth)
# =====================================================
def consume_quota_db(
    user_id: int,
    resource: str,  # 'cuit' | 'bank' | 'fiscal'
    amount: int,
    period: Optional[str] = None,
) -> Dict[str, Any]:

    if not user_id: raise ValueError("user_id vacío")
    amount = int(amount or 0)
    if amount <= 0:
        return {"allowed": False, "remaining": 0, "used": 0, "limit_total": 0}

    period = period or get_current_period()
    conn = get_connection()
    try:
        # Usamos RealDictCursor para manejar el retorno de la función SQL
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT allowed, remaining, used, limit_total FROM public.consume_quota(%s, %s, %s, %s)",
                (user_id, period, resource, amount),
            )
            row = cur.fetchone()

        if not row:
            return {"allowed": False, "remaining": 0, "used": 0, "limit_total": 0}

        return {
            "allowed": bool(row["allowed"]),
            "remaining": int(row["remaining"] or 0),
            "used": int(row["used"] or 0),
            "limit_total": int(row["limit_total"] or 0),
        }
    finally:
        conn.close()

# =====================================================
# ESTADO DE USO (Dashboard Overview)
# =====================================================
def get_usage_status(user_id: int) -> Dict[str, Any]:
    period = get_current_period()
    _ensure_usage_row(user_id, period)

    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT COALESCE(cuit_queries, 0) AS cuit_used, 
                       COALESCE(bank_extracts, 0) AS bank_used, 
                       last_activity 
                FROM usage WHERE user_id = %s AND period = %s LIMIT 1
                """,
                (user_id, period),
            )
            row = cur.fetchone()
    finally:
        conn.close()

    used = row if row else {"cuit_used": 0, "bank_used": 0, "last_activity": None}
    limits = get_effective_limits(user_id, period)
    days_left = days_until_expiration(user_id)

    return {
        "period": period,
        "plan_name": limits.get("plan_name", "Sin Plan"),
        "cuit_used": int(used["cuit_used"]),
        "bank_used": int(used["bank_used"]),
        "total_cuit": int(limits.get("total_cuit", 0)),
        "total_bank": int(limits.get("total_bank", 0)),
        "days_left": days_left,
        "last_activity": used.get("last_activity"),
    }

# =====================================================
# ALERTAS
# =====================================================
def should_show_expiration_alert(user_id: int) -> bool:
    """Retorna True si la suscripción vence en 7, 5, 3 o 1 días."""
    dl = days_until_expiration(user_id)
    # Alerta preventiva para el contador
    return dl in (7, 5, 3, 1) if dl is not None else False


# auth/limits.py

from datetime import datetime
from typing import Tuple

from auth.db import get_connection


def get_current_period() -> str:
    """
    Devuelve el período actual en formato YYYY-MM
    Ej: 2026-02
    """
    return datetime.now().strftime("%Y-%m")


def can_run_mass_cuit(user_id: int, cuits_to_process: int) -> Tuple[bool, str]:
    """
    Verifica si el usuario puede ejecutar una consulta masiva de CUITs.

    Reglas:
    - Consulta individual: ILIMITADA (no pasa por acá)
    - Consulta masiva: limitada por plan.max_cuit_queries
    - Si supera el límite mensual → bloquea

    Retorna:
        (True, "") si puede ejecutar
        (False, motivo) si NO puede ejecutar
    """

    conn = get_connection()
    cur = conn.cursor()

    # 1️⃣ Obtener suscripción activa
    cur.execute("""
        SELECT s.id, p.max_cuit_queries
        FROM subscriptions s
        JOIN plans p ON p.id = s.plan_id
        WHERE s.user_id = ?
          AND s.status = 'active'
          AND date(s.end_date) >= date('now')
        LIMIT 1
    """, (user_id,))

    row = cur.fetchone()

    if not row:
        return False, "No tenés una suscripción activa."

    subscription_id, max_cuit_queries = row

    # Seguridad extra
    if max_cuit_queries is None:
        return True, ""

    period = get_current_period()

    # 2️⃣ Obtener uso del período
    cur.execute("""
        SELECT cuit_queries
        FROM usage
        WHERE user_id = ?
          AND period = ?
    """, (user_id, period))

    usage_row = cur.fetchone()
    used_cuits = usage_row[0] if usage_row else 0

    # 3️⃣ Validar límite
    if used_cuits + cuits_to_process > max_cuit_queries:
        remaining = max_cuit_queries - used_cuits
        return (
            False,
            f"Límite mensual alcanzado. "
            f"Disponibles: {remaining} / {max_cuit_queries} CUITs."
        )

    return True, ""

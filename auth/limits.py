# auth/limits.py
from __future__ import annotations

from datetime import datetime
from typing import Tuple, Optional, Dict, Any

from auth.db import get_connection
from auth.subscriptions import get_active_subscription
from auth.extras import get_usage_extras


# =====================================================
# Período actual (YYYY-MM)
# =====================================================
def get_current_period() -> str:
    return datetime.now().strftime("%Y-%m")


# =====================================================
# Uso mensual
# =====================================================
def _get_month_usage(user_id: int, period: str) -> dict:
    conn = get_connection()

    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        COALESCE(cuit_queries, 0) AS cuit_used,
                        COALESCE(bank_extracts, 0) AS bank_used,
                        last_activity
                    FROM usage
                    WHERE user_id = %s AND period = %s
                    LIMIT 1
                    """,
                    (user_id, period),
                )

                row = cur.fetchone()

        if not row:
            return {"cuit_used": 0, "bank_used": 0, "last_activity": None}

        # row puede ser dict-like o tuple, según cursor factory
        d = dict(row)
        return {
            "cuit_used": int(d.get("cuit_used", 0) or 0),
            "bank_used": int(d.get("bank_used", 0) or 0),
            "last_activity": d.get("last_activity"),
        }

    finally:
        conn.close()


# =====================================================
# Límites efectivos (base + extras)
# =====================================================
def get_effective_limits(user_id: int, period: str, sub: Optional[dict] = None) -> dict:
    """
    Devuelve límites base + extras + totales.
    Requiere suscripción activa.
    - sub opcional para evitar volver a consultar.
    """
    if not user_id:
        return {}

    sub = sub or get_active_subscription(user_id)
    if not sub:
        return {}

    extras = get_usage_extras(user_id, period)

    base_cuit = int(sub.get("max_cuit_queries") or 0)
    base_bank = int(sub.get("max_bank_extracts") or 0)

    extra_cuit = int(extras.get("extra_cuit") or 0)
    extra_bank = int(extras.get("extra_bank") or 0)

    return {
        "base_cuit": base_cuit,
        "extra_cuit": extra_cuit,
        "total_cuit": base_cuit + extra_cuit,
        "base_bank": base_bank,
        "extra_bank": extra_bank,
        "total_bank": base_bank + extra_bank,
        "plan_code": sub.get("plan_code"),
        "plan_name": sub.get("plan_name"),
    }


# =====================================================
# Validar ejecución masiva CUIT
# =====================================================
def can_run_mass_cuit(user_id: int, cuits_to_process: int) -> Tuple[bool, str]:
    if not user_id:
        return False, "No se pudo identificar el usuario logueado (user_id vacío)."

    if cuits_to_process <= 0:
        return False, "No hay CUITs válidos para procesar."

    sub = get_active_subscription(user_id)
    if not sub:
        return False, "No tenés una suscripción activa (o está vencida)."

    period = get_current_period()
    usage = _get_month_usage(user_id, period)
    limits = get_effective_limits(user_id, period, sub=sub)

    used = int(usage.get("cuit_used", 0) or 0)
    total = int(limits.get("total_cuit", 0) or 0)
    base = int(limits.get("base_cuit", 0) or 0)
    extra = int(limits.get("extra_cuit", 0) or 0)

    if total <= 0:
        return False, "Tu plan no incluye consultas masivas de CUIT."

    remaining = max(0, total - used)

    if cuits_to_process > remaining:
        return (
            False,
            f"Límite alcanzado. Te quedan {remaining} consultas este período. "
            f"Usado: {used} / {base}+{extra} (máx {total}). "
            f"Intento: +{cuits_to_process}."
        )

    return True, ""


# =====================================================
# Validar ejecución extractor bancario
# =====================================================
def can_run_bank_extract(user_id: int) -> Tuple[bool, str]:
    if not user_id:
        return False, "No se pudo identificar el usuario logueado (user_id vacío)."

    sub = get_active_subscription(user_id)
    if not sub:
        return False, "No tenés una suscripción activa (o está vencida)."

    period = get_current_period()
    usage = _get_month_usage(user_id, period)
    limits = get_effective_limits(user_id, period, sub=sub)

    used = int(usage.get("bank_used", 0) or 0)
    total = int(limits.get("total_bank", 0) or 0)
    base = int(limits.get("base_bank", 0) or 0)
    extra = int(limits.get("extra_bank", 0) or 0)

    if total <= 0:
        return False, "Tu plan no incluye extractores bancarios."

    remaining = max(0, total - used)

    if remaining <= 0:
        return (
            False,
            f"Límite alcanzado. Usado: {used} / {base}+{extra} (máx {total})."
        )

    return True, ""

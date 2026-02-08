from datetime import datetime
from typing import Tuple

from auth.db import get_connection
from auth.subscriptions import get_active_subscription
from auth.extras import get_usage_extras


def get_current_period() -> str:
    return datetime.now().strftime("%Y-%m")


def _get_month_usage(user_id: int, period: str) -> dict:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT COALESCE(cuit_queries, 0) AS cuit_used,
               COALESCE(bank_extracts, 0) AS bank_used
        FROM usage
        WHERE user_id = ? AND period = ?
        LIMIT 1
    """, (user_id, period))
    row = cur.fetchone()
    if not row:
        return {"cuit_used": 0, "bank_used": 0}
    return {"cuit_used": int(row["cuit_used"]), "bank_used": int(row["bank_used"])}


def get_effective_limits(user_id: int, period: str) -> dict:
    """
    Devuelve límites base + extras + totales.
    Requiere suscripción activa.
    """
    sub = get_active_subscription(user_id)
    if not sub:
        return {}

    extras = get_usage_extras(user_id, period)

    base_cuit = int(sub["max_cuit_queries"] or 0)
    base_bank = int(sub["max_bank_extracts"] or 0)

    extra_cuit = int(extras["extra_cuit"])
    extra_bank = int(extras["extra_bank"])

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


def can_run_mass_cuit(user_id: int, cuits_to_process: int) -> Tuple[bool, str]:
    sub = get_active_subscription(user_id)
    if not sub:
        return False, "No tenés una suscripción activa (o está vencida)."

    period = get_current_period()
    usage = _get_month_usage(user_id, period)
    limits = get_effective_limits(user_id, period)

    used = usage["cuit_used"]
    total = limits["total_cuit"]
    base = limits["base_cuit"]
    extra = limits["extra_cuit"]

    # Si el plan base es 0 y no hay extras, bloquea (FREE por defecto)
    if total <= 0:
        return False, "Tu plan no incluye consultas masivas de CUIT."

    if used + cuits_to_process > total:
        return (
            False,
            f"Límite alcanzado. Usado: {used} / {base} +{extra}. "
            f"Intento: +{cuits_to_process} (máx total {total})."
        )

    return True, ""


def can_run_bank_extract(user_id: int) -> Tuple[bool, str]:
    sub = get_active_subscription(user_id)
    if not sub:
        return False, "No tenés una suscripción activa (o está vencida)."

    period = get_current_period()
    usage = _get_month_usage(user_id, period)
    limits = get_effective_limits(user_id, period)

    used = usage["bank_used"]
    total = limits["total_bank"]
    base = limits["base_bank"]
    extra = limits["extra_bank"]

    if total <= 0:
        return False, "Tu plan no incluye extractores bancarios."

    if used + 1 > total:
        return (
            False,
            f"Límite alcanzado. Usado: {used} / {base} +{extra} (máx total {total})."
        )

    return True, ""

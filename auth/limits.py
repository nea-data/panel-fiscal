from datetime import datetime
from typing import Tuple

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

    with conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    COALESCE(cuit_queries, 0) AS cuit_used,
                    COALESCE(bank_extracts, 0) AS bank_used
                FROM usage
                WHERE user_id = %s AND period = %s
                LIMIT 1
            """, (user_id, period))

            row = cur.fetchone()

    conn.close()

    if not row:
        return {"cuit_used": 0, "bank_used": 0}

    return {
        "cuit_used": int(row["cuit_used"]),
        "bank_used": int(row["bank_used"])
    }


# =====================================================
# Límites efectivos (base + extras)
# =====================================================
def get_effective_limits(user_id: int, period: str) -> dict:
    """
    Devuelve límites base + extras + totales.
    Requiere suscripción activa.
    """

    sub = get_active_subscription(user_id)
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
    sub = get_active_subscription(user_id)
    if not sub:
        return False, "No tenés una suscripción activa (o está vencida)."

    period = get_current_period()
    usage = _get_month_usage(user_id, period)
    limits = get_effective_limits(user_id, period)

    used = usage["cuit_used"]
    total = limits.get("total_cuit", 0)
    base = limits.get("base_cuit", 0)
    extra = limits.get("extra_cuit", 0)

    if total <= 0:
        return False, "Tu plan no incluye consultas masivas de CUIT."

    if used + cuits_to_process > total:
        return (
            False,
            f"Límite alcanzado. Usado: {used} / {base} +{extra}. "
            f"Intento: +{cuits_to_process} (máx total {total})."
        )

    return True, ""


# =====================================================
# Validar ejecución extractor bancario
# =====================================================
def can_run_bank_extract(user_id: int) -> Tuple[bool, str]:
    sub = get_active_subscription(user_id)
    if not sub:
        return False, "No tenés una suscripción activa (o está vencida)."

    period = get_current_period()
    usage = _get_month_usage(user_id, period)
    limits = get_effective_limits(user_id, period)

    used = usage["bank_used"]
    total = limits.get("total_bank", 0)
    base = limits.get("base_bank", 0)
    extra = limits.get("extra_bank", 0)

    if total <= 0:
        return False, "Tu plan no incluye extractores bancarios."

    if used + 1 > total:
        return (
            False,
            f"Límite alcanzado. Usado: {used} / {base} +{extra} (máx total {total})."
        )

    return True, ""

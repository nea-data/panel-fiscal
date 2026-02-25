# auth/service.py
from __future__ import annotations

from typing import Optional, Tuple, Dict, Any

from auth.db import get_connection
from auth.limits import (
    can_run_mass_cuit,
    can_run_bank_extract,
    get_current_period,
    get_effective_limits,
)
from auth.subscriptions import days_until_expiration


# =====================================================
# Ensure usage row exists
# =====================================================
def _ensure_usage_row(user_id: int, period: str) -> None:
    conn = get_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id FROM usage
                    WHERE user_id = %s AND period = %s
                    """,
                    (user_id, period),
                )

                if cur.fetchone() is None:
                    cur.execute(
                        """
                        INSERT INTO usage (
                            user_id,
                            period,
                            cuit_queries,
                            bank_extracts,
                            fiscal_checks,
                            last_activity
                        )
                        VALUES (%s, %s, 0, 0, 0, CURRENT_TIMESTAMP)
                        """,
                        (user_id, period),
                    )
    finally:
        conn.close()


# =====================================================
# 🔥 ATOMIC QUOTA CONSUMPTION (DB is source of truth)
# =====================================================
def consume_quota_db(
    user_id: int,
    resource: str,  # 'cuit' | 'bank' | 'fiscal'
    amount: int,
    period: Optional[str] = None,
) -> Dict[str, Any]:

    if not user_id:
        raise ValueError("user_id vacío")

    amount = int(amount or 0)
    if amount <= 0:
        return {
            "allowed": False,
            "remaining": 0,
            "used": 0,
            "limit_total": 0,
        }

    period = period or get_current_period()

    conn = get_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT allowed, remaining, used, limit_total
                    FROM public.consume_quota(%s, %s, %s, %s)
                    """,
                    (user_id, period, resource, amount),
                )

                row = cur.fetchone()

        if not row:
            return {
                "allowed": False,
                "remaining": 0,
                "used": 0,
                "limit_total": 0,
            }

        return {
            "allowed": bool(row["allowed"]),
            "remaining": int(row["remaining"] or 0),
            "used": int(row["used"] or 0),
            "limit_total": int(row["limit_total"] or 0),
        }

    finally:
        conn.close()


# =====================================================
# VALIDATE ONLY (LEGACY – no descuenta)
# =====================================================
def validate_mass_cuit(user_id: int, cuits_to_process: int) -> Tuple[bool, str]:
    return can_run_mass_cuit(user_id=user_id, cuits_to_process=cuits_to_process)


def validate_bank_extract(user_id: int) -> Tuple[bool, str]:
    return can_run_bank_extract(user_id=user_id)


# =====================================================
# RECORD USAGE (LEGACY – ya no usar para CUIT masivo)
# =====================================================
def record_mass_cuit_usage(user_id: int, amount: int, period: Optional[str] = None) -> None:
    if not user_id:
        raise ValueError("user_id vacío")
    if int(amount) <= 0:
        return

    period = period or get_current_period()
    _ensure_usage_row(user_id, period)

    conn = get_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE usage
                    SET cuit_queries = cuit_queries + %s,
                        last_activity = CURRENT_TIMESTAMP
                    WHERE user_id = %s AND period = %s
                    """,
                    (int(amount), user_id, period),
                )
    finally:
        conn.close()


def record_bank_extract_usage(user_id: int, amount: int = 1, period: Optional[str] = None) -> None:
    if not user_id:
        raise ValueError("user_id vacío")
    if int(amount) <= 0:
        return

    period = period or get_current_period()
    _ensure_usage_row(user_id, period)

    conn = get_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE usage
                    SET bank_extracts = bank_extracts + %s,
                        last_activity = CURRENT_TIMESTAMP
                    WHERE user_id = %s AND period = %s
                    """,
                    (int(amount), user_id, period),
                )
    finally:
        conn.close()


# =====================================================
# Usage status (Admin Overview)
# =====================================================
def get_usage_status(user_id: int) -> Dict[str, Any]:
    period = get_current_period()
    _ensure_usage_row(user_id, period)

    conn = get_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        COALESCE(cuit_queries, 0)  AS cuit_used,
                        COALESCE(bank_extracts, 0) AS bank_used,
                        last_activity
                    FROM usage
                    WHERE user_id = %s AND period = %s
                    LIMIT 1
                    """,
                    (user_id, period),
                )
                row = cur.fetchone()
    finally:
        conn.close()

    used = dict(row) if row else {"cuit_used": 0, "bank_used": 0, "last_activity": None}

    limits = get_effective_limits(user_id, period)
    days_left = days_until_expiration(user_id)

    base_cuit = int(limits.get("base_cuit", 0) or 0)
    extra_cuit = int(limits.get("extra_cuit", 0) or 0)
    total_cuit = int(limits.get("total_cuit", 0) or 0)

    base_bank = int(limits.get("base_bank", 0) or 0)
    extra_bank = int(limits.get("extra_bank", 0) or 0)
    total_bank = int(limits.get("total_bank", 0) or 0)

    cuit_display = f"{used['cuit_used']} / {base_cuit} +{extra_cuit}"
    bank_display = f"{used['bank_used']} / {base_bank} +{extra_bank}"

    return {
        "period": period,
        "plan_code": limits.get("plan_code"),
        "plan_name": limits.get("plan_name"),
        "cuit_used": int(used["cuit_used"]),
        "bank_used": int(used["bank_used"]),
        "base_cuit": base_cuit,
        "extra_cuit": extra_cuit,
        "total_cuit": total_cuit,
        "base_bank": base_bank,
        "extra_bank": extra_bank,
        "total_bank": total_bank,
        "cuit_display": cuit_display,
        "bank_display": bank_display,
        "days_left": days_left,
        "last_activity": used.get("last_activity"),
    }


# =====================================================
# Expiration alert
# =====================================================
def should_show_expiration_alert(user_id: int) -> bool:
    dl = days_until_expiration(user_id)
    return dl in (7, 5)


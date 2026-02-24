from datetime import datetime
from typing import Optional, Dict

from auth.db import get_connection
from auth.limits import get_current_period


def _utcnow():
    # Si tu DB usa timestamptz, esto igual entra bien como UTC.
    return datetime.utcnow()


def _normalize_period(period: Optional[str]) -> str:
    return period or get_current_period()


def _normalize_amount(amount: int) -> int:
    try:
        amount = int(amount)
    except Exception:
        amount = 0
    return max(0, amount)


# =====================================================
# Obtener uso del mes (para debug / panel admin)
# =====================================================
def get_month_usage(user_id: int, period: Optional[str] = None) -> Dict[str, int]:
    period = _normalize_period(period)

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    COALESCE(cuit_queries, 0)  AS cuit_queries,
                    COALESCE(bank_extracts, 0) AS bank_extracts,
                    COALESCE(fiscal_checks, 0) AS fiscal_checks
                FROM usage
                WHERE user_id = %s AND period = %s
                LIMIT 1
            """, (user_id, period))
            row = cur.fetchone()

        if not row:
            return {"cuit_queries": 0, "bank_extracts": 0, "fiscal_checks": 0}

        return {
            "cuit_queries": int(row.get("cuit_queries", 0)),
            "bank_extracts": int(row.get("bank_extracts", 0)),
            "fiscal_checks": int(row.get("fiscal_checks", 0)),
        }
    finally:
        conn.close()


# =====================================================
# Incrementar uso CUIT (masivo)
# =====================================================
def increment_cuit_usage(user_id: int, amount: int, period: Optional[str] = None) -> None:
    period = _normalize_period(period)
    amount = _normalize_amount(amount)
    if amount <= 0:
        return

    conn = get_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO usage (user_id, period, cuit_queries, bank_extracts, fiscal_checks, last_activity)
                    VALUES (%s, %s, %s, 0, 0, %s)
                    ON CONFLICT (user_id, period)
                    DO UPDATE SET
                        cuit_queries  = usage.cuit_queries + EXCLUDED.cuit_queries,
                        last_activity = EXCLUDED.last_activity
                """, (user_id, period, amount, _utcnow()))
    finally:
        conn.close()


# =====================================================
# Incrementar uso Extractores Bancarios
# =====================================================
def increment_bank_usage(user_id: int, amount: int, period: Optional[str] = None) -> None:
    period = _normalize_period(period)
    amount = _normalize_amount(amount)
    if amount <= 0:
        return

    conn = get_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO usage (user_id, period, cuit_queries, bank_extracts, fiscal_checks, last_activity)
                    VALUES (%s, %s, 0, %s, 0, %s)
                    ON CONFLICT (user_id, period)
                    DO UPDATE SET
                        bank_extracts = usage.bank_extracts + EXCLUDED.bank_extracts,
                        last_activity = EXCLUDED.last_activity
                """, (user_id, period, amount, _utcnow()))
    finally:
        conn.close()


# =====================================================
# (Opcional) Incrementar checks fiscales (Gestión fiscal)
# =====================================================
def increment_fiscal_checks(user_id: int, amount: int = 1, period: Optional[str] = None) -> None:
    period = _normalize_period(period)
    amount = _normalize_amount(amount)
    if amount <= 0:
        return

    conn = get_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO usage (user_id, period, cuit_queries, bank_extracts, fiscal_checks, last_activity)
                    VALUES (%s, %s, 0, 0, %s, %s)
                    ON CONFLICT (user_id, period)
                    DO UPDATE SET
                        fiscal_checks = usage.fiscal_checks + EXCLUDED.fiscal_checks,
                        last_activity = EXCLUDED.last_activity
                """, (user_id, period, amount, _utcnow()))
    finally:
        conn.close()

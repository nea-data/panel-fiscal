# auth/service.py

from datetime import datetime

from auth.db import get_connection
from auth.limits import (
    can_run_mass_cuit,
    can_run_bank_extract,
    get_current_period,
)

# ======================================================
# USO / CONTADORES
# ======================================================

def _ensure_usage_row(user_id: int, period: str):
    """
    Crea la fila de usage si no existe para el período.
    """
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT id FROM usage
        WHERE user_id = ? AND period = ?
    """, (user_id, period))

    if cur.fetchone() is None:
        cur.execute("""
            INSERT INTO usage (
                user_id,
                period,
                cuit_queries,
                bank_extracts,
                fiscal_checks,
                last_activity
            )
            VALUES (?, ?, 0, 0, 0, CURRENT_TIMESTAMP)
        """, (user_id, period))

        conn.commit()


# ======================================================
# INCREMENTOS
# ======================================================

def increment_cuit_usage(user_id: int, amount: int):
    """
    Incrementa el uso de CUITs masivos.
    """
    conn = get_connection()
    cur = conn.cursor()

    period = get_current_period()
    _ensure_usage_row(user_id, period)

    cur.execute("""
        UPDATE usage
        SET cuit_queries = cuit_queries + ?,
            last_activity = CURRENT_TIMESTAMP
        WHERE user_id = ?
          AND period = ?
    """, (amount, user_id, period))

    conn.commit()


def increment_bank_extract(user_id: int):
    """
    Incrementa el uso de extractos bancarios.
    """
    conn = get_connection()
    cur = conn.cursor()

    period = get_current_period()
    _ensure_usage_row(user_id, period)

    cur.execute("""
        UPDATE usage
        SET bank_extracts = bank_extracts + 1,
            last_activity = CURRENT_TIMESTAMP
        WHERE user_id = ?
          AND period = ?
    """, (user_id, period))

    conn.commit()


# ======================================================
# API PÚBLICA (USO CONTROLADO)
# ======================================================

def run_mass_cuit_check(user_id: int, cuits_to_process: int):
    """
    Punto de entrada ÚNICO para consultas masivas de CUITs.

    - Valida límites
    - Registra uso
    - Lanza excepción si no puede ejecutar
    """

    can_run, message = can_run_mass_cuit(
        user_id=user_id,
        cuits_to_process=cuits_to_process
    )

    if not can_run:
        raise PermissionError(message)

    increment_cuit_usage(
        user_id=user_id,
        amount=cuits_to_process
    )

    return True


def run_bank_extract(user_id: int):
    """
    Punto de entrada ÚNICO para extracción de extractos bancarios.
    """

    can_run, message = can_run_bank_extract(user_id)

    if not can_run:
        raise PermissionError(message)

    increment_bank_extract(user_id)

    return True


# ======================================================
# CONSULTA DE USO (PARA EL PANEL)
# ======================================================

def get_usage_status(user_id: int) -> dict:
    """
    Devuelve el uso actual vs límites del plan activo.
    """
    conn = get_connection()
    cur = conn.cursor()

    period = get_current_period()

    cur.execute("""
        SELECT
            COALESCE(u.cuit_queries, 0) AS cuit_used,
            COALESCE(u.bank_extracts, 0) AS bank_used,
            p.max_cuit_queries,
            p.max_bank_extracts
        FROM users us
        JOIN subscriptions s ON s.user_id = us.id
        JOIN plans p ON p.id = s.plan_id
        LEFT JOIN usage u
            ON u.user_id = us.id AND u.period = ?
        WHERE us.id = ?
          AND s.status = 'active'
    """, (period, user_id))

    row = cur.fetchone()

    return dict(row) if row else {}

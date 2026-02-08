from auth.db import get_connection
from auth.limits import (
    can_run_mass_cuit,
    can_run_bank_extract,
    get_current_period,
    get_effective_limits,
)
from auth.subscriptions import days_until_expiration


def _ensure_usage_row(user_id: int, period: str) -> None:
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT id FROM usage
        WHERE user_id = ? AND period = ?
    """, (user_id, period))

    if cur.fetchone() is None:
        cur.execute("""
            INSERT INTO usage (user_id, period, cuit_queries, bank_extracts, fiscal_checks, last_activity)
            VALUES (?, ?, 0, 0, 0, CURRENT_TIMESTAMP)
        """, (user_id, period))
        conn.commit()


def increment_cuit_usage(user_id: int, amount: int) -> None:
    conn = get_connection()
    cur = conn.cursor()

    period = get_current_period()
    _ensure_usage_row(user_id, period)

    cur.execute("""
        UPDATE usage
        SET cuit_queries = cuit_queries + ?,
            last_activity = CURRENT_TIMESTAMP
        WHERE user_id = ? AND period = ?
    """, (int(amount), user_id, period))

    conn.commit()


def increment_bank_extract(user_id: int) -> None:
    conn = get_connection()
    cur = conn.cursor()

    period = get_current_period()
    _ensure_usage_row(user_id, period)

    cur.execute("""
        UPDATE usage
        SET bank_extracts = bank_extracts + 1,
            last_activity = CURRENT_TIMESTAMP
        WHERE user_id = ? AND period = ?
    """, (user_id, period))

    conn.commit()


def run_mass_cuit_check(user_id: int, cuits_to_process: int) -> bool:
    can_run, message = can_run_mass_cuit(user_id=user_id, cuits_to_process=cuits_to_process)
    if not can_run:
        raise PermissionError(message)

    increment_cuit_usage(user_id=user_id, amount=cuits_to_process)
    return True


def run_bank_extract(user_id: int) -> bool:
    can_run, message = can_run_bank_extract(user_id=user_id)
    if not can_run:
        raise PermissionError(message)

    increment_bank_extract(user_id)
    return True


def get_usage_status(user_id: int) -> dict:
    """
    Devuelve: usados + base + extras + totales + days_left
    """
    conn = get_connection()
    cur = conn.cursor()

    period = get_current_period()
    _ensure_usage_row(user_id, period)

    cur.execute("""
        SELECT
            COALESCE(u.cuit_queries, 0) AS cuit_used,
            COALESCE(u.bank_extracts, 0) AS bank_used,
            COALESCE(u.last_activity, NULL) AS last_activity
        FROM usage u
        WHERE u.user_id = ? AND u.period = ?
        LIMIT 1
    """, (user_id, period))

    row = cur.fetchone()
    used = dict(row) if row else {"cuit_used": 0, "bank_used": 0, "last_activity": None}

    limits = get_effective_limits(user_id, period)
    days_left = days_until_expiration(user_id)

    # strings display tipo: 180/200 +50
    cuit_display = f"{used['cuit_used']} / {limits.get('base_cuit', 0)} +{limits.get('extra_cuit', 0)}"
    bank_display = f"{used['bank_used']} / {limits.get('base_bank', 0)} +{limits.get('extra_bank', 0)}"

    return {
        "period": period,
        "plan_code": limits.get("plan_code"),
        "plan_name": limits.get("plan_name"),
        "cuit_used": used["cuit_used"],
        "bank_used": used["bank_used"],
        "base_cuit": limits.get("base_cuit", 0),
        "extra_cuit": limits.get("extra_cuit", 0),
        "total_cuit": limits.get("total_cuit", 0),
        "base_bank": limits.get("base_bank", 0),
        "extra_bank": limits.get("extra_bank", 0),
        "total_bank": limits.get("total_bank", 0),
        "cuit_display": cuit_display,
        "bank_display": bank_display,
        "days_left": days_left,
        "last_activity": used.get("last_activity"),
    }


def should_show_expiration_alert(user_id: int) -> bool:
    dl = days_until_expiration(user_id)
    return dl in (7, 5)

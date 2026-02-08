from auth.db import get_connection


def init_db() -> None:
    """
    Crea tablas si no existen (migración simple).
    No borra nada, no altera columnas existentes.
    """
    conn = get_connection()
    cur = conn.cursor()

    # -------------------------
    # USERS
    # status: pending | active | suspended
    # role: user | admin
    # -------------------------
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT NOT NULL UNIQUE,
        name TEXT DEFAULT '',
        role TEXT NOT NULL DEFAULT 'user',
        status TEXT NOT NULL DEFAULT 'pending',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        last_login_at TEXT
    )
    """)

    # -------------------------
    # PLANS
    # -------------------------
    cur.execute("""
    CREATE TABLE IF NOT EXISTS plans (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT NOT NULL UNIQUE,                 -- FREE | PRO | ...
        name TEXT NOT NULL,
        max_cuit_queries INTEGER,                  -- por mes (YYYY-MM)
        max_bank_extracts INTEGER                  -- por mes (YYYY-MM)
    )
    """)

    # -------------------------
    # SUBSCRIPTIONS (rolling 30 días)
    # status: active | expired | suspended
    # -------------------------
    cur.execute("""
    CREATE TABLE IF NOT EXISTS subscriptions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        plan_id INTEGER NOT NULL,
        status TEXT NOT NULL DEFAULT 'active',
        start_date TEXT NOT NULL,
        end_date TEXT NOT NULL,
        changed_by TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id),
        FOREIGN KEY(plan_id) REFERENCES plans(id)
    )
    """)

    # -------------------------
    # USAGE mensual (YYYY-MM)
    # -------------------------
    cur.execute("""
    CREATE TABLE IF NOT EXISTS usage (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        period TEXT NOT NULL,                      -- YYYY-MM
        cuit_queries INTEGER NOT NULL DEFAULT 0,
        bank_extracts INTEGER NOT NULL DEFAULT 0,
        fiscal_checks INTEGER NOT NULL DEFAULT 0,
        last_activity TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, period),
        FOREIGN KEY(user_id) REFERENCES users(id)
    )
    """)

    # -------------------------
    # EXTRAS por período
    # -------------------------
    cur.execute("""
    CREATE TABLE IF NOT EXISTS usage_extras (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        period TEXT NOT NULL,                      -- YYYY-MM
        extra_cuit_queries INTEGER NOT NULL DEFAULT 0,
        extra_bank_extracts INTEGER NOT NULL DEFAULT 0,
        granted_by TEXT,
        note TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, period),
        FOREIGN KEY(user_id) REFERENCES users(id)
    )
    """)

    # -------------------------
    # AUDITORIA admin (opcional pero útil)
    # -------------------------
    cur.execute("""
    CREATE TABLE IF NOT EXISTS admin_actions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        admin_email TEXT,
        action TEXT,
        target_user_id INTEGER,
        details TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()

    # Seed de planes mínimos
    seed_plans()
    conn.commit()


def seed_plans() -> None:
    """
    Crea planes base si no existen.
    Ajustá límites a gusto.
    """
    conn = get_connection()
    cur = conn.cursor()

    # FREE: por defecto sin masivo ni extractores (0)
    cur.execute("""
    INSERT OR IGNORE INTO plans (code, name, max_cuit_queries, max_bank_extracts)
    VALUES ('FREE', 'Free', 0, 0)
    """)

    cur.execute("""
    INSERT OR IGNORE INTO plans (code, name, max_cuit_queries, max_bank_extracts)
    VALUES ('PRO', 'Pro', 200, 20)
    """)

    cur.execute("""
    INSERT OR IGNORE INTO plans (code, name, max_cuit_queries, max_bank_extracts)
    VALUES ('STUDIO', 'Estudio', 800, 100)
    """)

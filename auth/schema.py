from auth.db import get_connection

def init_db() -> None:
    """
    Crea las tablas en Supabase si no existen.
    """
    conn = get_connection()
    cur = conn.cursor()

    # Tabla de Usuarios (Sintaxis Postgres)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id SERIAL PRIMARY KEY,
        correo_electronico TEXT NOT NULL UNIQUE,
        nombre TEXT DEFAULT '',
        role TEXT NOT NULL DEFAULT 'usuario',
        estado TEXT NOT NULL DEFAULT 'activo',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_login_at TIMESTAMP
    )
    """)

    # Tabla de Planes
    cur.execute("""
    CREATE TABLE IF NOT EXISTS planes (
        id SERIAL PRIMARY KEY,
        code TEXT NOT NULL UNIQUE,
        name TEXT NOT NULL,
        max_cuit_queries INTEGER,
        max_bank_extracts INTEGER
    )
    """)

    # Tabla de Suscripciones
    cur.execute("""
    CREATE TABLE IF NOT EXISTS suscripciones (
        id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL REFERENCES usuarios(id),
        plan_id INTEGER NOT NULL REFERENCES planes(id),
        status TEXT NOT NULL DEFAULT 'active',
        start_date DATE NOT NULL,
        end_date DATE NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    seed_plans()
    conn.commit()
    cur.close()
    conn.close()

def seed_plans() -> None:
    conn = get_connection()
    cur = conn.cursor()
    
    # Sintaxis ON CONFLICT para Postgres
    planes = [
        ('FREE', 'Free', 0, 0),
        ('PRO', 'Pro', 200, 20),
        ('STUDIO', 'Estudio', 800, 100)
    ]
    
    for p in planes:
        cur.execute("""
        INSERT INTO planes (code, name, max_cuit_queries, max_bank_extracts)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (code) DO NOTHING
        """, p)
    
    conn.commit()
    cur.close()
    conn.close()

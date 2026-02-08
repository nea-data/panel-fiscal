import sqlite3
from pathlib import Path

DB_PATH = Path("data/auth.db")


def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


# Alias por compatibilidad si ya llamabas get_conn()
def get_conn() -> sqlite3.Connection:
    return get_connection()

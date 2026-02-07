import sqlite3
from pathlib import Path

DB_PATH = Path("data/auth.db")

def get_conn():
    DB_PATH.parent.mkdir(exist_ok=True)
    return sqlite3.connect(DB_PATH, check_same_thread=False)

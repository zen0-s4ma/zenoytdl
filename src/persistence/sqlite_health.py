import sqlite3
from pathlib import Path


def sqlite_smoke_check(db_path: str) -> bool:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(path)
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        cursor.close()
        return True
    finally:
        connection.close()

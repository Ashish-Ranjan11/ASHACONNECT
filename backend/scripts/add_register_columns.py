import sqlite3
from pathlib import Path

DB_PATH = Path("awams.db")

COLUMNS = {
    "education": "TEXT DEFAULT ''",
    "occupation_type": "TEXT DEFAULT ''",
    "occupation_detail": "TEXT DEFAULT ''",
    "marital_status": "TEXT DEFAULT ''",
    "religion": "TEXT DEFAULT ''",
    "family_baby_count": "INTEGER DEFAULT 0",
    "last_baby_birth_date": "DATE",
}


def column_exists(cursor, table, column):
    cursor.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cursor.fetchall())


def main():
    if not DB_PATH.exists():
        print("awams.db not found. Run this inside backend folder.")
        return

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    for column, definition in COLUMNS.items():
        if not column_exists(cur, "beneficiaries", column):
            cur.execute(f"ALTER TABLE beneficiaries ADD COLUMN {column} {definition}")
            print(f"Added column: {column}")
        else:
            print(f"Already exists: {column}")

    conn.commit()
    conn.close()

    print("ASHA register columns added successfully.")


if __name__ == "__main__":
    main()

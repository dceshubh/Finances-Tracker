import sqlite3
import os
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "finance.db"


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('self', 'spouse')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            profile_id INTEGER NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
            institution TEXT NOT NULL,
            account_type TEXT NOT NULL CHECK(account_type IN ('checking', 'savings', 'credit_card')),
            account_name TEXT NOT NULL,
            last_four TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS statements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
            filename TEXT NOT NULL,
            file_hash TEXT,
            period_start DATE,
            period_end DATE,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending', 'parsed', 'failed', 'warning')),
            error_message TEXT
        );

        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
            statement_id INTEGER REFERENCES statements(id) ON DELETE SET NULL,
            date DATE NOT NULL,
            description TEXT NOT NULL,
            amount REAL NOT NULL,
            tx_type TEXT NOT NULL CHECK(tx_type IN ('credit', 'debit')),
            category TEXT DEFAULT 'uncategorized',
            hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE UNIQUE INDEX IF NOT EXISTS idx_tx_hash ON transactions(hash);
        CREATE INDEX IF NOT EXISTS idx_tx_date ON transactions(date);
        CREATE INDEX IF NOT EXISTS idx_tx_account ON transactions(account_id);
        CREATE INDEX IF NOT EXISTS idx_tx_category ON transactions(category);
    """)

    # --- Migration: add file_hash column to statements if missing ---
    cols = [r["name"] for r in conn.execute("PRAGMA table_info(statements)").fetchall()]
    if "file_hash" not in cols:
        conn.execute("ALTER TABLE statements ADD COLUMN file_hash TEXT")

    # Unique index on file_hash (NULLs allowed — SQLite treats each NULL as distinct)
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_stmt_file_hash ON statements(file_hash)")

    conn.commit()
    conn.close()

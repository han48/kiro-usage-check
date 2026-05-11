"""Database Writer module for storing account information in SQLite."""

import sqlite3
from datetime import datetime
from typing import Optional

from src.extractor import AccountInfo


class DatabaseWriter:
    """Manages SQLite database operations for storing account information."""

    def __init__(self, db_path: str = "dashboard/kiro_accounts.db"):
        """Initialize and create tables (accounts + credits_history) if not exists.

        Args:
            db_path: Path to the SQLite database file.
        """
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.execute("PRAGMA foreign_keys = ON")
        self._create_tables()

    def _create_tables(self) -> None:
        """Create the accounts and credits_history tables if they don't exist."""
        cursor = self.conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS accounts (
                profile_name TEXT PRIMARY KEY,
                email TEXT,
                user_id TEXT,
                credits_used REAL,
                credits_total REAL,
                plan_name TEXT,
                reset_date TEXT,
                extracted_at TEXT NOT NULL
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS credits_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                profile_name TEXT NOT NULL,
                credits_used REAL,
                credits_total REAL,
                plan_name TEXT,
                extracted_at TEXT NOT NULL,
                FOREIGN KEY (profile_name) REFERENCES accounts(profile_name)
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS scrape_errors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                profile_name TEXT NOT NULL,
                error_message TEXT,
                attempts INTEGER,
                failed_at TEXT NOT NULL
            )
        """)
        self.conn.commit()

    def save_account(self, profile_name: str, info: AccountInfo, extracted_at: str) -> None:
        """Insert or update account record in accounts table.

        Also inserts a new record into credits_history for tracking over time.

        Args:
            profile_name: The Chrome profile name/path identifier.
            info: AccountInfo dataclass with extracted account data.
            extracted_at: ISO timestamp of when the CLI run started.
        """
        cursor = self.conn.cursor()

        # Upsert into accounts table
        cursor.execute("""
            INSERT OR REPLACE INTO accounts
                (profile_name, email, user_id, credits_used, credits_total, plan_name, reset_date, extracted_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            profile_name,
            info.email,
            info.user_id,
            info.credits_used,
            info.credits_total,
            info.plan_name,
            info.reset_date,
            extracted_at,
        ))

        # Insert into credits_history
        cursor.execute("""
            INSERT INTO credits_history
                (profile_name, credits_used, credits_total, plan_name, extracted_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            profile_name,
            info.credits_used,
            info.credits_total,
            info.plan_name,
            extracted_at,
        ))

        self.conn.commit()

    def get_history(self, profile_name: str) -> list[dict]:
        """Get credits history for a specific profile, ordered by time.

        Args:
            profile_name: The Chrome profile name/path identifier.

        Returns:
            List of dicts with keys: id, profile_name, credits_used,
            credits_total, plan_name, extracted_at. Ordered by extracted_at ascending.
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT id, profile_name, credits_used, credits_total, plan_name, extracted_at
            FROM credits_history
            WHERE profile_name = ?
            ORDER BY extracted_at ASC
        """, (profile_name,))

        columns = ["id", "profile_name", "credits_used", "credits_total", "plan_name", "extracted_at"]
        rows = cursor.fetchall()
        return [dict(zip(columns, row)) for row in rows]

    def close(self) -> None:
        """Close database connection."""
        self.conn.close()

    def save_error(self, profile_name: str, error_message: str, attempts: int) -> None:
        """Save a persistent scraping error to the database."""
        failed_at = datetime.now().isoformat()
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO scrape_errors (profile_name, error_message, attempts, failed_at)
            VALUES (?, ?, ?, ?)
        """, (profile_name, error_message, attempts, failed_at))
        self.conn.commit()

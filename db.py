import sqlite3
import os
from datetime import datetime

DB_PATH = "octo_jules.db"

def get_connection():
    return sqlite3.connect(DB_PATH)

def init_db():
    """Initialize the database schema."""
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                issue_number INTEGER,
                issue_title TEXT,
                repo TEXT,
                state TEXT,
                pr_number INTEGER,
                pr_url TEXT,
                created_at TIMESTAMP,
                updated_at TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        # Initialize default settings
        conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('paused', 'false')")
        conn.commit()

def save_session(session_id, issue_number, title, repo, state="CREATED"):
    """Create or update a session record."""
    now = datetime.now().isoformat()
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO sessions (id, issue_number, issue_title, repo, state, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                state=excluded.state,
                updated_at=excluded.updated_at
        """, (session_id, issue_number, title, repo, state, now, now))
        conn.commit()

def update_session_pr(session_id, pr_number, pr_url):
    """Update PR details for a session."""
    now = datetime.now().isoformat()
    with get_connection() as conn:
        conn.execute("""
            UPDATE sessions SET 
                pr_number = ?, 
                pr_url = ?, 
                updated_at = ?
            WHERE id = ?
        """, (pr_number, pr_url, now, session_id))
        conn.commit()

def update_session_state(session_id, state):
    """Update the state of a session."""
    now = datetime.now().isoformat()
    with get_connection() as conn:
        conn.execute("""
            UPDATE sessions SET state = ?, updated_at = ? WHERE id = ?
        """, (state, now, session_id))
        conn.commit()

def get_session_by_issue(issue_number, repo):
    """Retrieve the most recent session by issue number and repo."""
    with get_connection() as conn:
        cursor = conn.execute(
            "SELECT * FROM sessions WHERE issue_number = ? AND repo = ? ORDER BY created_at DESC", 
            (issue_number, repo)
        )
        return cursor.fetchone()

def get_active_sessions(repo):
    """Retrieve all sessions that are not merged or failed."""
    with get_connection() as conn:
        cursor = conn.execute(
            "SELECT * FROM sessions WHERE repo = ? AND state NOT IN ('MERGED', 'FAILED')", 
            (repo,)
        )
        return cursor.fetchall()

def is_paused():
    """Check if the orchestrator is paused."""
    with get_connection() as conn:
        cursor = conn.execute("SELECT value FROM settings WHERE key = 'paused'")
        row = cursor.fetchone()
        return row[0].lower() == 'true' if row else False

def set_paused(paused: bool):
    """Set the paused state."""
    val = 'true' if paused else 'false'
    with get_connection() as conn:
        conn.execute("UPDATE settings SET value = ? WHERE key = 'paused'", (val,))
        conn.commit()
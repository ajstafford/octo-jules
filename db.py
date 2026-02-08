import os
import psycopg2
import time
import logging
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

def get_connection(retries=5, delay=2):
    """Establish a connection to the database with retry logic."""
    host = os.getenv("DB_HOST", "localhost")
    database = os.getenv("DB_NAME", "octo_jules")
    user = os.getenv("DB_USER", "postgres")
    password = os.getenv("DB_PASSWORD")
    port = os.getenv("DB_PORT", "5432")

    if not password:
        raise ValueError("DB_PASSWORD environment variable is not set.")

    for attempt in range(retries):
        try:
            conn = psycopg2.connect(
                host=host,
                database=database,
                user=user,
                password=password,
                port=port
            )
            return conn
        except psycopg2.OperationalError as e:
            if attempt < retries - 1:
                logger.warning(f"Database connection failed (attempt {attempt + 1}/{retries}). Retrying in {delay}s...")
                time.sleep(delay)
            else:
                logger.error("Failed to connect to database after multiple attempts.")
                raise e

def init_db():
    """Initialize the database schema."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
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
            cur.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)
            # Create indexes for performance
            cur.execute("CREATE INDEX IF NOT EXISTS idx_sessions_repo_state ON sessions (repo, state)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_sessions_issue_repo ON sessions (issue_number, repo)")
            
            # Initialize default settings (paused=true for safety per user request)
            cur.execute("INSERT INTO settings (key, value) VALUES ('paused', 'true') ON CONFLICT (key) DO NOTHING")
        conn.commit()
    finally:
        conn.close()

def save_session(session_id, issue_number, title, repo, state="CREATED"):
    """Create or update a session record."""
    now = datetime.now()
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO sessions (id, issue_number, issue_title, repo, state, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT(id) DO UPDATE SET
                    state=EXCLUDED.state,
                    updated_at=EXCLUDED.updated_at
            """, (session_id, issue_number, title, repo, state, now, now))
        conn.commit()
    finally:
        conn.close()

def update_session_pr(session_id, pr_number, pr_url):
    """Update PR details for a session."""
    now = datetime.now()
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE sessions SET 
                    pr_number = %s, 
                    pr_url = %s, 
                    updated_at = %s
                WHERE id = %s
            """, (pr_number, pr_url, now, session_id))
        conn.commit()
    finally:
        conn.close()

def update_session_state(session_id, state):
    """Update the state of a session."""
    now = datetime.now()
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE sessions SET state = %s, updated_at = %s WHERE id = %s
            """, (state, now, session_id))
        conn.commit()
    finally:
        conn.close()

def get_session_by_issue(issue_number, repo):
    """Retrieve the most recent session by issue number and repo."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM sessions WHERE issue_number = %s AND repo = %s ORDER BY created_at DESC", 
                (issue_number, repo)
            )
            return cur.fetchone()
    finally:
        conn.close()

def get_active_sessions(repo):
    """Retrieve all sessions that are not merged or failed."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM sessions WHERE repo = %s AND state NOT IN ('MERGED', 'FAILED')", 
                (repo,)
            )
            return cur.fetchall()
    finally:
        conn.close()

def is_paused():
    """Check if the orchestrator is paused."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT value FROM settings WHERE key = 'paused'")
            row = cur.fetchone()
            return row[0].lower() == 'true' if row else False
    finally:
        conn.close()

def set_paused(paused: bool):
    """Set the paused state."""
    val = 'true' if paused else 'false'
    set_setting('paused', val)

def set_setting(key, value):
    """Set a generic setting."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO settings (key, value) VALUES (%s, %s)
                ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
            """, (key, str(value)))
        conn.commit()
    finally:
        conn.close()

def get_setting(key):
    """Retrieve a generic setting."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT value FROM settings WHERE key = %s", (key,))
            row = cur.fetchone()
            return row[0] if row else None
    finally:
        conn.close()

def delete_setting(key):
    """Delete a generic setting."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM settings WHERE key = %s", (key,))
        conn.commit()
    finally:
        conn.close()
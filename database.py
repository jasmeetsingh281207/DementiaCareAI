"""
DementiaCareAI
SQLite Database Layer

Responsibilities:
- Database initialization
- SQLite connections
- Generic CRUD helpers
- Conversation persistence
- Memory media persistence

This module intentionally contains no AI logic.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from contextlib import contextmanager
from datetime import datetime
from typing import Any


# =========================================================
# PATHS
# =========================================================

BASE_DIR = Path(__file__).resolve().parent

DATA_DIR = BASE_DIR / "data"

DATABASE_PATH = DATA_DIR / "dementiacare.db"


# =========================================================
# TIME
# =========================================================

def _now() -> str:
    return datetime.now().isoformat()


# =========================================================
# DATABASE INITIALIZATION
# =========================================================

def initialize_database() -> None:
    """
    Create the database and required tables.

    Safe to call every time the application starts.
    """

    DATA_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    with get_connection() as connection:

        connection.execute(
            "PRAGMA foreign_keys = ON"
        )

        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS patient (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL DEFAULT 'Patient',
                preferred_language TEXT NOT NULL DEFAULT 'English',
                caregiver_name TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );


            CREATE TABLE IF NOT EXISTS patient_lists (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id INTEGER NOT NULL,
                list_type TEXT NOT NULL,
                value TEXT NOT NULL,
                created_at TEXT NOT NULL,

                FOREIGN KEY (patient_id)
                    REFERENCES patient(id)
                    ON DELETE CASCADE
            );


            CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY,
                category TEXT NOT NULL,
                name TEXT NOT NULL,
                relationship TEXT,
                description TEXT,
                event_date TEXT,
                tags TEXT NOT NULL DEFAULT '[]',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );


            CREATE TABLE IF NOT EXISTS memory_media (
                id TEXT PRIMARY KEY,
                memory_id TEXT NOT NULL,
                media_type TEXT NOT NULL,
                filename TEXT NOT NULL,
                stored_filename TEXT NOT NULL,
                file_path TEXT NOT NULL,
                caption TEXT,
                created_at TEXT NOT NULL,

                FOREIGN KEY (memory_id)
                    REFERENCES memories(id)
                    ON DELETE CASCADE
            );


            CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message TEXT NOT NULL,
                reminder_time TEXT NOT NULL,
                created_at TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'scheduled'
            );


            CREATE TABLE IF NOT EXISTS cognitive_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                activity_type TEXT NOT NULL,
                result TEXT NOT NULL,
                score REAL NOT NULL DEFAULT 0,
                memory_id TEXT,
                activity_id TEXT,
                answer TEXT,
                timestamp TEXT NOT NULL,

                FOREIGN KEY (memory_id)
                    REFERENCES memories(id)
                    ON DELETE SET NULL
            );


            CREATE TABLE IF NOT EXISTS activities (
                id TEXT PRIMARY KEY,
                activity_type TEXT NOT NULL,
                memory_id TEXT,
                question TEXT,
                result TEXT,
                created_at TEXT NOT NULL,
                completed_at TEXT,

                FOREIGN KEY (memory_id)
                    REFERENCES memories(id)
                    ON DELETE SET NULL
            );


            CREATE TABLE IF NOT EXISTS companion_state (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TEXT NOT NULL
            );


            CREATE TABLE IF NOT EXISTS conversation_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL DEFAULT 'default',
                role TEXT NOT NULL,
                message TEXT NOT NULL,
                created_at TEXT NOT NULL
            );


            CREATE INDEX IF NOT EXISTS idx_conversation_created
            ON conversation_messages(created_at);


            CREATE INDEX IF NOT EXISTS idx_memories_category
            ON memories(category);


            CREATE INDEX IF NOT EXISTS idx_memory_media_memory
            ON memory_media(memory_id);


            CREATE INDEX IF NOT EXISTS idx_reminders_time
            ON reminders(reminder_time);


            CREATE INDEX IF NOT EXISTS idx_reminders_status
            ON reminders(status);


            CREATE INDEX IF NOT EXISTS idx_cognitive_timestamp
            ON cognitive_records(timestamp);


            CREATE INDEX IF NOT EXISTS idx_activities_created
            ON activities(created_at);


            CREATE INDEX IF NOT EXISTS idx_activities_memory
            ON activities(memory_id);
            """
        )

        # Safe migrations for databases created by earlier releases.
        columns = {row["name"] for row in connection.execute("PRAGMA table_info(conversation_messages)")}
        if "session_id" not in columns:
            connection.execute("ALTER TABLE conversation_messages ADD COLUMN session_id TEXT NOT NULL DEFAULT 'default'")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_conversation_session_created ON conversation_messages(session_id, id)")

        # -------------------------------------------------
        # DEFAULT PATIENT
        # -------------------------------------------------

        patient = connection.execute(
            """
            SELECT id
            FROM patient
            ORDER BY id
            LIMIT 1
            """
        ).fetchone()

        if patient is None:

            now = _now()

            connection.execute(
                """
                INSERT INTO patient (
                    name,
                    preferred_language,
                    caregiver_name,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    "Patient",
                    "English",
                    None,
                    now,
                    now,
                ),
            )


# =========================================================
# CONNECTION
# =========================================================

def get_connection() -> sqlite3.Connection:
    """
    Return a configured SQLite connection.
    """

    DATA_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    connection = sqlite3.connect(
        DATABASE_PATH,
        timeout=30,
        check_same_thread=False,
    )

    connection.row_factory = sqlite3.Row

    connection.execute(
        "PRAGMA foreign_keys = ON"
    )

    connection.execute(
        "PRAGMA journal_mode = WAL"
    )

    connection.execute(
        "PRAGMA busy_timeout = 30000"
    )

    return connection


@contextmanager
def database_connection():
    """
    Transaction-safe database context.
    """

    connection = get_connection()

    try:

        yield connection

        connection.commit()

    except Exception:

        connection.rollback()

        raise

    finally:

        connection.close()


# =========================================================
# GENERIC DATABASE HELPERS
# =========================================================

def execute(
    query: str,
    parameters: tuple | list = (),
) -> int:

    with database_connection() as connection:

        cursor = connection.execute(
            query,
            parameters,
        )

        return cursor.lastrowid


def fetch_one(
    query: str,
    parameters: tuple | list = (),
) -> dict[str, Any] | None:

    with database_connection() as connection:

        cursor = connection.execute(
            query,
            parameters,
        )

        row = cursor.fetchone()

        if row is None:
            return None

        return dict(row)


def fetch_all(
    query: str,
    parameters: tuple | list = (),
) -> list[dict[str, Any]]:

    with database_connection() as connection:

        cursor = connection.execute(
            query,
            parameters,
        )

        rows = cursor.fetchall()

        return [
            dict(row)
            for row in rows
        ]


# =========================================================
# CONVERSATION
# =========================================================

def save_conversation_message(
    role: str,
    message: str,
    session_id: str | None = None,
) -> int:
    """
    Permanently save a conversation message.
    """

    if role not in {
        "user",
        "assistant",
    }:
        raise ValueError(
            "Conversation role must be "
            "'user' or 'assistant'."
        )

    if not message:
        raise ValueError(
            "Conversation message is required."
        )

    return execute(
        """
        INSERT INTO conversation_messages (
            session_id,
            role,
            message,
            created_at
        )
        VALUES (?, ?, ?, ?)
        """,
        (
            session_id or "default",
            role,
            str(message),
            _now(),
        ),
    )


def get_conversation_history(
    limit: int = 20,
    session_id: str | None = None,
) -> list[dict[str, Any]]:
    """
    Return the most recent conversation messages
    in chronological order.
    """

    limit = max(
        1,
        min(int(limit), 100),
    )

    rows = fetch_all(
        """
        SELECT
            id,
            role,
            message,
            created_at
        FROM conversation_messages
        WHERE session_id = ?
        ORDER BY id DESC
        LIMIT ?
        """,
        (session_id or "default", limit),
    )

    rows.reverse()

    return rows


def clear_conversation_history() -> bool:

    execute(
        """
        DELETE FROM conversation_messages
        """
    )

    return True


# =========================================================
# MEMORY MEDIA
# =========================================================

def add_memory_media(
    memory_id: str,
    file_path: str,
    media_type: str,
    caption: str | None = None,
    filename: str | None = None,
    stored_filename: str | None = None,
) -> str:
    """
    Add media attached to a memory.

    filename and stored_filename are optional for backward
    compatibility. When omitted, they are derived from
    file_path.
    """

    if not memory_id:
        raise ValueError(
            "Memory ID is required."
        )

    if not file_path:
        raise ValueError(
            "File path is required."
        )

    if media_type not in {
        "photo",
        "video",
    }:
        raise ValueError(
            "Media type must be 'photo' or 'video'."
        )

    path = Path(file_path)

    if not filename:
        filename = path.name or "media"

    if not stored_filename:
        stored_filename = path.name or filename

    media_id = (
        f"media_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
    )

    execute(
        """
        INSERT INTO memory_media (
            id,
            memory_id,
            media_type,
            filename,
            stored_filename,
            file_path,
            caption,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            media_id,
            memory_id,
            media_type,
            filename,
            stored_filename,
            str(file_path),
            caption,
            _now(),
        ),
    )

    return media_id


def get_memory_media(
    memory_id: str,
) -> list[dict[str, Any]]:

    return fetch_all(
        """
        SELECT
            id,
            memory_id,
            media_type,
            filename,
            stored_filename,
            file_path,
            caption,
            created_at
        FROM memory_media
        WHERE memory_id = ?
        ORDER BY created_at ASC
        """,
        (memory_id,),
    )


def delete_memory_media(
    media_id: str,
) -> bool:

    execute(
        """
        DELETE FROM memory_media
        WHERE id = ?
        """,
        (media_id,),
    )

    return True

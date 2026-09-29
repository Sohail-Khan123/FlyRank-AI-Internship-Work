"""
Repository: the ONLY module that talks to the database.

Routes call these functions and never touch SQL or the driver directly, so
swapping storage (memory -> SQLite -> Postgres) never changes the API.
"""

import os
import time
from typing import Optional

import psycopg
from psycopg.rows import dict_row

DATABASE_URL = os.environ.get("DATABASE_URL")

SEED_TASKS = [
    ("Buy milk", False),
    ("Write report", False),
    ("Walk the dog", True),
]


def get_connection() -> psycopg.Connection:
    if not DATABASE_URL:
        raise RuntimeError(
            "DATABASE_URL is not set. Copy .env.example to .env and fill it in."
        )
    return psycopg.connect(DATABASE_URL, row_factory=dict_row)


def init_db(retries: int = 15, delay: float = 1.0) -> None:
    """Create the tasks table if missing; seed 3 tasks only if the table is empty.

    Retries the connection because, on `docker compose up`, the database may
    still be starting when the API boots.
    """
    last_error: Optional[Exception] = None
    for _ in range(retries):
        try:
            with get_connection() as conn:  # commits on success, rolls back on error
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS tasks (
                        id    SERIAL PRIMARY KEY,
                        title TEXT    NOT NULL,
                        done  BOOLEAN NOT NULL DEFAULT FALSE
                    )
                    """
                )
                count = conn.execute("SELECT COUNT(*) AS n FROM tasks").fetchone()["n"]
                if count == 0:
                    # Same transaction as the check: seeding is all-or-nothing.
                    with conn.cursor() as cur:
                        cur.executemany(
                            "INSERT INTO tasks (title, done) VALUES (%s, %s)",
                            SEED_TASKS,
                        )
            return
        except psycopg.OperationalError as exc:
            last_error = exc
            time.sleep(delay)
    raise RuntimeError(f"Could not connect to the database: {last_error}")


def list_tasks() -> list[dict]:
    with get_connection() as conn:
        return conn.execute("SELECT * FROM tasks ORDER BY id").fetchall()


def get_task(task_id: int) -> Optional[dict]:
    with get_connection() as conn:
        return conn.execute("SELECT * FROM tasks WHERE id = %s", (task_id,)).fetchone()


def create_task(title: str) -> dict:
    with get_connection() as conn:
        return conn.execute(
            "INSERT INTO tasks (title, done) VALUES (%s, %s) RETURNING *",
            (title, False),
        ).fetchone()


def update_task(task_id: int, title: str, done: bool) -> Optional[dict]:
    with get_connection() as conn:
        return conn.execute(
            "UPDATE tasks SET title = %s, done = %s WHERE id = %s RETURNING *",
            (title, done, task_id),
        ).fetchone()


def delete_task(task_id: int) -> bool:
    with get_connection() as conn:
        cur = conn.execute("DELETE FROM tasks WHERE id = %s", (task_id,))
        return cur.rowcount > 0


def ping() -> bool:
    with get_connection() as conn:
        return conn.execute("SELECT 1 AS ok").fetchone()["ok"] == 1

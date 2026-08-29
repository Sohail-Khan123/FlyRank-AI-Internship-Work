"""
Task API — a small CRUD API backed by SQLite.

Run with:
    uvicorn main:app --reload --port 8000

Then visit:
    http://localhost:8000/          -> API description
    http://localhost:8000/health    -> health check
    http://localhost:8000/docs      -> Swagger UI (interactive docs)
"""

import sqlite3
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

app = FastAPI(
    title="Task API",
    version="1.0",
    description="A small SQLite-backed CRUD API for managing a to-do list.",
)

DB_PATH = Path(__file__).parent / "tasks.db"


class Task(BaseModel):
    id: int
    title: str
    done: bool = False


class TaskCreate(BaseModel):
    """Body for POST /tasks. Title is required and must be non-empty."""
    title: str = Field(..., description="The task title (required, non-empty)")


class TaskUpdate(BaseModel):
    """Body for PUT /tasks/{id}. Both fields optional, but at least one must be present."""
    title: Optional[str] = Field(None, description="New title")
    done: Optional[bool] = Field(None, description="New done state")


def get_connection() -> sqlite3.Connection:
    """Open a connection to tasks.db and return a row-aware connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    """Create the tasks table if needed and seed 3 example tasks only when empty."""
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id    INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT    NOT NULL,
                done  BOOLEAN NOT NULL DEFAULT 0
            )
            """
        )
        count = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
        if count == 0:
            conn.executemany(
                "INSERT INTO tasks (title, done) VALUES (?, ?)",
                [
                    ("Buy milk", 0),
                    ("Write report", 0),
                    ("Walk the dog", 1),
                ],
            )
        conn.commit()


def row_to_task(row: sqlite3.Row) -> dict:
    return {"id": row["id"], "title": row["title"], "done": bool(row["done"]) }


def error(message: str) -> dict:
    return {"error": message}


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Turn FastAPI's default 422 body-validation errors into 400 Bad Request,
    matching the assignment's status code requirements.
    """
    first = exc.errors()[0]
    field = ".".join(str(p) for p in first["loc"] if p != "body") or "body"
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=error(f"Invalid request body: {field} - {first['msg']}"),
    )


init_db()


@app.get("/", summary="API description")
def root():
    """Describes the API: name, version, available endpoints."""
    return {
        "name": "Task API",
        "version": "1.0",
        "endpoints": ["/tasks"],
    }


@app.get("/health", summary="Health check")
def health():
    """Simple liveness check."""
    return {"status": "ok"}


@app.get("/tasks", summary="List all tasks", response_model=List[Task])
def list_tasks():
    """Return all tasks from the SQLite database."""
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM tasks").fetchall()
    return [row_to_task(r) for r in rows]


@app.get("/tasks/{task_id}", summary="Get a single task", response_model=Task)
def get_task(task_id: int):
    """Return one task by id, or 404 if it doesn't exist."""
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    if row is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=error(f"Task {task_id} not found"),
        )
    return row_to_task(row)


@app.post(
    "/tasks",
    summary="Create a new task",
    status_code=status.HTTP_201_CREATED,
    response_model=Task,
)
def create_task(payload: TaskCreate):
    """Insert a task into SQLite. Title must be present and non-empty, or 400 is returned."""
    title = (payload.title or "").strip()
    if not title:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=error("Title is required and cannot be empty"),
        )

    with get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO tasks (title, done) VALUES (?, ?)",
            (title, 0),
        )
        conn.commit()
        new_id = cursor.lastrowid
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (new_id,)).fetchone()

    return row_to_task(row)


@app.put("/tasks/{task_id}", summary="Update a task", response_model=Task)
def update_task(task_id: int, payload: TaskUpdate):
    """
    Update a task's title and/or done state in the database.
    Unknown id -> 404. Empty/invalid body -> 400.
    """
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if row is None:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content=error(f"Task {task_id} not found"),
            )

        if payload.title is None and payload.done is None:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content=error("Provide at least one of: title, done"),
            )

        new_title = row["title"]
        if payload.title is not None:
            new_title = payload.title.strip()
            if not new_title:
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content=error("Title cannot be empty"),
                )

        new_done = row["done"] if payload.done is None else int(payload.done)
        conn.execute(
            "UPDATE tasks SET title = ?, done = ? WHERE id = ?",
            (new_title, new_done, task_id),
        )
        conn.commit()
        updated = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()

    return row_to_task(updated)


@app.delete("/tasks/{task_id}", summary="Delete a task", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: int):
    """Remove a task row by id via SQL DELETE. Unknown id -> 404."""
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if row is None:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content=error(f"Task {task_id} not found"),
            )
        conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        conn.commit()
    return None

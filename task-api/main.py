"""
Task API — a small in-memory CRUD API built with FastAPI.

Run with:
    uvicorn main:app --reload --port 8000

Then visit:
    http://localhost:8000/          -> API description
    http://localhost:8000/health    -> health check
    http://localhost:8000/docs      -> Swagger UI (interactive docs)
"""

from typing import Optional, List
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

app = FastAPI(
    title="Task API",
    version="1.0",
    description="A small in-memory CRUD API for managing a to-do list.",
)


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# In-memory "database"
# ---------------------------------------------------------------------------

def seed_tasks() -> List[dict]:
    return [
        {"id": 1, "title": "Buy milk", "done": False},
        {"id": 2, "title": "Write report", "done": False},
        {"id": 3, "title": "Walk the dog", "done": True},
    ]


tasks: List[dict] = seed_tasks()
next_id: int = 4


def find_task(task_id: int) -> Optional[dict]:
    return next((t for t in tasks if t["id"] == task_id), None)


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


# ---------------------------------------------------------------------------
# Root & health
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Read
# ---------------------------------------------------------------------------

@app.get("/tasks", summary="List all tasks", response_model=List[Task])
def list_tasks():
    """Return the full list of tasks."""
    return tasks


@app.get("/tasks/{task_id}", summary="Get a single task", response_model=Task)
def get_task(task_id: int):
    """Return one task by id, or 404 if it doesn't exist."""
    task = find_task(task_id)
    if task is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=error(f"Task {task_id} not found"),
        )
    return task


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------

@app.post(
    "/tasks",
    summary="Create a new task",
    status_code=status.HTTP_201_CREATED,
    response_model=Task,
)
def create_task(payload: TaskCreate):
    """Create a task. Title must be present and non-empty, or 400 is returned."""
    global next_id

    title = (payload.title or "").strip()
    if not title:
        raise HTTPException(status_code=400, detail="Title is required and cannot be empty")

    task = {"id": next_id, "title": title, "done": False}
    tasks.append(task)
    next_id += 1
    return task


# ---------------------------------------------------------------------------
# Update
# ---------------------------------------------------------------------------

@app.put("/tasks/{task_id}", summary="Update a task", response_model=Task)
def update_task(task_id: int, payload: TaskUpdate):
    """
    Replace a task's title and/or done state.
    Unknown id -> 404. Empty/invalid body (neither field given, or blank title) -> 400.
    """
    task = find_task(task_id)
    if task is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=error(f"Task {task_id} not found"),
        )

    if payload.title is None and payload.done is None:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=error("Provide at least one of: title, done"),
        )

    if payload.title is not None:
        title = payload.title.strip()
        if not title:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content=error("Title cannot be empty"),
            )
        task["title"] = title

    if payload.done is not None:
        task["done"] = payload.done

    return task


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------

@app.delete("/tasks/{task_id}", summary="Delete a task", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: int):
    """Remove a task by id. Unknown id -> 404."""
    task = find_task(task_id)
    if task is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=error(f"Task {task_id} not found"),
        )
    tasks.remove(task)
    return None

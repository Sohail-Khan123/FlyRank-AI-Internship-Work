"""
Task API — FastAPI routes on top of a Postgres repository.

Same endpoints and behaviour as A1 (memory) and A2 (SQLite). Only the storage
module (repository.py) changed; these routes barely did.

Run locally:   uvicorn main:app --reload --port 8000
Run the stack: docker compose up
"""

from contextlib import asynccontextmanager
from typing import List, Optional

from dotenv import load_dotenv

load_dotenv()  # read .env for local runs (must happen before importing repository)

from fastapi import FastAPI, Request, status  # noqa: E402
from fastapi.exceptions import RequestValidationError  # noqa: E402
from fastapi.responses import JSONResponse, Response  # noqa: E402
from pydantic import BaseModel, Field  # noqa: E402

import repository  # noqa: E402


@asynccontextmanager
async def lifespan(app: FastAPI):
    repository.init_db()
    yield


app = FastAPI(
    title="Task API",
    version="1.0",
    description="A CRUD API for a to-do list, backed by PostgreSQL.",
    lifespan=lifespan,
)


class Task(BaseModel):
    id: int
    title: str
    done: bool = False


class TaskCreate(BaseModel):
    title: str = Field(..., description="The task title (required, non-empty)")


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(None, description="New title")
    done: Optional[bool] = Field(None, description="New done state")


def error(message: str) -> dict:
    return {"error": message}


def not_found(task_id: int) -> JSONResponse:
    return JSONResponse(status_code=404, content=error(f"Task {task_id} not found"))


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """FastAPI's default is 422; the assignment requires 400."""
    first = exc.errors()[0]
    field = ".".join(str(p) for p in first["loc"] if p != "body") or "body"
    return JSONResponse(
        status_code=400,
        content=error(f"Invalid request body: {field} - {first['msg']}"),
    )


@app.get("/", summary="API description")
def root():
    return {"name": "Task API", "version": "1.0", "endpoints": ["/tasks"]}


@app.get("/health", summary="Health check (pings the database)")
def health():
    try:
        repository.ping()
    except Exception:
        return JSONResponse(status_code=503, content={"status": "error", "db": "down"})
    return {"status": "ok", "db": "ok"}


@app.get("/tasks", summary="List all tasks", response_model=List[Task])
def list_tasks():
    return repository.list_tasks()


@app.get("/tasks/{task_id}", summary="Get a single task", response_model=Task)
def get_task(task_id: int):
    task = repository.get_task(task_id)
    return task if task else not_found(task_id)


@app.post("/tasks", summary="Create a new task", status_code=201, response_model=Task)
def create_task(payload: TaskCreate):
    title = payload.title.strip()
    if not title:
        return JSONResponse(status_code=400, content=error("Title is required and cannot be empty"))
    return repository.create_task(title)


@app.put("/tasks/{task_id}", summary="Update a task", response_model=Task)
def update_task(task_id: int, payload: TaskUpdate):
    existing = repository.get_task(task_id)
    if existing is None:
        return not_found(task_id)
    if payload.title is None and payload.done is None:
        return JSONResponse(status_code=400, content=error("Provide at least one of: title, done"))

    title = existing["title"]
    if payload.title is not None:
        title = payload.title.strip()
        if not title:
            return JSONResponse(status_code=400, content=error("Title cannot be empty"))
    done = existing["done"] if payload.done is None else payload.done

    updated = repository.update_task(task_id, title, done)
    return updated if updated else not_found(task_id)


@app.delete("/tasks/{task_id}", summary="Delete a task", status_code=204)
def delete_task(task_id: int):
    if not repository.delete_task(task_id):
        return not_found(task_id)
    return Response(status_code=204)

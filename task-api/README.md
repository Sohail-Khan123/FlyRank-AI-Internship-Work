# Task API — now backed by SQLite

A small CRUD API for managing a to-do list, built with **FastAPI** (Python).
Originally built in-memory for Week 2 (Assignment A1); this version upgrades the
project to a real **SQLite** database using the six assignment stages below.

## Why SQLite

SQLite was chosen because it needs no separate database server: the entire
application data lives in a single file (`tasks.db`) that is created automatically
when the app starts. That keeps the project simple, portable, and easy to run while
still adding durable storage and SQL-based querying.

## Where the database lives

- File: `tasks.db`, created automatically in the project folder the first time the
  app starts.
- The app calls `get_connection()` to open the file and `init_db()` to create the
  `tasks` table if it is missing.
- The database file is ignored by Git via `.gitignore`, so each fresh clone starts
  empty and the app creates a fresh database automatically on first run.

## How to run it

Requires Python 3.10+. `sqlite3` is part of the Python standard library, so no extra
DB driver is needed.

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Start the server (creates tasks.db automatically if missing)
uvicorn main:app --reload --port 8000
```

Then open:
- **http://localhost:8000/** — API description
- **http://localhost:8000/health** — health check
- **http://localhost:8000/docs** — Swagger UI

## Endpoints

| Method | Path            | Description                          | Success  | Errors               |
|--------|-----------------|---------------------------------------|----------|-----------------------|
| GET    | `/`             | API description                       | 200      | —                     |
| GET    | `/health`       | Health check                          | 200      | —                     |
| GET    | `/tasks`        | List all tasks                       | 200      | —                     |
| GET    | `/tasks/{id}`   | Get one task                         | 200      | 404 unknown id        |
| POST   | `/tasks`        | Create a task (`{"title": "..."}`)    | 201      | 400 missing/empty title |
| PUT    | `/tasks/{id}`   | Update a task's `title` and/or `done` | 200      | 400 invalid body, 404 unknown id |
| DELETE | `/tasks/{id}`   | Delete a task                        | 204      | 404 unknown id        |

Task shape: `{ "id": number, "title": string, "done": boolean }`

## Database schema

```sql
CREATE TABLE IF NOT EXISTS tasks (
    id    INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT    NOT NULL,
    done  BOOLEAN NOT NULL DEFAULT 0
);
```

Three example tasks are inserted only if the table is empty, so restarting the server
never duplicates them. All reads and writes use parameterized SQL (`?` placeholders),
which keeps user input safe and consistent with the assignment requirements.

## Example SQL query executed

```sql
SELECT * FROM tasks WHERE done = 1;
```

This returns the completed tasks and mirrors what the API sees in the database.

## Example: curl -i output

```bash
$ curl -i -X POST http://localhost:8000/tasks \
    -H "Content-Type: application/json" \
    -d '{"title":"Buy eggs"}'

HTTP/1.1 201 Created
content-type: application/json

{"id":4,"title":"Buy eggs","done":false}
```

## Stage-by-stage assignment workflow

### Stage 0 — Create your database
- Create `tasks.db` and a `tasks` table.
- Seed 3 example tasks only when the table is empty.
- Restarting the app should not create duplicates.

### Stage 1 — Read from the database
- `GET /tasks` reads SQL rows from the database.
- `GET /tasks/{id}` returns a single task from SQLite.
- Unknown IDs still return `404 { "error": "Task not found" }`.

### Stage 2 — Create new tasks
- `POST /tasks` inserts a new row into SQLite.
- Validation stays the same: blank titles are rejected with `400`.
- Data survives a server restart.

### Stage 3 — Update and delete
- `PUT /tasks/{id}` updates a row in the database.
- `DELETE /tasks/{id}` removes a row.
- Endpoints behave the same as before.

### Stage 4 — Explore SQLite
- Open the database in DB Browser for SQLite.
- Queries such as `SELECT * FROM tasks`, `SELECT * FROM tasks WHERE done = 1;`,
  `SELECT COUNT(*) FROM tasks;`, `UPDATE tasks SET done = 1;`, and
  `DELETE FROM tasks WHERE done = 1;` all reflect immediately through the API.

### Stage 5 — Publish your project
- Documentation includes why SQLite was chosen, where the file lives, how to run it,
  a DB Browser screenshot, and an example SQL query.

## Database screenshot

![DB Browser for SQLite showing the tasks database](image.png)

![DB Browser for SQLite showing the tasks schema](image0.png)

## AI vs me

_(Optional Stage 6 bonus — not completed in this version.)_

## Notes

- The API layer still uses the same endpoints and JSON shapes as Assignment 1.
- The only substantive change is the storage layer: a Python list was replaced with
  a SQLite database file that persists across restarts.
- This is the core lesson of the assignment: the API contract stays the same, while
  the persistence layer becomes real and durable.

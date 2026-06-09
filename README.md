# Daily journal

A minimalist daily journal: to-dos, what went well / didn't / to improve,
a hobby tracker, and a mood emoji — all per day.

This is Layer 1 of the project: the application itself, running in containers.
Layer 2 (Kubernetes) and Layer 3 (CI/CD, secrets, observability) build on top.

## Structure

```
journal-app/
├── backend/            FastAPI + SQLAlchemy REST API
│   ├── app/
│   │   ├── database.py   DB connection (DATABASE_URL env var)
│   │   ├── models.py     tables: todos, journal_entries, moods, hobbies, hobby_logs
│   │   ├── schemas.py    request/response shapes (Pydantic)
│   │   └── main.py       all API routes + /healthz, /readyz
│   ├── requirements.txt
│   └── Dockerfile        multi-stage, non-root
├── frontend/           static HTML/CSS/JS served by nginx
│   ├── index.html
│   ├── style.css
│   ├── app.js
│   ├── nginx.conf        serves files + proxies /api to the backend
│   └── Dockerfile
└── docker-compose.yml  backend + frontend + Postgres
```

## Run it (Docker)

```bash
docker compose up --build
```

Then open http://localhost:8080

## Run the backend alone (no Docker)

With no DATABASE_URL set it uses a local SQLite file, so it just runs:

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Interactive API docs: http://localhost:8000/docs

## API quick reference

| Method | Path                  | Purpose                          |
|--------|-----------------------|----------------------------------|
| GET    | /api/day/{date}       | everything for one day           |
| POST   | /api/todos            | add a to-do                      |
| PATCH  | /api/todos/{id}       | toggle done / edit text          |
| DELETE | /api/todos/{id}       | delete a to-do                   |
| POST   | /api/entries          | add positive/negative/improve    |
| DELETE | /api/entries/{id}     | delete an entry                  |
| PUT    | /api/mood             | set the mood for a day           |
| GET    | /api/hobbies          | list tracked hobbies             |
| POST   | /api/hobbies          | add a hobby                      |
| DELETE | /api/hobbies/{id}     | remove a hobby                   |
| PUT    | /api/hobby-logs       | mark a hobby done/not for a day  |
| GET    | /healthz, /readyz     | health checks (for k8s probes)   |
```

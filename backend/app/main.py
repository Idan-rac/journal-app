from datetime import date

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, delete
from sqlalchemy.orm import Session

from . import models, schemas
from .database import Base, engine, get_db

# Create the tables if they do not exist yet. Fine for this project;
# in a larger app you would use migrations (Alembic) instead.
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Daily Journal API")

# Allow the browser frontend to call the API during local development.
# In docker-compose/Kubernetes the frontend proxies /api, so this is a fallback.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Health checks (used by Kubernetes probes in a later layer) ---------------

@app.get("/healthz")
def healthz():
    """Liveness: is the process up?"""
    return {"status": "ok"}


@app.get("/readyz")
def readyz(db: Session = Depends(get_db)):
    """Readiness: can we actually reach the database?"""
    db.execute(select(1))
    return {"status": "ready"}


# --- The aggregate endpoint the frontend uses on every day change -------------

@app.get("/api/day/{day}", response_model=schemas.DaySummary)
def get_day(day: date, db: Session = Depends(get_db)):
    todos = db.scalars(select(models.Todo).where(models.Todo.day == day).order_by(models.Todo.id)).all()
    entries = db.scalars(select(models.JournalEntry).where(models.JournalEntry.day == day).order_by(models.JournalEntry.id)).all()
    mood = db.scalar(select(models.Mood).where(models.Mood.day == day))

    # Every hobby in the catalogue, with its done-status for this specific day.
    hobbies = db.scalars(select(models.Hobby).order_by(models.Hobby.id)).all()
    logs = db.scalars(select(models.HobbyLog).where(models.HobbyLog.day == day)).all()
    done_map = {log.hobby_id: log.done for log in logs}

    return schemas.DaySummary(
        day=day,
        mood=mood.emoji if mood else None,
        todos=[schemas.TodoOut.model_validate(t) for t in todos],
        positive=[schemas.EntryOut.model_validate(e) for e in entries if e.kind == "positive"],
        negative=[schemas.EntryOut.model_validate(e) for e in entries if e.kind == "negative"],
        improve=[schemas.EntryOut.model_validate(e) for e in entries if e.kind == "improve"],
        hobbies=[
            schemas.HobbyStatus(id=h.id, name=h.name, done=done_map.get(h.id, False))
            for h in hobbies
        ],
    )


# --- To-dos -------------------------------------------------------------------

@app.post("/api/todos", response_model=schemas.TodoOut)
def create_todo(body: schemas.TodoCreate, db: Session = Depends(get_db)):
    todo = models.Todo(day=body.day, text=body.text, done=False)
    db.add(todo)
    db.commit()
    db.refresh(todo)
    return todo


@app.patch("/api/todos/{todo_id}", response_model=schemas.TodoOut)
def update_todo(todo_id: int, body: schemas.TodoUpdate, db: Session = Depends(get_db)):
    todo = db.get(models.Todo, todo_id)
    if not todo:
        raise HTTPException(status_code=404, detail="Todo not found")
    if body.text is not None:
        todo.text = body.text
    if body.done is not None:
        todo.done = body.done
    db.commit()
    db.refresh(todo)
    return todo


@app.delete("/api/todos/{todo_id}")
def delete_todo(todo_id: int, db: Session = Depends(get_db)):
    todo = db.get(models.Todo, todo_id)
    if not todo:
        raise HTTPException(status_code=404, detail="Todo not found")
    db.delete(todo)
    db.commit()
    return {"deleted": todo_id}


# --- Journal entries (positive / negative / improve) --------------------------

@app.post("/api/entries", response_model=schemas.EntryOut)
def create_entry(body: schemas.EntryCreate, db: Session = Depends(get_db)):
    if body.kind not in ("positive", "negative", "improve"):
        raise HTTPException(status_code=400, detail="Invalid kind")
    entry = models.JournalEntry(day=body.day, kind=body.kind, text=body.text)
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


@app.delete("/api/entries/{entry_id}")
def delete_entry(entry_id: int, db: Session = Depends(get_db)):
    entry = db.get(models.JournalEntry, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    db.delete(entry)
    db.commit()
    return {"deleted": entry_id}


# --- Mood (one per day, upsert) -----------------------------------------------

@app.put("/api/mood", response_model=schemas.MoodSet)
def set_mood(body: schemas.MoodSet, db: Session = Depends(get_db)):
    mood = db.scalar(select(models.Mood).where(models.Mood.day == body.day))
    if mood:
        mood.emoji = body.emoji
    else:
        db.add(models.Mood(day=body.day, emoji=body.emoji))
    db.commit()
    return body


# --- Hobbies catalogue --------------------------------------------------------

@app.get("/api/hobbies", response_model=list[schemas.HobbyOut])
def list_hobbies(db: Session = Depends(get_db)):
    return db.scalars(select(models.Hobby).order_by(models.Hobby.id)).all()


@app.post("/api/hobbies", response_model=schemas.HobbyOut)
def create_hobby(body: schemas.HobbyCreate, db: Session = Depends(get_db)):
    existing = db.scalar(select(models.Hobby).where(models.Hobby.name == body.name))
    if existing:
        return existing
    hobby = models.Hobby(name=body.name)
    db.add(hobby)
    db.commit()
    db.refresh(hobby)
    return hobby


@app.delete("/api/hobbies/{hobby_id}")
def delete_hobby(hobby_id: int, db: Session = Depends(get_db)):
    hobby = db.get(models.Hobby, hobby_id)
    if not hobby:
        raise HTTPException(status_code=404, detail="Hobby not found")
    # Remove its logs too, so no orphan rows are left behind.
    db.execute(delete(models.HobbyLog).where(models.HobbyLog.hobby_id == hobby_id))
    db.delete(hobby)
    db.commit()
    return {"deleted": hobby_id}


# --- Hobby log (was a hobby done on a day? upsert) ----------------------------

@app.put("/api/hobby-logs", response_model=schemas.HobbyLogSet)
def set_hobby_log(body: schemas.HobbyLogSet, db: Session = Depends(get_db)):
    log = db.scalar(
        select(models.HobbyLog).where(
            models.HobbyLog.day == body.day,
            models.HobbyLog.hobby_id == body.hobby_id,
        )
    )
    if log:
        log.done = body.done
    else:
        db.add(models.HobbyLog(day=body.day, hobby_id=body.hobby_id, done=body.done))
    db.commit()
    return body

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

# The whole DB connection is driven by one environment variable.
# - No variable set  -> a local SQLite file (zero setup, good for `python` on your laptop).
# - DATABASE_URL set -> Postgres (this is what docker-compose and Kubernetes will inject).
# This is deliberate: config comes from the environment, never hardcoded.
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./journal.db")

# SQLite needs this one extra flag when used with a web server; Postgres does not.
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    """All ORM models inherit from this."""
    pass


def get_db():
    """Hands a DB session to a request, and always closes it afterwards."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

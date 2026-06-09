from datetime import date, datetime

from sqlalchemy import (
    String, Boolean, Date, DateTime, ForeignKey, UniqueConstraint, func,
)
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


# Each model below maps to one table. Everything is organised around a "day"
# (a calendar date), because the app is a daily journal.


class Todo(Base):
    __tablename__ = "todos"

    id: Mapped[int] = mapped_column(primary_key=True)
    day: Mapped[date] = mapped_column(Date, index=True)
    text: Mapped[str] = mapped_column(String(500))
    done: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class JournalEntry(Base):
    """A single line under one of: positive / negative / improve."""
    __tablename__ = "journal_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    day: Mapped[date] = mapped_column(Date, index=True)
    kind: Mapped[str] = mapped_column(String(20))  # "positive" | "negative" | "improve"
    text: Mapped[str] = mapped_column(String(1000))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Mood(Base):
    """One mood emoji per day."""
    __tablename__ = "moods"

    id: Mapped[int] = mapped_column(primary_key=True)
    day: Mapped[date] = mapped_column(Date, unique=True, index=True)
    emoji: Mapped[str] = mapped_column(String(8))


class Hobby(Base):
    """The catalogue of hobbies you track (e.g. Reading, Gym, Guitar)."""
    __tablename__ = "hobbies"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)


class HobbyLog(Base):
    """Whether a given hobby was done on a given day. One row per (day, hobby)."""
    __tablename__ = "hobby_logs"
    __table_args__ = (UniqueConstraint("day", "hobby_id", name="uq_hobby_day"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    day: Mapped[date] = mapped_column(Date, index=True)
    hobby_id: Mapped[int] = mapped_column(
        ForeignKey("hobbies.id", ondelete="CASCADE"), index=True
    )
    done: Mapped[bool] = mapped_column(Boolean, default=False)

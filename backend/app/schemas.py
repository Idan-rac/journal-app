from datetime import date

from pydantic import BaseModel


# Pydantic models define the JSON shapes the API accepts and returns.
# "Create"/"Update" = what the client sends in. "Out" = what we send back.


class TodoCreate(BaseModel):
    day: date
    text: str


class TodoUpdate(BaseModel):
    text: str | None = None
    done: bool | None = None


class TodoOut(BaseModel):
    id: int
    day: date
    text: str
    done: bool

    model_config = {"from_attributes": True}  # allow building from an ORM object


class EntryCreate(BaseModel):
    day: date
    kind: str  # "positive" | "negative" | "improve"
    text: str


class EntryOut(BaseModel):
    id: int
    day: date
    kind: str
    text: str

    model_config = {"from_attributes": True}


class MoodSet(BaseModel):
    day: date
    emoji: str


class HobbyCreate(BaseModel):
    name: str


class HobbyOut(BaseModel):
    id: int
    name: str

    model_config = {"from_attributes": True}


class HobbyStatus(BaseModel):
    """A hobby plus whether it was done on the requested day."""
    id: int
    name: str
    done: bool


class HobbyLogSet(BaseModel):
    day: date
    hobby_id: int
    done: bool


class DaySummary(BaseModel):
    """Everything the frontend needs to render one day, in a single response."""
    day: date
    mood: str | None
    todos: list[TodoOut]
    positive: list[EntryOut]
    negative: list[EntryOut]
    improve: list[EntryOut]
    hobbies: list[HobbyStatus]

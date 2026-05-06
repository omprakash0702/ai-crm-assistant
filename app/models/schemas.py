from pydantic import BaseModel, field_validator
from typing import Optional, List

_MAX_LEN = 500


def _required(v: str) -> str:
    v = v.strip()
    if not v:
        raise ValueError("cannot be empty")
    if len(v) > _MAX_LEN:
        raise ValueError(f"must be {_MAX_LEN} characters or fewer")
    return v


def _optional(v: str) -> str:
    return v.strip()


class StructuredInteractionRequest(BaseModel):
    doctor_name: str
    interaction_type: str = "Meeting"
    date_time: Optional[str] = None
    attendees: Optional[str] = None
    notes: str = ""
    products_discussed: Optional[str] = None
    sentiment: str = "Neutral"
    follow_up: Optional[str] = None

    @field_validator("doctor_name", mode="before")
    @classmethod
    def validate_doctor_name(cls, v):
        return _required(v)

    @field_validator("notes", mode="before")
    @classmethod
    def validate_notes(cls, v):
        return _optional(v)


class LogInteractionRequest(BaseModel):
    doctor_name: str
    notes: str

    @field_validator("doctor_name", "notes", mode="before")
    @classmethod
    def validate_fields(cls, v):
        return _required(v)


class EditInteractionRequest(BaseModel):
    id: int
    notes: str

    @field_validator("notes", mode="before")
    @classmethod
    def validate_notes(cls, v):
        return _required(v)


class HistoryMessage(BaseModel):
    role: str
    text: str


class ChatRequest(BaseModel):
    message: str
    history: Optional[List[HistoryMessage]] = None

    @field_validator("message", mode="before")
    @classmethod
    def validate_message(cls, v):
        return _required(v)


class SummarizeRequest(BaseModel):
    text: str

    @field_validator("text", mode="before")
    @classmethod
    def validate_text(cls, v):
        return _required(v)


class DoctorCreate(BaseModel):
    name: str

    @field_validator("name", mode="before")
    @classmethod
    def validate_name(cls, v):
        return _required(v)


class FollowUpCreate(BaseModel):
    doctor_id: int
    task: str
    due_date: Optional[str] = None
    status: str = "pending"

    @field_validator("task", mode="before")
    @classmethod
    def validate_task(cls, v):
        return _required(v)


class FollowUpUpdate(BaseModel):
    status: str


class SignupRequest(BaseModel):
    name: str
    email: str
    password: str
    company: str
    job_title: str
    territory: Optional[str] = None

    @field_validator("name", "email", "company", "job_title", mode="before")
    @classmethod
    def validate_str_fields(cls, v):
        return _required(v)

    @field_validator("territory", mode="before")
    @classmethod
    def validate_territory(cls, v):
        return v.strip() if v else None

    @field_validator("password", mode="before")
    @classmethod
    def validate_password(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("cannot be empty")
        if len(v) < 8:
            raise ValueError("must be at least 8 characters")
        return v


class LoginRequest(BaseModel):
    email: str
    password: str

    @field_validator("email", "password", mode="before")
    @classmethod
    def validate_login_fields(cls, v):
        return _required(v)


class FormatNotesRequest(BaseModel):
    notes: List[str]
    types: Optional[List[str]] = None

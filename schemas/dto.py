from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional
from datetime import datetime


class ParentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    primary_contact: str = Field(..., max_length=15)
    father_name: Optional[str] = Field(None, max_length=100)
    mother_name: Optional[str] = Field(None, max_length=100)
    guardian_name: Optional[str] = Field(None, max_length=150)
    secondary_contact: Optional[str] = Field(None, max_length=15)
    guardian_contact: Optional[str] = Field(None, max_length=15)
    guardian_email: Optional[str] = Field(None, max_length=150)
    address: Optional[str] = None
    permanent_address: Optional[str] = None
    occupation: Optional[str] = Field(None, max_length=150)
    annual_income: Optional[str] = Field(None, max_length=50)


class ParentUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: Optional[EmailStr] = None
    primary_contact: Optional[str] = Field(None, max_length=15)
    father_name: Optional[str] = Field(None, max_length=100)
    mother_name: Optional[str] = Field(None, max_length=100)
    guardian_name: Optional[str] = Field(None, max_length=150)
    secondary_contact: Optional[str] = Field(None, max_length=15)
    guardian_contact: Optional[str] = Field(None, max_length=15)
    address: Optional[str] = None
    occupation: Optional[str] = Field(None, max_length=150)
    is_active: Optional[bool] = None


class ParentListOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: Optional[str]
    father_name: Optional[str]
    mother_name: Optional[str]
    guardian_name: Optional[str]
    primary_contact: str
    is_active: bool


class ParentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: Optional[str]
    email: Optional[str]
    father_name: Optional[str]
    mother_name: Optional[str]
    guardian_name: Optional[str]
    primary_contact: str
    secondary_contact: Optional[str]
    guardian_contact: Optional[str]
    guardian_email: Optional[str]
    address: Optional[str]
    permanent_address: Optional[str]
    occupation: Optional[str]
    annual_income: Optional[str]
    is_active: bool


class LinkStudentPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    student_id: str = Field(..., min_length=2, max_length=20)
    relationship_type: str = Field(default="GUARDIAN")
    is_primary_contact: bool = False
    can_view_academics: bool = True
    can_view_attendance: bool = True
    can_view_timetable: bool = True


class LinkedStudentOut(BaseModel):
    student_id: str
    full_name: str
    relationship_type: str
    is_primary_contact: bool
    can_view_academics: bool
    can_view_attendance: bool
    can_view_timetable: bool


class ParentTeacherMeetingCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    teacher_id: str = Field(..., min_length=2, max_length=20)
    student_id: Optional[str] = Field(default=None, min_length=2, max_length=20)
    meeting_at: datetime
    duration_minutes: int = Field(default=30, ge=10, le=180)
    mode: str = Field(default="ONLINE", max_length=20)
    agenda: Optional[str] = Field(default=None, max_length=1000)


class ParentTeacherMeetingDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str = Field(..., max_length=20)
    notes: Optional[str] = Field(default=None, max_length=1000)
    meeting_link: Optional[str] = Field(default=None, max_length=500)


class ParentTeacherMeetingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    parent_id: str
    teacher_id: str
    student_id: Optional[str]
    meeting_at: datetime
    duration_minutes: int
    mode: str
    agenda: Optional[str]
    status: str
    meeting_link: Optional[str]
    notes: Optional[str]

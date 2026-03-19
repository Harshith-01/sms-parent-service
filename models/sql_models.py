from sqlalchemy import (
    Boolean, Column, ForeignKey, Integer, String, Text,
    TIMESTAMP, CheckConstraint
)
from sqlalchemy.dialects.postgresql import TIMESTAMP as PGTS
from sqlalchemy.sql import func
from core.database import Base


class User(Base):
    __tablename__ = "users"
    id = Column(String(20), primary_key=True)
    email = Column(String(255), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP, server_default=func.now())


class Role(Base):
    __tablename__ = "roles"
    id = Column(Integer, primary_key=True)
    role_name = Column(String(50), unique=True, nullable=False)


class UserRole(Base):
    __tablename__ = "user_roles"
    user_id = Column(String(20), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    role_id = Column(Integer, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True)


class Parent(Base):
    __tablename__ = "parents"

    id = Column(String(20), primary_key=True)
    user_id = Column(String(20), ForeignKey("users.id", ondelete="SET NULL"), unique=True)

    father_name = Column(String(100))
    mother_name = Column(String(100))
    guardian_name = Column(String(150))
    primary_contact = Column(String(15), nullable=False)
    secondary_contact = Column(String(15))
    guardian_contact = Column(String(15))
    email = Column(String(100))
    guardian_email = Column(String(150))
    address = Column(Text)
    permanent_address = Column(Text)
    occupation = Column(String(150))
    annual_income = Column(String(50))

    is_active = Column(Boolean, default=True, nullable=False)
    deleted_at = Column(PGTS(timezone=True))
    created_at = Column(PGTS(timezone=True), server_default=func.now())
    updated_at = Column(PGTS(timezone=True), server_default=func.now())


class Student(Base):
    __tablename__ = "students"
    id = Column(String(20), primary_key=True)
    user_id = Column(String(20), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    full_name = Column(String(150), nullable=False)
    admission_number = Column(String(50))


class StudentParentRelationship(Base):
    __tablename__ = "student_parent_relationship"

    id = Column(Integer, primary_key=True)
    student_id = Column(String(20), ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    parent_id = Column(String(20), ForeignKey("parents.id", ondelete="CASCADE"), nullable=False)
    relationship_type = Column(String(30), nullable=False, default="GUARDIAN")
    is_primary_contact = Column(Boolean, nullable=False, default=False)
    can_view_academics = Column(Boolean, nullable=False, default=True)
    can_view_attendance = Column(Boolean, nullable=False, default=True)
    can_view_timetable = Column(Boolean, nullable=False, default=True)
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.now())

    __table_args__ = (
        CheckConstraint(
            "relationship_type IN ('FATHER','MOTHER','GUARDIAN','STEP_PARENT','SIBLING_GUARDIAN','OTHER')",
            name="chk_relationship_type",
        ),
    )


class TeacherRef(Base):
    __tablename__ = "teachers"
    id = Column(String(20), primary_key=True)


class ParentTeacherMeeting(Base):
    __tablename__ = "parent_teacher_meetings"

    id = Column(Integer, primary_key=True)
    parent_id = Column(String(20), ForeignKey("parents.id", ondelete="CASCADE"), nullable=False)
    teacher_id = Column(String(20), ForeignKey("teachers.id", ondelete="CASCADE"), nullable=False)
    student_id = Column(String(20), ForeignKey("students.id", ondelete="SET NULL"))
    meeting_at = Column(PGTS(timezone=True), nullable=False)
    duration_minutes = Column(Integer, nullable=False, default=30)
    mode = Column(String(20), nullable=False, default="ONLINE")
    agenda = Column(Text)
    status = Column(String(20), nullable=False, default="REQUESTED")
    meeting_link = Column(Text)
    notes = Column(Text)
    requested_by = Column(String(20), ForeignKey("users.id", ondelete="SET NULL"), nullable=False)
    approved_by = Column(String(20), ForeignKey("users.id", ondelete="SET NULL"))
    created_at = Column(PGTS(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(PGTS(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("duration_minutes BETWEEN 10 AND 180", name="chk_ptm_duration"),
        CheckConstraint("mode IN ('ONLINE','OFFLINE','PHONE')", name="chk_ptm_mode"),
        CheckConstraint("status IN ('REQUESTED','APPROVED','REJECTED','COMPLETED','CANCELLED')", name="chk_ptm_status"),
    )

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import text
from core.db_errors import db_integrity_http_exception

from core.database import get_db
from core.dependencies import require_role
from core.id_generator import generate_parent_id, generate_user_id
from core.security import get_password_hash
from models.sql_models import (
    Parent, StudentParentRelationship, Student,
    User, Role, UserRole, ParentTeacherMeeting
)
from schemas.dto import (
    ParentCreate, ParentUpdate, ParentOut, ParentListOut,
    LinkStudentPayload, LinkedStudentOut,
    ParentTeacherMeetingCreate, ParentTeacherMeetingDecision, ParentTeacherMeetingOut,
)
from services.attendance_client import get_student_attendance_summary
from services.assessment_client import get_student_report_cards, get_exam_schedule
from services.academic_client import get_student_timetable

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/parents", tags=["Parent Service"])


# ============================================================
# INTERNAL LOGIC
# ============================================================

def create_parent_logic(db: Session, data: ParentCreate) -> str:
    normalized_email = data.email.strip().lower()

    if db.query(User).filter(User.email == normalized_email).first():
        raise HTTPException(409, "Email already registered")

    parent_id = generate_parent_id(db)
    user_id = generate_user_id(db)

    temp_password = data.primary_contact or "Welcome@123"

    new_user = User(
        id=user_id,
        email=normalized_email,
        hashed_password=get_password_hash(temp_password),
        is_active=True,
    )
    db.add(new_user)
    db.flush()

    role = db.query(Role).filter(Role.role_name == "PARENT").first()
    if not role:
        raise HTTPException(500, "PARENT role not found in roles table")

    db.add(UserRole(user_id=user_id, role_id=role.id))

    parent = Parent(
        id=parent_id,
        user_id=user_id,
        father_name=data.father_name,
        mother_name=data.mother_name,
        guardian_name=data.guardian_name,
        primary_contact=data.primary_contact,
        secondary_contact=data.secondary_contact,
        guardian_contact=data.guardian_contact,
        email=normalized_email,
        guardian_email=data.guardian_email,
        address=data.address,
        permanent_address=data.permanent_address,
        occupation=data.occupation,
        annual_income=data.annual_income,
        is_active=True,
    )
    db.add(parent)
    return parent_id


# ============================================================
# CREATE PARENT (admin)
# ============================================================

@router.post("", status_code=201)
def create_parent(
    data: ParentCreate,
    db: Session = Depends(get_db),
    user=Depends(require_role(["ADMIN"])),
):
    try:
        parent_id = create_parent_logic(db, data)
        db.commit()
        logger.info(f"Parent created: {parent_id} by {user.get('user_id')}")
        return {"parent_id": parent_id}
    except IntegrityError as exc:
        db.rollback()
        raise db_integrity_http_exception(exc, fallback_status=409, fallback_detail="Duplicate or invalid parent data")
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        logger.exception("Parent creation failed")
        raise HTTPException(500, "Internal server error")


# ============================================================
# LIST (admin)
# ============================================================

@router.get("", response_model=list[ParentListOut])
def list_parents(
    is_active: bool | None = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user=Depends(require_role(["ADMIN"])),
):
    query = db.query(Parent)
    if is_active is not None:
        query = query.filter(Parent.is_active == is_active)
    else:
        query = query.filter(Parent.is_active.is_(True))
    return [ParentListOut.model_validate(p) for p in query.offset(offset).limit(limit).all()]


# ============================================================
# GET BY ID (admin)
# ============================================================

@router.get("/me", response_model=ParentOut)
def get_my_profile(
    db: Session = Depends(get_db),
    user=Depends(require_role(["PARENT"])),
):
    parent = db.query(Parent).filter(Parent.user_id == user["user_id"]).first()
    if not parent:
        raise HTTPException(404, "Parent profile not found")
    return ParentOut.model_validate(parent)


@router.get("/me/children", response_model=list[LinkedStudentOut])
def get_my_children(
    db: Session = Depends(get_db),
    user=Depends(require_role(["PARENT"])),
):
    parent = db.query(Parent).filter(Parent.user_id == user["user_id"]).first()
    if not parent:
        raise HTTPException(404, "Parent profile not found")
    return _get_children(db, parent.id)


@router.get("/me/children/{student_id}/attendance")
def get_child_attendance(
    student_id: str,
    class_section_id: int,
    academic_term_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_role(["PARENT"])),
):
    parent = db.query(Parent).filter(Parent.user_id == user["user_id"]).first()
    if not parent:
        raise HTTPException(404, "Parent profile not found")
    _assert_child_linked(db, parent.id, student_id, require_attendance=True)
    return get_student_attendance_summary(student_id, class_section_id, academic_term_id)


@router.get("/me/children/{student_id}/report-cards")
def get_child_report_cards(
    student_id: str,
    db: Session = Depends(get_db),
    user=Depends(require_role(["PARENT"])),
):
    parent = db.query(Parent).filter(Parent.user_id == user["user_id"]).first()
    if not parent:
        raise HTTPException(404, "Parent profile not found")
    _assert_child_linked(db, parent.id, student_id, require_academics=True)
    return get_student_report_cards(student_id)


@router.get("/me/children/{student_id}/exam-schedule")
def get_child_exam_schedule(
    student_id: str,
    class_section_id: int,
    academic_year_id: int,
    academic_term_id: int | None = None,
    db: Session = Depends(get_db),
    user=Depends(require_role(["PARENT"])),
):
    parent = db.query(Parent).filter(Parent.user_id == user["user_id"]).first()
    if not parent:
        raise HTTPException(404, "Parent profile not found")
    _assert_child_linked(db, parent.id, student_id, require_academics=True)
    return get_exam_schedule(class_section_id, academic_year_id, academic_term_id)


@router.get("/me/children/{student_id}/timetable")
def get_child_timetable(
    student_id: str,
    class_section_id: int,
    academic_term_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_role(["PARENT"])),
):
    parent = db.query(Parent).filter(Parent.user_id == user["user_id"]).first()
    if not parent:
        raise HTTPException(404, "Parent profile not found")
    _assert_child_linked(db, parent.id, student_id, require_timetable=True)
    return get_student_timetable(class_section_id, academic_term_id)


@router.get("/{parent_id}", response_model=ParentOut)
def get_parent(
    parent_id: str,
    db: Session = Depends(get_db),
    user=Depends(require_role(["ADMIN"])),
):
    parent = db.query(Parent).filter(Parent.id == parent_id).first()
    if not parent:
        raise HTTPException(404, "Parent not found")
    return ParentOut.model_validate(parent)


# ============================================================
# LINK STUDENT TO PARENT (admin)
# ============================================================

@router.post("/{parent_id}/link-student", status_code=201)
def link_student(
    parent_id: str,
    payload: LinkStudentPayload,
    db: Session = Depends(get_db),
    user=Depends(require_role(["ADMIN"])),
):
    parent = db.query(Parent).filter(Parent.id == parent_id).first()
    if not parent:
        raise HTTPException(404, "Parent not found")

    student = db.query(Student).filter(Student.id == payload.student_id).first()
    if not student:
        raise HTTPException(404, "Student not found")

    # If setting primary, unset existing primary contact for this student
    if payload.is_primary_contact:
        db.query(StudentParentRelationship).filter(
            StudentParentRelationship.student_id == payload.student_id,
            StudentParentRelationship.is_primary_contact.is_(True),
        ).update({"is_primary_contact": False})

    try:
        rel = StudentParentRelationship(
            student_id=payload.student_id,
            parent_id=parent_id,
            relationship_type=payload.relationship_type,
            is_primary_contact=payload.is_primary_contact,
            can_view_academics=payload.can_view_academics,
            can_view_attendance=payload.can_view_attendance,
            can_view_timetable=payload.can_view_timetable,
        )
        db.add(rel)
        db.commit()
        return {"message": "Student linked to parent"}
    except IntegrityError as exc:
        db.rollback()
        raise db_integrity_http_exception(exc, fallback_status=409, fallback_detail="This student is already linked to this parent")


@router.delete("/{parent_id}/unlink-student/{student_id}")
def unlink_student(
    parent_id: str,
    student_id: str,
    db: Session = Depends(get_db),
    user=Depends(require_role(["ADMIN"])),
):
    rel = db.query(StudentParentRelationship).filter(
        StudentParentRelationship.parent_id == parent_id,
        StudentParentRelationship.student_id == student_id,
    ).first()
    if not rel:
        raise HTTPException(404, "Relationship not found")
    db.delete(rel)
    db.commit()
    return {"message": "Student unlinked from parent"}


@router.get("/{parent_id}/children", response_model=list[LinkedStudentOut])
def get_parent_children(
    parent_id: str,
    db: Session = Depends(get_db),
    user=Depends(require_role(["ADMIN"])),
):
    parent = db.query(Parent).filter(Parent.id == parent_id).first()
    if not parent:
        raise HTTPException(404, "Parent not found")
    return _get_children(db, parent_id)


# ============================================================
# UPDATE (admin)
# ============================================================

@router.put("/{parent_id}")
def update_parent(
    parent_id: str,
    data: ParentUpdate,
    db: Session = Depends(get_db),
    user=Depends(require_role(["ADMIN"])),
):
    parent = db.query(Parent).filter(Parent.id == parent_id).first()
    if not parent:
        raise HTTPException(404, "Parent not found")

    updates = data.model_dump(exclude_unset=True)

    if "email" in updates:
        new_email = updates["email"].strip().lower()
        existing = db.query(User).filter(
            User.email == new_email, User.id != parent.user_id
        ).first()
        if existing:
            raise HTTPException(409, "Email already in use")
        auth_user = db.query(User).filter(User.id == parent.user_id).first()
        if auth_user:
            auth_user.email = new_email
        parent.email = new_email
        updates.pop("email")

    for key, value in updates.items():
        setattr(parent, key, value)

    try:
        db.commit()
        return {"message": "Parent updated"}
    except IntegrityError as exc:
        db.rollback()
        raise db_integrity_http_exception(exc, fallback_status=409, fallback_detail="Update constraint violation")


# ============================================================
# DEACTIVATE (admin)
# ============================================================

@router.delete("/{parent_id}")
def deactivate_parent(
    parent_id: str,
    db: Session = Depends(get_db),
    user=Depends(require_role(["ADMIN"])),
):
    parent = db.query(Parent).filter(Parent.id == parent_id).first()
    if not parent:
        raise HTTPException(404, "Parent not found")

    parent.is_active = False
    auth_user = db.query(User).filter(User.id == parent.user_id).first()
    if auth_user:
        auth_user.is_active = False

    db.commit()
    return {"message": "Parent deactivated"}


# ============================================================
# PARENT-TEACHER MEETINGS
# ============================================================

@router.post("/me/meetings", response_model=ParentTeacherMeetingOut, status_code=201)
def request_parent_teacher_meeting(
    payload: ParentTeacherMeetingCreate,
    db: Session = Depends(get_db),
    user=Depends(require_role(["PARENT"]))
):
    parent = db.query(Parent).filter(Parent.user_id == user["user_id"]).first()
    if not parent:
        raise HTTPException(404, "Parent profile not found")

    if payload.student_id:
        _assert_child_linked(db, parent.id, payload.student_id)

    mode = payload.mode.upper()
    if mode not in {"ONLINE", "OFFLINE", "PHONE"}:
        raise HTTPException(400, "Invalid mode")

    row = ParentTeacherMeeting(
        parent_id=parent.id,
        teacher_id=payload.teacher_id,
        student_id=payload.student_id,
        meeting_at=payload.meeting_at,
        duration_minutes=payload.duration_minutes,
        mode=mode,
        agenda=payload.agenda,
        status="REQUESTED",
        requested_by=user["user_id"],
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return ParentTeacherMeetingOut.model_validate(row)


@router.get("/me/meetings", response_model=list[ParentTeacherMeetingOut])
def list_my_meetings(
    status: str | None = None,
    db: Session = Depends(get_db),
    user=Depends(require_role(["PARENT"]))
):
    parent = db.query(Parent).filter(Parent.user_id == user["user_id"]).first()
    if not parent:
        raise HTTPException(404, "Parent profile not found")

    query = db.query(ParentTeacherMeeting).filter(ParentTeacherMeeting.parent_id == parent.id)
    if status:
        query = query.filter(ParentTeacherMeeting.status == status.upper())
    return query.order_by(ParentTeacherMeeting.meeting_at.desc()).all()


@router.patch("/meetings/{meeting_id}", response_model=ParentTeacherMeetingOut)
def decide_or_update_meeting(
    meeting_id: int,
    payload: ParentTeacherMeetingDecision,
    db: Session = Depends(get_db),
    user=Depends(require_role(["ADMIN", "TEACHER"]))
):
    row = db.query(ParentTeacherMeeting).filter(ParentTeacherMeeting.id == meeting_id).first()
    if not row:
        raise HTTPException(404, "Meeting not found")

    new_status = payload.status.upper()
    if new_status not in {"APPROVED", "REJECTED", "COMPLETED", "CANCELLED"}:
        raise HTTPException(400, "Invalid status")

    actor_role = (user.get("role") or "").upper()
    if actor_role == "TEACHER":
        teacher_row = db.execute(
            text("SELECT id FROM teachers WHERE user_id = :user_id LIMIT 1"),
            {"user_id": user["user_id"]},
        ).fetchone()
        teacher_id = teacher_row[0] if teacher_row else None
        if teacher_id != row.teacher_id:
            raise HTTPException(403, "Not allowed to update this meeting")

    row.status = new_status
    row.notes = payload.notes
    row.meeting_link = payload.meeting_link
    row.approved_by = user["user_id"]
    db.commit()
    db.refresh(row)
    return ParentTeacherMeetingOut.model_validate(row)


@router.get("/meetings", response_model=list[ParentTeacherMeetingOut])
def list_all_meetings(
    teacher_id: str | None = None,
    status: str | None = None,
    db: Session = Depends(get_db),
    user=Depends(require_role(["ADMIN", "TEACHER"]))
):
    query = db.query(ParentTeacherMeeting)

    actor_role = (user.get("role") or "").upper()
    if actor_role == "TEACHER":
        teacher_row = db.execute(
            text("SELECT id FROM teachers WHERE user_id = :user_id LIMIT 1"),
            {"user_id": user["user_id"]},
        ).fetchone()
        actor_teacher_id = teacher_row[0] if teacher_row else None
        if not actor_teacher_id:
            raise HTTPException(403, "Teacher profile not found")
        query = query.filter(ParentTeacherMeeting.teacher_id == actor_teacher_id)
    elif teacher_id:
        query = query.filter(ParentTeacherMeeting.teacher_id == teacher_id)

    if status:
        query = query.filter(ParentTeacherMeeting.status == status.upper())

    return query.order_by(ParentTeacherMeeting.meeting_at.desc()).all()


# ============================================================
# HELPERS
# ============================================================

def _get_children(db: Session, parent_id: str):
    rels = (
        db.query(StudentParentRelationship)
        .filter(StudentParentRelationship.parent_id == parent_id)
        .all()
    )
    result = []
    for rel in rels:
        student = db.query(Student).filter(Student.id == rel.student_id).first()
        if student:
            result.append(
                LinkedStudentOut(
                    student_id=student.id,
                    full_name=student.full_name,
                    relationship_type=rel.relationship_type,
                    is_primary_contact=rel.is_primary_contact,
                    can_view_academics=rel.can_view_academics,
                    can_view_attendance=rel.can_view_attendance,
                    can_view_timetable=rel.can_view_timetable,
                )
            )
    return result


def _assert_child_linked(
    db: Session,
    parent_id: str,
    student_id: str,
    require_academics: bool = False,
    require_attendance: bool = False,
    require_timetable: bool = False,
):
    rel = db.query(StudentParentRelationship).filter(
        StudentParentRelationship.parent_id == parent_id,
        StudentParentRelationship.student_id == student_id,
    ).first()
    if not rel:
        raise HTTPException(403, "This student is not linked to your account")
    if require_academics and not rel.can_view_academics:
        raise HTTPException(403, "Academics access not permitted for this student")
    if require_attendance and not rel.can_view_attendance:
        raise HTTPException(403, "Attendance access not permitted for this student")
    if require_timetable and not rel.can_view_timetable:
        raise HTTPException(403, "Timetable access not permitted for this student")

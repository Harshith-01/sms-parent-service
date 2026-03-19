Parent service initiated

# Parent Service - School ERP

Production-ready Parent Management microservice built with FastAPI and PostgreSQL.

This service handles:

- Parent account/profile lifecycle
- Parent-child linkage and permissioned visibility
- Parent self-service child views (attendance, report cards, exam schedule, timetable)
- Parent-teacher meeting workflow
- Cross-service read integrations for academic and assessment visibility

---

## Overview

Service base URL (local): http://127.0.0.1:8007

API prefix: /parents

Health endpoint: /health

---

## Tech Stack

- FastAPI
- SQLAlchemy
- PostgreSQL
- Pydantic v2
- SlowAPI (rate limiting)
- TrustedHost + CORS middleware

---

## Security Model

- JWT bearer authentication
- Role-based authorization per endpoint
- Roles used by routes: ADMIN, PARENT, TEACHER
- Strict DTO validation (forbid extra fields)
- Trusted host and CORS guardrails

Role examples:

- ADMIN: parent CRUD, linking, directory, cross-parent operations
- PARENT: self profile, child visibility, meeting request/list
- TEACHER: meeting decision/list access (scoped to teacher identity)

---

## Core Features

### 1) Parent Profile Lifecycle

- Create parent profile with linked auth user and PARENT role assignment
- List parents with active-state filtering
- Admin get/update/deactivate parent profile
- Parent self-profile endpoint

### 2) Parent-Child Relationship Management

- Link student to parent (relationship type + access flags)
- Unlink student from parent
- Mark/set primary contact behavior per student
- Parent child listing (self) and admin child listing (by parent)

Relationship permissions supported:

- can_view_academics
- can_view_attendance
- can_view_timetable

### 3) Parent Self-Service Child Information

Permissioned endpoints for linked children:

- Child attendance summary
- Child report cards
- Child exam schedule
- Child timetable

All self-service child endpoints enforce linkage checks and capability checks.

### 4) Parent-Teacher Meetings

- Parent can request meetings
- Parent can list own meetings
- Admin/Teacher can update meeting decision/status
- Admin/Teacher can list meetings (teacher scope enforced)

Meeting statuses:

- REQUESTED
- APPROVED
- REJECTED
- COMPLETED
- CANCELLED

Meeting modes:

- ONLINE
- OFFLINE
- PHONE

---

## Cross-Service Integrations

This service consumes read APIs from other services with internal service token headers.

### Attendance service integration

- Fetches student attendance summary
- Endpoint used: /timetable-attendance/attendance/students/{student_id}/summary

### Assessment service integration

- Fetches student report cards
- Fetches exam schedule by class/academic year/term
- Endpoints used:
	- /assessment/report-cards/student/{student_id}
	- /assessment/exams

### Academic service integration

- Fetches class timetable entries
- Endpoint used: /timetable-attendance/entries/class/{class_section_id}

Integration behavior:

- Retry-enabled HTTP session
- Timeout-controlled requests
- 502 responses for upstream unavailability/connection failures where relevant

---

## Main API Endpoints

All endpoints are under /parents.

### Parent management (ADMIN)

- POST /
- GET /
- GET /{parent_id}
- PUT /{parent_id}
- DELETE /{parent_id}

### Parent self-service (PARENT)

- GET /me
- GET /me/children
- GET /me/children/{student_id}/attendance
- GET /me/children/{student_id}/report-cards
- GET /me/children/{student_id}/exam-schedule
- GET /me/children/{student_id}/timetable

### Linkage operations (ADMIN)

- POST /{parent_id}/link-student
- DELETE /{parent_id}/unlink-student/{student_id}
- GET /{parent_id}/children

### Parent-teacher meetings

- POST /me/meetings (PARENT)
- GET /me/meetings (PARENT)
- PATCH /meetings/{meeting_id} (ADMIN, TEACHER)
- GET /meetings (ADMIN, TEACHER)

---

## Data Model Highlights

- parents
- student_parent_relationship
- parent_teacher_meetings

Shared reference models used for relation/auth consistency:

- users
- roles
- user_roles
- students
- teachers

Important constraints:

- Relationship type check constraints
- Meeting status/mode/duration constraints
- Parent-child relation integrity via FKs

---

## Environment Variables

Use .env in this service folder.

- DATABASE_URL
- SECRET_KEY (or JWT secret configured in your platform)
- ACCESS_TOKEN_EXPIRE_MINUTES
- ALLOWED_ORIGINS
- ALLOWED_HOSTS
- SERVICE_NAME
- INTERNAL_SERVICE_TOKEN
- INTERNAL_SERVICE_NAME
- INTERNAL_ALLOWED_SERVICES
- ATTENDANCE_SERVICE_URL
- ASSESSMENT_SERVICE_URL
- ACADEMIC_SERVICE_URL

---

## Local Run

Install dependencies:

python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

Run:

uvicorn main:app --host 0.0.0.0 --port 8000

Typical local mapping for this service is port 8007.

---

## Deployment Notes

- Apply parent-service db-init SQL before first deployment where schema is not present
- Ensure shared JWT secret/internal token policy matches other services
- Ensure referenced upstream services are reachable for integrated child views

---

## Health Check

GET /health

Response:

{
	"status": "ok",
	"service": "parent_service"
}

---

## Production Checklist

- Strong secrets set
- Restricted ALLOWED_HOSTS and ALLOWED_ORIGINS
- Internal service token configured consistently
- Postgres backups enabled
- Logs/alerts configured
- Cross-service integration tests passed
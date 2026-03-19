-- Parent service bootstrap SQL
-- Adds parent-teacher meeting workflow tables.

BEGIN;

CREATE TABLE IF NOT EXISTS public.parent_teacher_meetings (
    id BIGSERIAL PRIMARY KEY,
    parent_id VARCHAR(20) NOT NULL REFERENCES public.parents(id) ON DELETE CASCADE,
    teacher_id VARCHAR(20) NOT NULL REFERENCES public.teachers(id) ON DELETE CASCADE,
    student_id VARCHAR(20) REFERENCES public.students(id) ON DELETE SET NULL,
    meeting_at TIMESTAMPTZ NOT NULL,
    duration_minutes INT NOT NULL DEFAULT 30,
    mode VARCHAR(20) NOT NULL DEFAULT 'ONLINE',
    agenda TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'REQUESTED',
    meeting_link TEXT,
    notes TEXT,
    requested_by VARCHAR(20) NOT NULL REFERENCES public.users(id) ON DELETE SET NULL,
    approved_by VARCHAR(20) REFERENCES public.users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_ptm_duration CHECK (duration_minutes BETWEEN 10 AND 180),
    CONSTRAINT chk_ptm_mode CHECK (mode IN ('ONLINE','OFFLINE','PHONE')),
    CONSTRAINT chk_ptm_status CHECK (status IN ('REQUESTED','APPROVED','REJECTED','COMPLETED','CANCELLED'))
);

CREATE INDEX IF NOT EXISTS idx_ptm_teacher_meeting_time
ON public.parent_teacher_meetings (teacher_id, meeting_at DESC);

CREATE INDEX IF NOT EXISTS idx_ptm_parent_meeting_time
ON public.parent_teacher_meetings (parent_id, meeting_at DESC);

COMMIT;

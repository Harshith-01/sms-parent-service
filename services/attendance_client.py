import os
import requests
from fastapi import HTTPException
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

ATTENDANCE_SERVICE_URL = os.getenv("ATTENDANCE_SERVICE_URL", "").rstrip("/")
INTERNAL_SERVICE_TOKEN = os.getenv("INTERNAL_SERVICE_TOKEN", "")
INTERNAL_SERVICE_NAME = os.getenv("INTERNAL_SERVICE_NAME", "parent-service")
TIMEOUT = 5


def _session() -> requests.Session:
    retry = Retry(
        total=2,
        connect=2,
        read=2,
        backoff_factor=0.3,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "POST"],
    )
    adapter = HTTPAdapter(max_retries=retry)
    sess = requests.Session()
    sess.mount("http://", adapter)
    sess.mount("https://", adapter)
    return sess


def _headers():
    return {
        "Authorization": f"Bearer {INTERNAL_SERVICE_TOKEN}",
        "X-Internal-Service": INTERNAL_SERVICE_NAME,
    }


def get_student_attendance_summary(student_id: str, class_section_id: int, academic_term_id: int) -> dict:
    if not ATTENDANCE_SERVICE_URL:
        return {"integration_enabled": False}
    try:
        r = _session().get(
            f"{ATTENDANCE_SERVICE_URL}/timetable-attendance/attendance/students/{student_id}/summary",
            params={"class_section_id": class_section_id, "academic_term_id": academic_term_id},
            headers=_headers(),
            timeout=TIMEOUT,
        )
        if r.status_code == 404:
            return {"student_id": student_id, "total_sessions": 0, "absences": 0}
        if r.status_code != 200:
            raise HTTPException(502, "Attendance service unavailable")
        return r.json()
    except requests.RequestException:
        raise HTTPException(502, "Attendance service connection error")

import os
import requests
from fastapi import HTTPException
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

ACADEMIC_SERVICE_URL = os.getenv("ACADEMIC_SERVICE_URL", "").rstrip("/")
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


def get_student_timetable(class_section_id: int, academic_term_id: int) -> list:
    if not ACADEMIC_SERVICE_URL:
        return []
    try:
        r = _session().get(
            f"{ACADEMIC_SERVICE_URL}/timetable-attendance/entries/class/{class_section_id}",
            params={"academic_term_id": academic_term_id, "page": 1, "page_size": 200},
            headers=_headers(),
            timeout=TIMEOUT,
        )
    except requests.RequestException:
        raise HTTPException(502, "Academic/Attendance service connection error")
    if r.status_code != 200:
        return []
    data = r.json()
    return data.get("data", []) if isinstance(data, dict) else []

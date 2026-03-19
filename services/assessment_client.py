import os
import requests
from fastapi import HTTPException
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

ASSESSMENT_SERVICE_URL = os.getenv("ASSESSMENT_SERVICE_URL", "").rstrip("/")
INTERNAL_SERVICE_TOKEN = os.getenv("INTERNAL_SERVICE_TOKEN", "")
INTERNAL_SERVICE_NAME = os.getenv("INTERNAL_SERVICE_NAME", "parent-service")
TIMEOUT = 5
MAX_PAGES = 10


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


def get_student_report_cards(student_id: str) -> list:
    if not ASSESSMENT_SERVICE_URL:
        return []
    records = []
    for page in range(1, MAX_PAGES + 1):
        try:
            r = _session().get(
                f"{ASSESSMENT_SERVICE_URL}/assessment/report-cards/student/{student_id}",
                params={"page": page, "page_size": 20},
                headers=_headers(),
                timeout=TIMEOUT,
            )
        except requests.RequestException:
            raise HTTPException(502, "Assessment service connection error")
        if r.status_code == 404:
            return []
        if r.status_code != 200:
            raise HTTPException(502, "Assessment service unavailable")
        data = r.json()
        rows = data.get("data", []) if isinstance(data, dict) else []
        records.extend(rows)
        if len(rows) < 20:
            break
    return records


def get_exam_schedule(
    class_section_id: int,
    academic_year_id: int,
    academic_term_id: int | None = None,
) -> list:
    if not ASSESSMENT_SERVICE_URL:
        return []

    params = {
        "class_section_id": class_section_id,
        "academic_year_id": academic_year_id,
        "page": 1,
        "page_size": 200,
    }
    if academic_term_id is not None:
        params["academic_term_id"] = academic_term_id

    try:
        r = _session().get(
            f"{ASSESSMENT_SERVICE_URL}/assessment/exams",
            params=params,
            headers=_headers(),
            timeout=TIMEOUT,
        )
    except requests.RequestException:
        raise HTTPException(502, "Assessment service connection error")

    if r.status_code != 200:
        raise HTTPException(502, "Assessment service unavailable")

    data = r.json()
    return data.get("data", []) if isinstance(data, dict) else []

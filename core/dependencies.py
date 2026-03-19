from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from core.security import decode_token
from core.config import INTERNAL_SERVICE_TOKEN, INTERNAL_ALLOWED_SERVICES
from secrets import compare_digest

bearer_scheme = HTTPBearer()
ROLE_ALIASES = {"SUPER_ADMIN": "SUPERADMIN"}


def _normalize_role(role: str | None) -> str:
    return ROLE_ALIASES.get(role or "", role or "")


def _has_required_role(actual_role: str, allowed_roles: list[str]) -> bool:
    actual = _normalize_role(actual_role)
    allowed = {_normalize_role(r) for r in allowed_roles}
    if actual in {"SUPERADMIN"}:
        return True
    if "ADMIN" in allowed and actual in {"ADMIN", "SUPERADMIN"}:
        return True
    return actual in allowed


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
):
    token = credentials.credentials
    if INTERNAL_SERVICE_TOKEN and compare_digest(token, INTERNAL_SERVICE_TOKEN):
        service_name = request.headers.get("x-internal-service", "unknown").strip() or "unknown"
        if INTERNAL_ALLOWED_SERVICES and service_name not in INTERNAL_ALLOWED_SERVICES:
            raise HTTPException(status_code=403, detail="Service identity not allowed")
        return {"sub": f"svc:{service_name}", "role": "SERVICE", "principal_type": "service"}
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return payload


def require_role(allowed_roles: list):
    def checker(user=Depends(get_current_user)):
        user["user_id"] = user.get("sub", "")
        if not _has_required_role(user.get("role", ""), allowed_roles):
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user
    return checker

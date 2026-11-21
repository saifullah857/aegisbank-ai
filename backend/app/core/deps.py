"""Authentication + role checks shared by all routers.

Roles: ADMIN (everything) · FRAUD_ANALYST (investigate) · AUDITOR (read + audit log) · VIEWER (read only).
The role is re-read from the database on every request, never trusted from the token alone, so a
demotion or deactivation takes effect on the very next call.
"""
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.base import AuditLog, User
from app.db.session import get_db

bearer = HTTPBearer(auto_error=False)
INVESTIGATE = ("ADMIN", "FRAUD_ANALYST")
AUDIT = ("ADMIN", "AUDITOR")


def current_user(cred: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)) -> User:
    claims = decode_access_token(cred.credentials) if cred else None
    user = db.query(User).filter(User.username == claims["sub"]).first() if claims else None
    if not user or not user.is_active:
        raise HTTPException(401, "Not authenticated", headers={"WWW-Authenticate": "Bearer"})
    return user


def require_roles(*roles: str):
    def dep(user: User = Depends(current_user), db: Session = Depends(get_db)) -> User:
        if user.role not in roles:
            log_audit(db, user.username, "ACCESS_DENIED", details={"required_roles": list(roles), "actual_role": user.role})
            db.commit()  # the denial itself must be recorded even though the request fails
            raise HTTPException(403, "Your role does not permit this action")
        return user

    return dep


def log_audit(db: Session, actor: str | None, action: str, case_id: int | None = None,
              previous_status: str | None = None, new_status: str | None = None, details: dict | None = None) -> None:
    db.add(AuditLog(actor=actor, action=action, case_id=case_id, previous_status=previous_status,
                    new_status=new_status, details=details or {}))

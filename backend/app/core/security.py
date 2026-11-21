from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.core.config import get_settings


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except ValueError:
        return False


def create_access_token(subject: str, role: str) -> str:
    s = get_settings()
    exp = datetime.now(timezone.utc) + timedelta(minutes=s.ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode({"sub": subject, "role": role, "exp": exp}, s.JWT_SECRET, algorithm=s.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict | None:
    s = get_settings()
    try:
        # The algorithm list is pinned: tokens using any other algorithm (including "none") are rejected.
        return jwt.decode(token, s.JWT_SECRET, algorithms=[s.JWT_ALGORITHM])
    except jwt.PyJWTError:
        return None

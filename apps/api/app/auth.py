import hashlib
import secrets
from datetime import timedelta

from argon2 import PasswordHasher
from fastapi import Cookie, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from .db import get_db
from .config import get_settings
from .models import Membership, SessionToken, User, utcnow

password_hasher = PasswordHasher()
SESSION_COOKIE = "signalflow_session"
CSRF_COOKIE = "signalflow_csrf"


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    try:
        return password_hasher.verify(hashed, password)
    except Exception:
        return False


def digest_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def issue_session(response: Response, db: Session, user: User) -> str:
    token = secrets.token_urlsafe(32)
    csrf = secrets.token_urlsafe(24)
    session = SessionToken(
        token_hash=digest_token(token),
        user_id=user.id,
        expires_at=utcnow() + timedelta(days=7),
    )
    db.add(session)
    secure = get_settings().app_env not in {"development", "test"}
    response.set_cookie(SESSION_COOKIE, token, httponly=True, samesite="lax", secure=secure, max_age=7 * 86400)
    response.set_cookie(CSRF_COOKIE, csrf, httponly=False, samesite="lax", secure=secure, max_age=7 * 86400)
    return csrf


def current_user(
    session_token: str | None = Cookie(default=None, alias=SESSION_COOKIE),
    db: Session = Depends(get_db),
) -> User:
    if not session_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    record = db.query(SessionToken).filter(SessionToken.token_hash == digest_token(session_token)).first()
    if not record or record.expires_at <= utcnow():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired")
    user = db.get(User, record.user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


def workspace_membership(workspace_id: str, user: User, db: Session) -> Membership:
    membership = db.query(Membership).filter(
        Membership.workspace_id == workspace_id, Membership.user_id == user.id
    ).first()
    if not membership:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Workspace access denied")
    return membership


def require_roles(membership: Membership, *roles: str) -> None:
    if membership.role not in roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")


def verify_csrf(cookie_value: str | None, header_value: str | None) -> None:
    if not cookie_value or not header_value or not secrets.compare_digest(cookie_value, header_value):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF validation failed")

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models.stocky import RoleDB, UserDB


def _auth_error(message: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"code": "AUTH_ERROR", "message": message},
    )


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000)
    return f"{salt}${digest.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        salt, expected = stored_hash.split("$", 1)
    except ValueError:
        return False
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000).hex()
    return hmac.compare_digest(digest, expected)


def _get_secret() -> str:
    return os.getenv("AUTH_SECRET_KEY", "change-me-stocky-secret")


def create_access_token(user_id: str) -> tuple[str, datetime]:
    expires_in_minutes = int(os.getenv("AUTH_TOKEN_EXPIRE_MINUTES", "480"))
    expires_at = datetime.now(UTC) + timedelta(minutes=expires_in_minutes)
    payload = {"sub": user_id, "exp": expires_at.isoformat()}
    body = json.dumps(payload, separators=(",", ":"), ensure_ascii=True).encode()
    encoded = base64.urlsafe_b64encode(body).decode().rstrip("=")
    signature = hmac.new(_get_secret().encode(), encoded.encode(), hashlib.sha256).hexdigest()
    return f"{encoded}.{signature}", expires_at


def decode_access_token(token: str) -> dict[str, str]:
    try:
        encoded, signature = token.split(".", 1)
    except ValueError as exc:
        raise _auth_error("Неверный формат токена") from exc

    expected_signature = hmac.new(_get_secret().encode(), encoded.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected_signature):
        raise _auth_error("Недействительный токен")

    padding = "=" * (-len(encoded) % 4)
    try:
        payload = json.loads(base64.urlsafe_b64decode(encoded + padding).decode())
    except (json.JSONDecodeError, ValueError) as exc:
        raise _auth_error("Не удалось прочитать токен") from exc

    exp_value = payload.get("exp")
    sub = payload.get("sub")
    if not sub or not exp_value:
        raise _auth_error("Токен поврежден")

    expires_at = datetime.fromisoformat(exp_value)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    if expires_at <= datetime.now(UTC):
        raise _auth_error("Срок действия токена истек")

    return {"sub": str(sub), "exp": exp_value}


def authenticate_token(token: str, db: Session) -> UserDB:
    payload = decode_access_token(token)
    user = (
        db.query(UserDB)
        .options(joinedload(UserDB.role))
        .filter(UserDB.id == payload["sub"], UserDB.is_active.is_(True))
        .first()
    )
    if not user:
        raise _auth_error("Пользователь не найден или деактивирован")
    return user


def get_current_user(
    authorization: str | None = Header(default=None, alias="Authorization"),
    x_access_token: str | None = Header(default=None, alias="X-Access-Token"),
    access_token: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> UserDB:
    raw_token = authorization or x_access_token or access_token
    if not raw_token:
        raise _auth_error("Требуется Bearer токен")

    scheme, _, token = raw_token.partition(" ")
    if scheme.lower() == "bearer" and token:
        normalized_token = token
    else:
        normalized_token = raw_token.strip()
        if not normalized_token:
            raise _auth_error("Ожидается заголовок Authorization: Bearer <token>")

    return authenticate_token(normalized_token, db)


CurrentUser = Annotated[UserDB, Depends(get_current_user)]

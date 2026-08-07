import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import text
from sqlalchemy.orm import Session

SECRET_KEY = os.getenv(
    "ASHACONNECT_SECRET_KEY",
    "CHANGE_THIS_SECRET_BEFORE_DEPLOYMENT_ASHACONNECT_2026",
)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "480"))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    if not password_hash:
        return False

    try:
        return pwd_context.verify(password, password_hash)
    except Exception:
        return False


def create_access_token(data: dict, expires_minutes: Optional[int] = None) -> str:
    payload = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=expires_minutes or ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload.update({"exp": expire})
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return {}


def role_value(role) -> str:
    if hasattr(role, "value"):
        return role.value
    return str(role or "").strip()


def audit_log(
    db: Session,
    actor_type: str,
    actor_id: str,
    actor_role: str,
    action: str,
    entity_type: str = "",
    entity_id: str = "",
    details: str = "",
):
    try:
        db.execute(
            text(
                """
                INSERT INTO audit_logs
                (actor_type, actor_id, actor_role, action, entity_type, entity_id, details, created_at)
                VALUES
                (:actor_type, :actor_id, :actor_role, :action, :entity_type, :entity_id, :details, :created_at)
                """
            ),
            {
                "actor_type": actor_type,
                "actor_id": str(actor_id or ""),
                "actor_role": str(actor_role or ""),
                "action": action,
                "entity_type": entity_type,
                "entity_id": str(entity_id or ""),
                "details": details,
                "created_at": datetime.utcnow().isoformat(),
            },
        )
        db.commit()
    except Exception:
        db.rollback()

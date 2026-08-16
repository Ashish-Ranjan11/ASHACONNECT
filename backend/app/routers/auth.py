from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session

from app.db.mysql import get_db
from app.deps import get_current_worker
from app.models import AshaWorker
from app.security import (
    audit_log,
    create_access_token,
    hash_password,
    role_value,
    verify_password,
)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


def worker_json(worker: AshaWorker):
    return {
        "worker_id": worker.worker_id,
        "id": worker.worker_id,
        "name": worker.name,
        "email": worker.email,
        "phone_no": worker.phone_no,
        "village": worker.village,
        "address": worker.address,
        "qualification": worker.qualification,
        "phc_id": worker.phc_id,
        "role": role_value(worker.role),
        "sos_id": worker.sos_id,
        "is_active": worker.is_active,
    }


@router.post("/login")
def login(payload: dict = Body(...), db: Session = Depends(get_db)):
    email = str(payload.get("email") or "").strip().lower()
    password = str(payload.get("password") or "")

    if not email or not password:
        raise HTTPException(status_code=400, detail="Email and password are required")

    worker = db.query(AshaWorker).filter(AshaWorker.email == email).first()

    if not worker:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if hasattr(worker, "is_active") and not worker.is_active:
        raise HTTPException(status_code=403, detail="Account is disabled")

    password_ok = verify_password(password, worker.password_hash)

    # Temporary legacy support: if an old demo account stored plain password,
    # allow login once and immediately upgrade it to hashed password.
    if not password_ok and password == worker.password_hash:
        worker.password_hash = hash_password(password)
        db.commit()
        password_ok = True

    if not password_ok:
        audit_log(
            db,
            actor_type="staff",
            actor_id=worker.worker_id,
            actor_role=role_value(worker.role),
            action="LOGIN_FAILED",
            entity_type="AshaWorker",
            entity_id=worker.worker_id,
            details=f"Failed login for {email}",
        )
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token(
        {
            "sub": str(worker.worker_id),
            "email": worker.email,
            "role": role_value(worker.role),
            "account_type": "staff",
        }
    )

    audit_log(
        db,
        actor_type="staff",
        actor_id=worker.worker_id,
        actor_role=role_value(worker.role),
        action="LOGIN_SUCCESS",
        entity_type="AshaWorker",
        entity_id=worker.worker_id,
        details=f"Staff login for {email}",
    )

    return {
        "access_token": token,
        "token_type": "bearer",
        "role": role_value(worker.role),
        "user": worker_json(worker),
    }


@router.get("/me")
def me(current: AshaWorker = Depends(get_current_worker)):
    return worker_json(current)

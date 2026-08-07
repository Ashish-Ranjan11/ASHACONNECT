from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.mysql import get_db
from app.deps import get_current_worker, require_roles, visible_worker_ids
from app.models import AshaWorker
from app.security import audit_log, hash_password, role_value, verify_password

router = APIRouter(prefix="/api/security", tags=["Security & RBAC"])


def worker_json(worker: AshaWorker):
    return {
        "worker_id": worker.worker_id,
        "name": worker.name,
        "email": worker.email,
        "phone_no": worker.phone_no,
        "village": worker.village,
        "qualification": worker.qualification,
        "phc_id": worker.phc_id,
        "role": role_value(worker.role),
        "is_active": worker.is_active,
        "sos_id": worker.sos_id,
    }


@router.get("/access-scope")
def access_scope(
    db: Session = Depends(get_db),
    current: AshaWorker = Depends(get_current_worker),
):
    ids = visible_worker_ids(db, current)

    return {
        "current_user": worker_json(current),
        "visible_worker_ids": ids,
        "access_type": "phc_scope" if role_value(current.role) in ["phc_admin", "supervisor"] else "own_records_only",
    }


@router.get("/workers")
def list_workers(
    db: Session = Depends(get_db),
    current: AshaWorker = Depends(require_roles("phc_admin", "supervisor")),
):
    ids = visible_worker_ids(db, current)

    workers = (
        db.query(AshaWorker)
        .filter(AshaWorker.worker_id.in_(ids))
        .order_by(AshaWorker.worker_id.asc())
        .all()
    )

    audit_log(
        db,
        "staff",
        current.worker_id,
        role_value(current.role),
        "VIEW_WORKERS",
        "AshaWorker",
        "",
        "Viewed worker list",
    )

    return [worker_json(worker) for worker in workers]


@router.post("/workers")
def create_or_update_worker(
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    current: AshaWorker = Depends(require_roles("phc_admin", "supervisor")),
):
    email = str(payload.get("email") or "").strip().lower()
    password = str(payload.get("password") or "").strip()
    name = str(payload.get("name") or "").strip()
    role = str(payload.get("role") or "asha").strip()

    allowed_roles = ["asha", "phc_admin", "supervisor"]

    if role not in allowed_roles:
        raise HTTPException(status_code=400, detail="Invalid role")

    if not email or not name:
        raise HTTPException(status_code=400, detail="Name and email are required")

    worker = db.query(AshaWorker).filter(AshaWorker.email == email).first()

    if worker:
        worker.name = name
        worker.phone_no = str(payload.get("phone_no") or worker.phone_no or "")
        worker.village = str(payload.get("village") or worker.village or "")
        worker.address = str(payload.get("address") or worker.address or worker.village or "")
        worker.qualification = str(payload.get("qualification") or worker.qualification or "")
        worker.role = role
        worker.is_active = bool(payload.get("is_active", True))

        if password:
            worker.password_hash = hash_password(password)

        action = "UPDATE_WORKER"
    else:
        if not password:
            raise HTTPException(status_code=400, detail="Password is required for new account")

        worker = AshaWorker(
            name=name,
            email=email,
            phone_no=str(payload.get("phone_no") or f"90000{len(email)}999"),
            password_hash=hash_password(password),
            village=str(payload.get("village") or ""),
            address=str(payload.get("address") or payload.get("village") or ""),
            age=int(payload.get("age") or 30),
            gender=str(payload.get("gender") or "Female"),
            qualification=str(payload.get("qualification") or ""),
            phc_id=payload.get("phc_id") or current.phc_id,
            is_active=True,
            role=role,
            sos_id=str(payload.get("sos_id") or f"SOS-{email.split('@')[0].upper()}"),
        )
        db.add(worker)
        action = "CREATE_WORKER"

    db.commit()
    db.refresh(worker)

    audit_log(
        db,
        "staff",
        current.worker_id,
        role_value(current.role),
        action,
        "AshaWorker",
        worker.worker_id,
        f"{action}: {worker.email}",
    )

    return {
        "message": "Worker account saved successfully",
        "worker": worker_json(worker),
    }


@router.post("/change-password")
def change_password(
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    current: AshaWorker = Depends(get_current_worker),
):
    old_password = str(payload.get("old_password") or "")
    new_password = str(payload.get("new_password") or "")

    if len(new_password) < 8:
        raise HTTPException(status_code=400, detail="New password must be at least 8 characters")

    if not verify_password(old_password, current.password_hash):
        raise HTTPException(status_code=401, detail="Old password is incorrect")

    current.password_hash = hash_password(new_password)
    db.commit()

    audit_log(
        db,
        "staff",
        current.worker_id,
        role_value(current.role),
        "CHANGE_PASSWORD",
        "AshaWorker",
        current.worker_id,
        "Password changed",
    )

    return "Password changed successfully"


@router.get("/audit-logs")
def audit_logs(
    limit: int = 100,
    db: Session = Depends(get_db),
    current: AshaWorker = Depends(require_roles("phc_admin", "supervisor")),
):
    rows = db.execute(
        text(
            """
            SELECT id, actor_type, actor_id, actor_role, action, entity_type, entity_id, details, created_at
            FROM audit_logs
            ORDER BY id DESC
            LIMIT :limit
            """
        ),
        {"limit": min(limit, 300)},
    ).mappings().all()

    return [dict(row) for row in rows]

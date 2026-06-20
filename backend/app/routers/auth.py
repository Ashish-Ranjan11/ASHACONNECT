from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.mysql import get_db
from app.deps import get_current_worker, visible_worker_ids, require_roles
from app.models import AshaWorker, PrimaryHealthCentre
from app.schemas import AshaWorkerCreate, AshaWorkerOut, LoginRequest, PHCCreate, PHCOut, Token
from app.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["Auth"])


def worker_payload(worker: AshaWorker):
    return {
        "worker_id": worker.worker_id,
        "name": worker.name,
        "email": worker.email,
        "role": worker.role,
        "village": worker.village,
        "phc_id": worker.phc_id,
        "phc": worker.phc.name if worker.phc else None,
        "sos_id": worker.sos_id,
    }


@router.post("/login", response_model=Token)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    worker = db.query(AshaWorker).filter(AshaWorker.email == payload.email).first()

    if not worker or not verify_password(payload.password, worker.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    if not worker.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account inactive")

    token = create_access_token(subject=str(worker.worker_id))

    return {
        "access_token": token,
        "token_type": "bearer",
        "worker": worker_payload(worker),
    }


@router.get("/me")
def me(current: AshaWorker = Depends(get_current_worker)):
    return worker_payload(current)


@router.get("/demo-users")
def demo_users():
    return [
        {"role": "ASHA Worker", "email": "asha@example.com", "password": "password123"},
        {"role": "ASHA Worker 2", "email": "asha2@example.com", "password": "password123"},
        {"role": "PHC Admin", "email": "phcadmin@example.com", "password": "password123"},
        {"role": "Supervisor", "email": "supervisor@example.com", "password": "password123"},
    ]


@router.post("/create-phc", response_model=PHCOut)
def create_phc(
    payload: PHCCreate,
    db: Session = Depends(get_db),
    current: AshaWorker = Depends(require_roles("supervisor")),
):
    phc = PrimaryHealthCentre(**payload.model_dump())
    db.add(phc)
    db.commit()
    db.refresh(phc)
    return phc


@router.post("/register-worker", response_model=AshaWorkerOut)
def register_worker(
    payload: AshaWorkerCreate,
    db: Session = Depends(get_db),
    current: AshaWorker = Depends(require_roles("phc_admin", "supervisor")),
):
    existing = db.query(AshaWorker).filter(
        (AshaWorker.email == payload.email) | (AshaWorker.phone_no == payload.phone_no)
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="Email or phone already registered")

    if current.role == "phc_admin":
        payload.phc_id = current.phc_id

    data = payload.model_dump(exclude={"password"})
    data["password_hash"] = hash_password(payload.password)

    worker = AshaWorker(**data)
    db.add(worker)
    db.commit()
    db.refresh(worker)
    return worker


@router.get("/workers", response_model=list[AshaWorkerOut])
def list_workers(
    db: Session = Depends(get_db),
    current: AshaWorker = Depends(require_roles("phc_admin", "supervisor")),
):
    query = db.query(AshaWorker).filter(AshaWorker.worker_id.in_(visible_worker_ids(db, current)))
    return query.order_by(AshaWorker.worker_id.asc()).all()

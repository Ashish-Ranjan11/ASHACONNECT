from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.mysql import get_db
from app.models import AshaWorker, PrimaryHealthCentre
from app.schemas import AshaWorkerCreate, AshaWorkerOut, LoginRequest, PHCCreate, PHCOut, Token
from app.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["Auth"])


@router.post("/create-phc", response_model=PHCOut)
def create_phc(payload: PHCCreate, db: Session = Depends(get_db)):
    phc = PrimaryHealthCentre(**payload.model_dump())
    db.add(phc)
    db.commit()
    db.refresh(phc)
    return phc


@router.post("/register-worker", response_model=AshaWorkerOut)
def register_worker(payload: AshaWorkerCreate, db: Session = Depends(get_db)):
    existing = db.query(AshaWorker).filter(
        (AshaWorker.email == payload.email) | (AshaWorker.phone_no == payload.phone_no)
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email or phone already registered")

    data = payload.model_dump(exclude={"password"})
    data["password_hash"] = hash_password(payload.password)
    worker = AshaWorker(**data)
    db.add(worker)
    db.commit()
    db.refresh(worker)
    return worker


@router.post("/login", response_model=Token)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    worker = db.query(AshaWorker).filter(AshaWorker.email == payload.email).first()
    if not worker or not verify_password(payload.password, worker.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    token = create_access_token(subject=str(worker.worker_id))
    return {
        "access_token": token,
        "token_type": "bearer",
        "worker": {
            "worker_id": worker.worker_id,
            "name": worker.name,
            "email": worker.email,
            "role": worker.role,
            "village": worker.village,
        },
    }

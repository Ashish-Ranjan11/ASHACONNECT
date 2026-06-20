from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.db.mysql import get_db
from app.models import AshaWorker, Beneficiary
from app.security import decode_access_token

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_worker(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> AshaWorker:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing token")

    worker_id = decode_access_token(credentials.credentials)
    if not worker_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    worker = db.get(AshaWorker, int(worker_id))
    if not worker or not worker.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Worker not found or inactive")

    return worker


def visible_worker_ids(db: Session, current: AshaWorker) -> list[int]:
    if current.role == "asha":
        return [current.worker_id]

    if current.role == "phc_admin":
        rows = db.query(AshaWorker.worker_id).filter(
            AshaWorker.phc_id == current.phc_id,
            AshaWorker.is_active == True,
        ).all()
        return [r[0] for r in rows]

    return [r[0] for r in db.query(AshaWorker.worker_id).filter(AshaWorker.is_active == True).all()]


def scoped_beneficiary_query(db: Session, current: AshaWorker):
    return db.query(Beneficiary).filter(Beneficiary.asha_worker_id.in_(visible_worker_ids(db, current)))


def ensure_beneficiary_access(db: Session, beneficiary_id: int, current: AshaWorker) -> Beneficiary:
    beneficiary = db.get(Beneficiary, beneficiary_id)

    if not beneficiary:
        raise HTTPException(status_code=404, detail="Beneficiary not found")

    if beneficiary.asha_worker_id not in visible_worker_ids(db, current):
        raise HTTPException(status_code=403, detail="You do not have access to this beneficiary")

    return beneficiary


def require_roles(*roles):
    def checker(current: AshaWorker = Depends(get_current_worker)):
        if current.role not in roles:
            raise HTTPException(status_code=403, detail="Role not allowed")
        return current

    return checker

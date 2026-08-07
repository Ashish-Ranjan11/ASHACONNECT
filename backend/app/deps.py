from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.db.mysql import get_db
from app.models import AshaWorker, Beneficiary
from app.security import decode_access_token, role_value

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def get_current_worker(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    payload = decode_access_token(token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    if payload.get("account_type", "staff") != "staff":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint requires staff access",
        )

    worker_id = payload.get("sub")

    if not worker_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    worker = db.get(AshaWorker, int(worker_id))

    if not worker:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Worker account not found",
        )

    if hasattr(worker, "is_active") and not worker.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled",
        )

    return worker


def require_roles(*allowed_roles):
    def checker(current: AshaWorker = Depends(get_current_worker)):
        current_role = role_value(current.role)

        if current_role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission for this action",
            )

        return current

    return checker


def visible_worker_ids(db: Session, current: AshaWorker):
    current_role = role_value(current.role)

    if current_role in ["phc_admin", "supervisor"]:
        query = db.query(AshaWorker.worker_id)

        if getattr(current, "phc_id", None):
            query = query.filter(AshaWorker.phc_id == current.phc_id)

        return [row[0] for row in query.all()]

    return [current.worker_id]


def scoped_beneficiary_query(db: Session, current: AshaWorker):
    """
    Returns a beneficiary query filtered by the current user's role.

    ASHA Worker:
      - only beneficiaries assigned to that ASHA worker

    PHC Admin / Supervisor:
      - beneficiaries assigned to ASHA workers under the same PHC scope
    """
    ids = visible_worker_ids(db, current)

    query = db.query(Beneficiary)

    if hasattr(Beneficiary, "asha_worker_id"):
        query = query.filter(Beneficiary.asha_worker_id.in_(ids))

    return query


def can_access_beneficiary(db: Session, current: AshaWorker, beneficiary_id: int):
    beneficiary = db.get(Beneficiary, beneficiary_id)

    if not beneficiary:
        raise HTTPException(status_code=404, detail="Beneficiary not found")

    ids = visible_worker_ids(db, current)

    if hasattr(beneficiary, "asha_worker_id") and beneficiary.asha_worker_id not in ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this beneficiary",
        )

    return beneficiary

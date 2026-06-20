from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.mysql import get_db
from app.deps import get_current_worker, scoped_beneficiary_query, ensure_beneficiary_access, visible_worker_ids
from app.models import AshaWorker, Beneficiary
from app.schemas import BeneficiaryCreate, BeneficiaryOut, BeneficiaryUpdate

router = APIRouter(prefix="/api/beneficiaries", tags=["Beneficiaries"])


@router.get("", response_model=list[BeneficiaryOut])
def list_beneficiaries(
    db: Session = Depends(get_db),
    current: AshaWorker = Depends(get_current_worker),
):
    return scoped_beneficiary_query(db, current).order_by(Beneficiary.beneficiary_id.desc()).all()


@router.post("", response_model=BeneficiaryOut)
def create_beneficiary(
    payload: BeneficiaryCreate,
    db: Session = Depends(get_db),
    current: AshaWorker = Depends(get_current_worker),
):
    data = payload.model_dump()

    requested_worker_id = data.pop("asha_worker_id", None)

    if current.role == "asha":
        assigned_worker_id = current.worker_id
    else:
        assigned_worker_id = requested_worker_id or current.worker_id

        if assigned_worker_id not in visible_worker_ids(db, current):
            raise HTTPException(status_code=403, detail="Cannot assign beneficiary to this worker")

    beneficiary = Beneficiary(**data, asha_worker_id=assigned_worker_id)
    db.add(beneficiary)
    db.commit()
    db.refresh(beneficiary)
    return beneficiary


@router.get("/{beneficiary_id}", response_model=BeneficiaryOut)
def get_beneficiary(
    beneficiary_id: int,
    db: Session = Depends(get_db),
    current: AshaWorker = Depends(get_current_worker),
):
    return ensure_beneficiary_access(db, beneficiary_id, current)


@router.put("/{beneficiary_id}", response_model=BeneficiaryOut)
def update_beneficiary(
    beneficiary_id: int,
    payload: BeneficiaryUpdate,
    db: Session = Depends(get_db),
    current: AshaWorker = Depends(get_current_worker),
):
    beneficiary = ensure_beneficiary_access(db, beneficiary_id, current)

    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(beneficiary, key, value)

    db.commit()
    db.refresh(beneficiary)
    return beneficiary


@router.delete("/{beneficiary_id}")
def deactivate_beneficiary(
    beneficiary_id: int,
    db: Session = Depends(get_db),
    current: AshaWorker = Depends(get_current_worker),
):
    beneficiary = ensure_beneficiary_access(db, beneficiary_id, current)
    beneficiary.is_active = False
    db.commit()
    return {"message": "Beneficiary deactivated"}

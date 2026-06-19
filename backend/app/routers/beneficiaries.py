from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.mysql import get_db
from app.deps import get_current_worker
from app.models import AshaWorker, Beneficiary
from app.schemas import BeneficiaryCreate, BeneficiaryOut, BeneficiaryUpdate

router = APIRouter(prefix="/api/beneficiaries", tags=["Beneficiaries"])


@router.get("", response_model=list[BeneficiaryOut])
def list_beneficiaries(db: Session = Depends(get_db), current: AshaWorker = Depends(get_current_worker)):
    query = db.query(Beneficiary)
    if current.role == "asha":
        query = query.filter(Beneficiary.asha_worker_id == current.worker_id)
    return query.order_by(Beneficiary.beneficiary_id.desc()).all()


@router.post("", response_model=BeneficiaryOut)
def create_beneficiary(payload: BeneficiaryCreate, db: Session = Depends(get_db), current: AshaWorker = Depends(get_current_worker)):
    beneficiary = Beneficiary(**payload.model_dump(), asha_worker_id=current.worker_id)
    db.add(beneficiary)
    db.commit()
    db.refresh(beneficiary)
    return beneficiary


@router.get("/{beneficiary_id}", response_model=BeneficiaryOut)
def get_beneficiary(beneficiary_id: int, db: Session = Depends(get_db), current: AshaWorker = Depends(get_current_worker)):
    beneficiary = db.get(Beneficiary, beneficiary_id)
    if not beneficiary:
        raise HTTPException(status_code=404, detail="Beneficiary not found")
    if current.role == "asha" and beneficiary.asha_worker_id != current.worker_id:
        raise HTTPException(status_code=403, detail="Not allowed")
    return beneficiary


@router.put("/{beneficiary_id}", response_model=BeneficiaryOut)
def update_beneficiary(beneficiary_id: int, payload: BeneficiaryUpdate, db: Session = Depends(get_db), current: AshaWorker = Depends(get_current_worker)):
    beneficiary = get_beneficiary(beneficiary_id, db, current)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(beneficiary, key, value)
    db.commit()
    db.refresh(beneficiary)
    return beneficiary


@router.delete("/{beneficiary_id}")
def deactivate_beneficiary(beneficiary_id: int, db: Session = Depends(get_db), current: AshaWorker = Depends(get_current_worker)):
    beneficiary = get_beneficiary(beneficiary_id, db, current)
    beneficiary.is_active = False
    db.commit()
    return {"message": "Beneficiary deactivated"}

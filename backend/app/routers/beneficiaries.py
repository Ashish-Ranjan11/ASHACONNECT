from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session

from app.db.mysql import get_db
from app.deps import get_current_worker, visible_worker_ids
from app.models import AshaWorker, Beneficiary

router = APIRouter(prefix="/api/beneficiaries", tags=["Beneficiaries"])


def ensure_access(db: Session, beneficiary_id: int, current: AshaWorker):
    worker_ids = visible_worker_ids(db, current)

    beneficiary = (
        db.query(Beneficiary)
        .filter(Beneficiary.beneficiary_id == beneficiary_id)
        .first()
    )

    if not beneficiary:
        raise HTTPException(status_code=404, detail="Beneficiary not found")

    if beneficiary.asha_worker_id not in worker_ids:
        raise HTTPException(status_code=403, detail="Access denied")

    return beneficiary


@router.get("")
def list_beneficiaries(
    db: Session = Depends(get_db),
    current: AshaWorker = Depends(get_current_worker),
):
    worker_ids = visible_worker_ids(db, current)

    return (
        db.query(Beneficiary)
        .filter(Beneficiary.asha_worker_id.in_(worker_ids))
        .order_by(Beneficiary.beneficiary_id.desc())
        .all()
    )


@router.post("")
def create_beneficiary(
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    current: AshaWorker = Depends(get_current_worker),
):
    required_fields = ["name", "age", "gender", "village", "category"]

    for field in required_fields:
        if payload.get(field) in [None, ""]:
            raise HTTPException(status_code=400, detail=f"{field} is required")

    worker_ids = visible_worker_ids(db, current)
    role = (current.role or "").lower()

    selected_worker_id = payload.get("asha_worker_id")

    if role in ["phc_admin", "supervisor", "admin"] and selected_worker_id:
        selected_worker_id = int(selected_worker_id)

        if selected_worker_id not in worker_ids:
            raise HTTPException(status_code=403, detail="Invalid ASHA worker selected")
    else:
        selected_worker_id = current.worker_id

    beneficiary = Beneficiary(
        name=payload.get("name"),
        age=int(payload.get("age")),
        gender=payload.get("gender"),
        phone=payload.get("phone"),
        village=payload.get("village"),
        category=payload.get("category"),
        address=payload.get("address"),
        asha_worker_id=selected_worker_id,
    )

    db.add(beneficiary)
    db.commit()
    db.refresh(beneficiary)

    return beneficiary


@router.put("/{beneficiary_id}")
def update_beneficiary(
    beneficiary_id: int,
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    current: AshaWorker = Depends(get_current_worker),
):
    beneficiary = ensure_access(db, beneficiary_id, current)

    allowed_fields = [
        "name",
        "age",
        "gender",
        "phone",
        "village",
        "category",
        "address",
    ]

    for field in allowed_fields:
        if field in payload:
            value = payload.get(field)

            if field == "age" and value not in [None, ""]:
                value = int(value)

            setattr(beneficiary, field, value)

    db.commit()
    db.refresh(beneficiary)

    return {
        "message": "Beneficiary updated successfully",
        "beneficiary": beneficiary,
    }


@router.delete("/{beneficiary_id}")
def delete_beneficiary(
    beneficiary_id: int,
    db: Session = Depends(get_db),
    current: AshaWorker = Depends(get_current_worker),
):
    beneficiary = ensure_access(db, beneficiary_id, current)

    db.delete(beneficiary)
    db.commit()

    return {
        "message": "Beneficiary deleted successfully",
        "beneficiary_id": beneficiary_id,
    }
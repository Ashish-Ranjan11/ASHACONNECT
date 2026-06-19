from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.mysql import get_db
from app.deps import get_current_worker
from app.models import AshaWorker, Beneficiary, ImmunizationRecord, PregnancyRecord, Record
from app.schemas import (
    ImmunizationRecordCreate,
    ImmunizationRecordOut,
    ImmunizationRecordUpdate,
    PregnancyRecordCreate,
    PregnancyRecordOut,
    RecordCreate,
    RecordOut,
)

router = APIRouter(prefix="/api/records", tags=["Clinical Records"])


def _check_beneficiary(db: Session, beneficiary_id: int, current: AshaWorker):
    beneficiary = db.get(Beneficiary, beneficiary_id)
    if not beneficiary:
        raise HTTPException(status_code=404, detail="Beneficiary not found")
    if current.role == "asha" and beneficiary.asha_worker_id != current.worker_id:
        raise HTTPException(status_code=403, detail="Not allowed")
    return beneficiary


@router.post("/general", response_model=RecordOut)
def add_general_record(payload: RecordCreate, db: Session = Depends(get_db), current: AshaWorker = Depends(get_current_worker)):
    _check_beneficiary(db, payload.beneficiary_id, current)
    record = Record(**payload.model_dump(), created_by=current.worker_id)
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.get("/beneficiary/{beneficiary_id}/general", response_model=list[RecordOut])
def list_general_records(beneficiary_id: int, db: Session = Depends(get_db), current: AshaWorker = Depends(get_current_worker)):
    _check_beneficiary(db, beneficiary_id, current)
    return db.query(Record).filter(Record.beneficiary_id == beneficiary_id).order_by(Record.record_date.desc()).all()


@router.post("/pregnancy", response_model=PregnancyRecordOut)
def add_pregnancy_record(payload: PregnancyRecordCreate, db: Session = Depends(get_db), current: AshaWorker = Depends(get_current_worker)):
    beneficiary = _check_beneficiary(db, payload.beneficiary_id, current)
    data = payload.model_dump()
    if data.get("expected_delivery_date") is None and payload.lmp_date:
        data["expected_delivery_date"] = payload.lmp_date + timedelta(days=280)

    # Simple decision-support high-risk flag for demo purpose.
    if payload.hemoglobin_level is not None and payload.hemoglobin_level < 11:
        data["status"] = "high_risk"
    if payload.blood_pressure and payload.blood_pressure.replace(" ", "") in {"140/90", "150/100", "160/100"}:
        data["status"] = "high_risk"

    pregnancy = PregnancyRecord(**data, created_by=current.worker_id)
    beneficiary.category = "pregnant"
    db.add(pregnancy)
    db.commit()
    db.refresh(pregnancy)
    return pregnancy


@router.get("/pregnancy", response_model=list[PregnancyRecordOut])
def list_pregnancy_records(db: Session = Depends(get_db), current: AshaWorker = Depends(get_current_worker)):
    query = db.query(PregnancyRecord).join(Beneficiary)
    if current.role == "asha":
        query = query.filter(Beneficiary.asha_worker_id == current.worker_id)
    return query.order_by(PregnancyRecord.pregnancy_id.desc()).all()


@router.post("/immunization", response_model=ImmunizationRecordOut)
def add_immunization_record(payload: ImmunizationRecordCreate, db: Session = Depends(get_db), current: AshaWorker = Depends(get_current_worker)):
    beneficiary = _check_beneficiary(db, payload.beneficiary_id, current)
    immunization = ImmunizationRecord(**payload.model_dump(), created_by=current.worker_id)
    if beneficiary.category == "general":
        beneficiary.category = "child"
    db.add(immunization)
    db.commit()
    db.refresh(immunization)
    return immunization


@router.get("/immunization", response_model=list[ImmunizationRecordOut])
def list_immunization_records(db: Session = Depends(get_db), current: AshaWorker = Depends(get_current_worker)):
    query = db.query(ImmunizationRecord).join(Beneficiary)
    if current.role == "asha":
        query = query.filter(Beneficiary.asha_worker_id == current.worker_id)
    return query.order_by(ImmunizationRecord.immunization_id.desc()).all()


@router.put("/immunization/{immunization_id}", response_model=ImmunizationRecordOut)
def update_immunization_record(immunization_id: int, payload: ImmunizationRecordUpdate, db: Session = Depends(get_db), current: AshaWorker = Depends(get_current_worker)):
    immunization = db.get(ImmunizationRecord, immunization_id)
    if not immunization:
        raise HTTPException(status_code=404, detail="Immunization record not found")
    _check_beneficiary(db, immunization.beneficiary_id, current)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(immunization, key, value)
    db.commit()
    db.refresh(immunization)
    return immunization

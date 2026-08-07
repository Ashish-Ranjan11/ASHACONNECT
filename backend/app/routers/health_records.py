from datetime import date, datetime
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session

from app.db.mysql import get_db
from app.deps import get_current_worker, visible_worker_ids
from app.models import (
    AshaWorker,
    Beneficiary,
    PregnancyRecord,
    ImmunizationRecord,
)

router = APIRouter(tags=["Health Records"])


def parse_date(value):
    if isinstance(value, date):
        return value

    value = str(value or "").strip()

    if not value:
        return date.today()

    formats = ["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%m/%d/%Y"]

    for fmt in formats:
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            pass

    return date.today()


def normalize_pregnancy_status(value):
    value = str(value or "active").strip().lower()

    mapping = {
        "active": "active",
        "completed": "completed",
        "complete": "completed",
        "high risk": "high_risk",
        "high_risk": "high_risk",
        "high-risk": "high_risk",
    }

    return mapping.get(value, "active")


def normalize_immunization_status(value):
    value = str(value or "scheduled").strip().lower()

    mapping = {
        "scheduled": "scheduled",
        "pending": "scheduled",
        "given": "given",
        "completed": "given",
        "done": "given",
        "missed": "missed",
        "postponed": "postponed",
    }

    return mapping.get(value, "scheduled")


def check_beneficiary_access(db: Session, beneficiary_id: int, current: AshaWorker):
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


def pregnancy_json(item: PregnancyRecord):
    return {
        "pregnancy_id": item.pregnancy_id,
        "id": item.pregnancy_id,
        "beneficiary_id": item.beneficiary_id,
        "registration_date": str(item.registration_date) if item.registration_date else None,
        "lmp_date": str(item.lmp_date) if item.lmp_date else None,
        "expected_delivery_date": str(item.expected_delivery_date) if item.expected_delivery_date else None,
        "hemoglobin_level": item.hemoglobin_level,
        "blood_pressure": item.blood_pressure,
        "weight": item.weight,
        "status": item.status,
        "anc_count": item.anc_count,
        "created_by": item.created_by,
    }


def immunization_json(item: ImmunizationRecord):
    return {
        "immunization_id": item.immunization_id,
        "id": item.immunization_id,
        "beneficiary_id": item.beneficiary_id,
        "vaccine_name": item.vaccine_name,
        "dose_number": item.dose_number,
        "scheduled_date": str(item.scheduled_date) if item.scheduled_date else None,
        "given_date": str(item.given_date) if item.given_date else None,
        "status": item.status,
        "created_by": item.created_by,
    }


@router.get("/api/pregnancy-records")
def list_pregnancy_records(
    db: Session = Depends(get_db),
    current: AshaWorker = Depends(get_current_worker),
):
    worker_ids = visible_worker_ids(db, current)

    records = (
        db.query(PregnancyRecord)
        .join(Beneficiary, PregnancyRecord.beneficiary_id == Beneficiary.beneficiary_id)
        .filter(Beneficiary.asha_worker_id.in_(worker_ids))
        .order_by(PregnancyRecord.pregnancy_id.desc())
        .all()
    )

    return [pregnancy_json(item) for item in records]


@router.post("/api/pregnancy-records")
def create_pregnancy_record(
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    current: AshaWorker = Depends(get_current_worker),
):
    beneficiary_id = payload.get("beneficiary_id")

    if not beneficiary_id:
        raise HTTPException(status_code=400, detail="Select a beneficiary first")

    check_beneficiary_access(db, int(beneficiary_id), current)

    record = PregnancyRecord(
        beneficiary_id=int(beneficiary_id),
        registration_date=parse_date(payload.get("registration_date") or payload.get("date")),
        lmp_date=parse_date(payload.get("lmp_date")),
        expected_delivery_date=parse_date(
            payload.get("expected_delivery_date")
            or payload.get("edd")
            or payload.get("delivery_date")
        ),
        hemoglobin_level=float(payload.get("hemoglobin_level") or payload.get("hb") or 0),
        blood_pressure=str(payload.get("blood_pressure") or payload.get("bp") or ""),
        weight=float(payload.get("weight") or 0),
        status=normalize_pregnancy_status(payload.get("status")),
        anc_count=int(payload.get("anc_count") or 0),
        created_by=current.worker_id,
    )

    db.add(record)
    db.flush()
    db.commit()

    return "Pregnancy record added successfully"


@router.get("/api/immunization-records")
def list_immunization_records(
    db: Session = Depends(get_db),
    current: AshaWorker = Depends(get_current_worker),
):
    worker_ids = visible_worker_ids(db, current)

    records = (
        db.query(ImmunizationRecord)
        .join(Beneficiary, ImmunizationRecord.beneficiary_id == Beneficiary.beneficiary_id)
        .filter(Beneficiary.asha_worker_id.in_(worker_ids))
        .order_by(ImmunizationRecord.immunization_id.desc())
        .all()
    )

    return [immunization_json(item) for item in records]


@router.post("/api/immunization-records")
def create_immunization_record(
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    current: AshaWorker = Depends(get_current_worker),
):
    beneficiary_id = payload.get("beneficiary_id")

    if not beneficiary_id:
        raise HTTPException(status_code=400, detail="Select a beneficiary first")

    check_beneficiary_access(db, int(beneficiary_id), current)

    record = ImmunizationRecord(
        beneficiary_id=int(beneficiary_id),
        vaccine_name=str(payload.get("vaccine_name") or payload.get("vaccine") or "Routine Vaccine"),
        dose_number=int(payload.get("dose_number") or payload.get("dose") or 1),
        scheduled_date=parse_date(payload.get("scheduled_date") or payload.get("date")),
        given_date=parse_date(payload.get("given_date")) if payload.get("given_date") else None,
        status=normalize_immunization_status(payload.get("status")),
        created_by=current.worker_id,
    )

    db.add(record)
    db.flush()
    db.commit()

    return "Immunization record added successfully"

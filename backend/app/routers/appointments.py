from datetime import date, time, datetime
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session

from app.db.mysql import get_db
from app.deps import get_current_worker, visible_worker_ids
from app.models import AshaWorker, Appointment, Beneficiary

router = APIRouter(prefix="/api/appointments", tags=["Appointments"])


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


def parse_time(value):
    if isinstance(value, time):
        return value

    value = str(value or "").strip()

    if not value:
        return time(10, 0)

    formats = ["%H:%M:%S", "%H:%M", "%I:%M %p", "%I:%M:%S %p"]

    for fmt in formats:
        try:
            return datetime.strptime(value, fmt).time()
        except ValueError:
            pass

    return time(10, 0)


def normalize_status(value):
    value = str(value or "scheduled").strip().lower()
    mapping = {
        "scheduled": "scheduled",
        "complete": "completed",
        "completed": "completed",
        "cancelled": "cancelled",
        "canceled": "cancelled",
        "missed": "missed",
    }
    return mapping.get(value, "scheduled")


def serialize_appointment(item: Appointment, beneficiary_name="N/A"):
    return {
        "appointment_id": item.appointment_id,
        "id": item.appointment_id,
        "beneficiary_id": item.beneficiary_id,
        "beneficiary_name": beneficiary_name,
        "name": beneficiary_name,
        "title": item.appointment_type,
        "appointment_type": item.appointment_type,
        "appointment_date": str(item.appointment_date),
        "date": str(item.appointment_date),
        "appointment_time": str(item.appointment_time),
        "time": str(item.appointment_time),
        "location": item.notes or "",
        "notes": item.notes or "",
        "status": item.status,
        "created_by": item.created_by,
    }


def ensure_beneficiary_access(db: Session, beneficiary_id: int, current: AshaWorker):
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
def list_appointments(
    date: str | None = None,
    db: Session = Depends(get_db),
    current: AshaWorker = Depends(get_current_worker),
):
    worker_ids = visible_worker_ids(db, current)

    query = (
        db.query(Appointment)
        .join(
            Beneficiary,
            Appointment.beneficiary_id == Beneficiary.beneficiary_id
        )
        .filter(
            Beneficiary.asha_worker_id.in_(worker_ids)
        )
    )

    if date:
        query = query.filter(
            Appointment.appointment_date == parse_date(date)
        )

    appointments = (
        query
        .order_by(Appointment.appointment_date.asc())
        .all()
    )

    result = []

    for item in appointments:
        beneficiary = db.get(Beneficiary, item.beneficiary_id)
        beneficiary_name = beneficiary.full_name if beneficiary else "N/A"
        result.append(serialize_appointment(item, beneficiary_name))

    return result


@router.post("")
def create_appointment(
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    current: AshaWorker = Depends(get_current_worker),
):
    beneficiary_id = payload.get("beneficiary_id")

    if not beneficiary_id:
        raise HTTPException(status_code=400, detail="Select a beneficiary first")

    beneficiary = ensure_beneficiary_access(db, int(beneficiary_id), current)

    appointment_type = (
        payload.get("appointment_type")
        or payload.get("title")
        or payload.get("type")
        or "Follow-up Visit"
    )

    notes = payload.get("notes") or payload.get("location") or ""

    appointment = Appointment(
        beneficiary_id=int(beneficiary_id),
        appointment_date=parse_date(payload.get("appointment_date") or payload.get("date")),
        appointment_time=parse_time(payload.get("appointment_time") or payload.get("time")),
        appointment_type=str(appointment_type).strip(),
        status=normalize_status(payload.get("status")),
        notes=str(notes).strip(),
        created_by=current.worker_id,
    )

    db.add(appointment)
    db.flush()
    db.commit()

    return "Appointment scheduled successfully"

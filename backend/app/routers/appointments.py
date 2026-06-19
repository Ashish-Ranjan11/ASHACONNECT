from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.mysql import get_db
from app.deps import get_current_worker
from app.models import Appointment, AshaWorker, Beneficiary
from app.schemas import AppointmentCreate, AppointmentOut

router = APIRouter(prefix="/api/appointments", tags=["Appointments"])


def _check_beneficiary(db: Session, beneficiary_id: int, current: AshaWorker):
    beneficiary = db.get(Beneficiary, beneficiary_id)
    if not beneficiary:
        raise HTTPException(status_code=404, detail="Beneficiary not found")
    if current.role == "asha" and beneficiary.asha_worker_id != current.worker_id:
        raise HTTPException(status_code=403, detail="Not allowed")
    return beneficiary


@router.get("", response_model=list[AppointmentOut])
def list_appointments(db: Session = Depends(get_db), current: AshaWorker = Depends(get_current_worker)):
    query = db.query(Appointment).join(Beneficiary)
    if current.role == "asha":
        query = query.filter(Beneficiary.asha_worker_id == current.worker_id)
    return query.order_by(Appointment.appointment_date.asc()).all()


@router.post("", response_model=AppointmentOut)
def create_appointment(payload: AppointmentCreate, db: Session = Depends(get_db), current: AshaWorker = Depends(get_current_worker)):
    _check_beneficiary(db, payload.beneficiary_id, current)
    appointment = Appointment(**payload.model_dump(), created_by=current.worker_id)
    db.add(appointment)
    db.commit()
    db.refresh(appointment)
    return appointment

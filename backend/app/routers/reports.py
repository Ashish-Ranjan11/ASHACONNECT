from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.mysql import get_db
from app.deps import get_current_worker
from app.models import Appointment, AshaWorker, Beneficiary, Event, ImmunizationRecord, MonthlyReport, PregnancyRecord
from app.schemas import MonthlyReportCreate, MonthlyReportOut

router = APIRouter(prefix="/api/reports", tags=["Reports"])


@router.get("", response_model=list[MonthlyReportOut])
def list_reports(db: Session = Depends(get_db), current: AshaWorker = Depends(get_current_worker)):
    query = db.query(MonthlyReport)
    if current.role == "asha":
        query = query.filter(MonthlyReport.generated_by == current.worker_id)
    return query.order_by(MonthlyReport.report_id.desc()).all()


@router.post("/generate", response_model=MonthlyReportOut)
def generate_report(payload: MonthlyReportCreate, db: Session = Depends(get_db), current: AshaWorker = Depends(get_current_worker)):
    # For MVP: aggregate worker-level totals. Later, filter by exact month dates.
    total_patients = db.query(Beneficiary).filter(Beneficiary.asha_worker_id == current.worker_id).count()
    total_pregnancies = db.query(PregnancyRecord).join(Beneficiary).filter(Beneficiary.asha_worker_id == current.worker_id).count()
    total_immunizations = db.query(ImmunizationRecord).join(Beneficiary).filter(Beneficiary.asha_worker_id == current.worker_id).count()
    total_appointments = db.query(Appointment).join(Beneficiary).filter(Beneficiary.asha_worker_id == current.worker_id).count()
    total_events = db.query(Event).filter(Event.organizer_id == current.worker_id).count()

    report = MonthlyReport(
        month=payload.month,
        year=payload.year,
        total_patients=total_patients,
        total_pregnancies=total_pregnancies,
        total_immunizations=total_immunizations,
        total_appointments=total_appointments,
        total_events=total_events,
        generated_by=current.worker_id,
        phc_id=current.phc_id,
        status=payload.status,
        notes=payload.notes,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report

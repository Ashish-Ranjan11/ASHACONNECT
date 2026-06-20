from datetime import date, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.mysql import get_db
from app.deps import get_current_worker, visible_worker_ids, scoped_beneficiary_query
from app.models import (
    Appointment,
    AshaWorker,
    Beneficiary,
    Event,
    ImmunizationRecord,
    MonthlyReport,
    Notice,
    PregnancyRecord,
    PrimaryHealthCentre,
    SOSAlert,
)

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


def _iso(value):
    if value is None:
        return None
    return value.isoformat() if hasattr(value, "isoformat") else str(value)


@router.get("/summary")
def dashboard_summary(
    db: Session = Depends(get_db),
    current: AshaWorker = Depends(get_current_worker),
):
    today = date.today()
    next_30 = today + timedelta(days=30)

    worker_ids = visible_worker_ids(db, current)

    beneficiaries = scoped_beneficiary_query(db, current).all()
    beneficiary_ids = [b.beneficiary_id for b in beneficiaries]
    beneficiary_map = {b.beneficiary_id: b.full_name for b in beneficiaries}

    if not beneficiary_ids:
        beneficiary_ids = [0]

    pregnancies = db.query(PregnancyRecord).filter(PregnancyRecord.beneficiary_id.in_(beneficiary_ids))
    immunizations = db.query(ImmunizationRecord).filter(ImmunizationRecord.beneficiary_id.in_(beneficiary_ids))
    appointments = db.query(Appointment).filter(Appointment.beneficiary_id.in_(beneficiary_ids))
    notices = db.query(Notice).filter(Notice.beneficiary_id.in_(beneficiary_ids))
    events = db.query(Event).filter(Event.organizer_id.in_(worker_ids))
    sos = db.query(SOSAlert).filter(SOSAlert.worker_id.in_(worker_ids))
    reports = db.query(MonthlyReport).filter(MonthlyReport.generated_by.in_(worker_ids))

    upcoming_appointments = appointments.filter(
        Appointment.appointment_date >= today,
        Appointment.status == "scheduled",
    ).count()

    overdue_appointments = appointments.filter(
        Appointment.appointment_date < today,
        Appointment.status == "scheduled",
    ).count()

    missed_immunizations = immunizations.filter(ImmunizationRecord.status == "missed").count()

    due_immunizations = immunizations.filter(
        ImmunizationRecord.status == "scheduled",
        ImmunizationRecord.scheduled_date <= next_30,
    ).count()

    high_risk = pregnancies.filter(PregnancyRecord.status == "high_risk").count()

    low_hb = pregnancies.filter(
        PregnancyRecord.hemoglobin_level != None,
        PregnancyRecord.hemoglobin_level < 11,
    ).count()

    active_sos = sos.filter(SOSAlert.status == "active").count()

    cards = {
        "asha_workers": len(worker_ids),
        "phcs": db.query(PrimaryHealthCentre).count() if current.role == "supervisor" else 1,
        "beneficiaries": len(beneficiaries),
        "pregnancies": pregnancies.count(),
        "immunizations": immunizations.count(),
        "appointments": appointments.count(),
        "upcoming_appointments": upcoming_appointments,
        "events": events.count(),
        "notices_sent": notices.filter(Notice.status == "sent").count(),
        "monthly_reports": reports.count(),
        "high_risk_pregnancies": high_risk,
        "missed_immunizations": missed_immunizations,
        "due_immunizations": due_immunizations,
        "active_sos_alerts": active_sos,
    }

    category_breakdown = {
        "pregnant": sum(1 for b in beneficiaries if b.category == "pregnant"),
        "child": sum(1 for b in beneficiaries if b.category == "child"),
        "elderly": sum(1 for b in beneficiaries if b.category == "elderly"),
        "general": sum(1 for b in beneficiaries if b.category == "general"),
    }

    upcoming_appts = appointments.filter(
        Appointment.appointment_date >= today
    ).order_by(Appointment.appointment_date.asc()).limit(6).all()

    upcoming_imms = immunizations.filter(
        ImmunizationRecord.scheduled_date >= today
    ).order_by(ImmunizationRecord.scheduled_date.asc()).limit(6).all()

    upcoming_events = events.filter(
        Event.event_date >= today
    ).order_by(Event.event_date.asc()).limit(6).all()

    alerts = []

    if active_sos:
        alerts.append({
            "level": "critical",
            "title": "Active SOS alert",
            "message": f"{active_sos} emergency alert is active. Verify location and escalate immediately.",
        })

    if high_risk:
        alerts.append({
            "level": "high",
            "title": "High-risk pregnancy tracking",
            "message": f"{high_risk} high-risk pregnancy record needs close ANC monitoring.",
        })

    if low_hb:
        alerts.append({
            "level": "medium",
            "title": "Low hemoglobin cases",
            "message": f"{low_hb} pregnancy record has Hb below 11 g/dL. Plan IFA counselling and follow-up.",
        })

    if missed_immunizations:
        alerts.append({
            "level": "medium",
            "title": "Missed immunizations",
            "message": f"{missed_immunizations} immunization record is marked missed. Send reminder and reschedule.",
        })

    if overdue_appointments:
        alerts.append({
            "level": "medium",
            "title": "Overdue appointments",
            "message": f"{overdue_appointments} scheduled appointment crossed due date.",
        })

    if not alerts:
        alerts.append({
            "level": "normal",
            "title": "Workflow stable",
            "message": "No critical alerts. Continue planned beneficiary follow-ups.",
        })

    role_title = {
        "asha": "ASHA Worker Dashboard",
        "phc_admin": "PHC Admin Dashboard",
        "supervisor": "Supervisor Dashboard",
    }.get(current.role, "Dashboard")

    return {
        "worker": {
            "id": current.worker_id,
            "name": current.name,
            "role": current.role,
            "role_title": role_title,
            "village": current.village,
            "phone_no": current.phone_no,
            "email": current.email,
            "sos_id": current.sos_id,
            "phc": current.phc.name if current.phc else None,
        },
        "cards": cards,
        "category_breakdown": category_breakdown,
        "clinical_risk": {
            "high_risk_pregnancies": high_risk,
            "low_hb_cases": low_hb,
            "missed_immunizations": missed_immunizations,
            "overdue_appointments": overdue_appointments,
            "active_sos_alerts": active_sos,
        },
        "care_pipeline": [
            {
                "label": "Register beneficiary",
                "value": len(beneficiaries),
                "target": max(len(beneficiaries), 10),
                "status": "live",
            },
            {
                "label": "ANC / pregnancy monitoring",
                "value": pregnancies.count(),
                "target": max(pregnancies.count(), 6),
                "status": "clinical",
            },
            {
                "label": "Immunization tracking",
                "value": immunizations.count(),
                "target": max(immunizations.count(), 8),
                "status": "child health",
            },
            {
                "label": "Appointments & follow-ups",
                "value": upcoming_appointments,
                "target": max(upcoming_appointments, 5),
                "status": "scheduled",
            },
            {
                "label": "Reports submitted",
                "value": reports.filter(MonthlyReport.status.in_(["submitted", "approved"])).count(),
                "target": max(reports.count(), 1),
                "status": "PHC review",
            },
        ],
        "upcoming": {
            "appointments": [
                {
                    "id": a.appointment_id,
                    "beneficiary": beneficiary_map.get(a.beneficiary_id, f"Beneficiary #{a.beneficiary_id}"),
                    "type": a.appointment_type,
                    "date": _iso(a.appointment_date),
                    "time": _iso(a.appointment_time),
                    "status": a.status,
                    "notes": a.notes,
                }
                for a in upcoming_appts
            ],
            "immunizations": [
                {
                    "id": i.immunization_id,
                    "beneficiary": beneficiary_map.get(i.beneficiary_id, f"Beneficiary #{i.beneficiary_id}"),
                    "vaccine": i.vaccine_name,
                    "dose": i.dose_number,
                    "date": _iso(i.scheduled_date),
                    "status": i.status,
                }
                for i in upcoming_imms
            ],
            "events": [
                {
                    "id": e.event_id,
                    "name": e.event_name,
                    "type": e.event_type,
                    "date": _iso(e.event_date),
                    "time": _iso(e.event_time),
                    "location": e.location,
                    "status": e.status,
                }
                for e in upcoming_events
            ],
        },
        "alerts": alerts,
        "uml_modules": [
            {"module": "Access Control", "items": ["Multi-role login", "JWT sessions", "Role-based dashboard"]},
            {"module": "Beneficiary Services", "items": ["Register beneficiary", "Update profile", "ASHA mapping"]},
            {"module": "Clinical Records", "items": ["Pregnancy records", "Immunization records", "Risk flags"]},
            {"module": "Outreach & Safety", "items": ["Events", "Notices", "Monthly reports", "SOS"]},
        ],
        "architecture_layers": [
            {"name": "React UI", "detail": "Role-aware dashboard for ASHA, PHC Admin, and Supervisor"},
            {"name": "FastAPI Backend", "detail": "Authentication, CRUD, reporting, alerts and role-based data access"},
            {"name": "SQLite / MySQL DB", "detail": "Relational storage for PHC, workers, beneficiaries and clinical records"},
            {"name": "Notification Gateway", "detail": "SMS / push reminder simulation for beneficiaries"},
            {"name": "Emergency Services", "detail": "SOS escalation with worker identity and location"},
        ],
    }

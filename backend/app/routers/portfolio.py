from datetime import date, datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.mysql import get_db
from app.deps import get_current_worker, visible_worker_ids
from app.models import (
    AshaWorker,
    Beneficiary,
    PregnancyRecord,
    ImmunizationRecord,
    Appointment,
    Notice,
)

router = APIRouter(prefix="/api/beneficiaries", tags=["Beneficiary Portfolio"])


def safe_date(value):
    if value is None:
        return None
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return str(value)


def safe_time(value):
    if value is None:
        return None
    return str(value)


def beneficiary_json(item):
    return {
        "beneficiary_id": item.beneficiary_id,
        "id": item.beneficiary_id,
        "name": item.full_name,
        "full_name": item.full_name,
        "age": item.age,
        "gender": item.gender,
        "category": item.category,
        "phone": item.contact_no or "",
        "contact_no": item.contact_no or "",
        "address": item.address or "",
        "village": item.address or "",
        "asha_worker_id": item.asha_worker_id,
        "is_active": item.is_active,
    }


def build_risk(beneficiary, pregnancies, immunizations, appointments):
    score = 0
    reasons = []

    missed_appointments = len([a for a in appointments if str(a.status).lower() == "missed"])
    pending_immunizations = len([i for i in immunizations if str(i.status).lower() in ["scheduled", "pending", "postponed"]])
    missed_immunizations = len([i for i in immunizations if str(i.status).lower() == "missed"])
    active_pregnancies = len([p for p in pregnancies if str(p.status).lower() in ["active", "high_risk"]])
    high_risk_pregnancies = len([p for p in pregnancies if str(p.status).lower() == "high_risk"])

    if high_risk_pregnancies:
        score += 40
        reasons.append("High-risk pregnancy record exists.")

    if active_pregnancies:
        score += 15
        reasons.append("Active pregnancy follow-up is required.")

    if missed_appointments:
        score += missed_appointments * 15
        reasons.append(f"{missed_appointments} missed appointment(s).")

    if missed_immunizations:
        score += missed_immunizations * 20
        reasons.append(f"{missed_immunizations} missed immunization record(s).")

    if pending_immunizations:
        score += 10
        reasons.append(f"{pending_immunizations} pending immunization task(s).")

    if beneficiary.category == "pregnant" and not pregnancies:
        score += 20
        reasons.append("Beneficiary is marked pregnant but pregnancy record is not added.")

    score = min(score, 100)

    if score >= 60:
        level = "High Risk"
    elif score >= 25:
        level = "Medium Risk"
    else:
        level = "Low Risk"

    if not reasons:
        reasons.append("No major risk indicators found from current records.")

    return {
        "level": level,
        "score": score,
        "reasons": reasons,
        "missed_appointments": missed_appointments,
        "pending_immunizations": pending_immunizations,
        "active_pregnancies": active_pregnancies,
    }


def build_timeline(pregnancies, immunizations, appointments, notices):
    timeline = []

    for p in pregnancies:
        timeline.append({
            "date": safe_date(p.registration_date),
            "type": "Pregnancy",
            "title": f"Pregnancy record: {p.status}",
            "detail": f"ANC Count: {p.anc_count or 0}, Hb: {p.hemoglobin_level or 'N/A'}",
            "status": p.status,
        })

    for i in immunizations:
        timeline.append({
            "date": safe_date(i.scheduled_date),
            "type": "Immunization",
            "title": f"{i.vaccine_name} Dose {i.dose_number}",
            "detail": f"Status: {i.status}",
            "status": i.status,
        })

    for a in appointments:
        timeline.append({
            "date": safe_date(a.appointment_date),
            "type": "Appointment",
            "title": a.appointment_type,
            "detail": f"{safe_time(a.appointment_time) or ''} {a.notes or ''}".strip(),
            "status": a.status,
        })

    for n in notices:
        timeline.append({
            "date": safe_date(n.notice_date),
            "type": "Notice",
            "title": "Notice sent",
            "detail": n.message,
            "status": n.status,
        })

    timeline.sort(key=lambda x: x.get("date") or "", reverse=True)
    return timeline


@router.get("/{beneficiary_id}/profile")
def get_beneficiary_profile(
    beneficiary_id: int,
    db: Session = Depends(get_db),
    current: AshaWorker = Depends(get_current_worker),
):
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

    pregnancies = (
        db.query(PregnancyRecord)
        .filter(PregnancyRecord.beneficiary_id == beneficiary_id)
        .order_by(PregnancyRecord.pregnancy_id.desc())
        .all()
    )

    immunizations = (
        db.query(ImmunizationRecord)
        .filter(ImmunizationRecord.beneficiary_id == beneficiary_id)
        .order_by(ImmunizationRecord.immunization_id.desc())
        .all()
    )

    appointments = (
        db.query(Appointment)
        .filter(Appointment.beneficiary_id == beneficiary_id)
        .order_by(Appointment.appointment_id.desc())
        .all()
    )

    notices = (
        db.query(Notice)
        .filter(Notice.beneficiary_id == beneficiary_id)
        .order_by(Notice.notice_id.desc())
        .all()
    )

    asha_worker = db.get(AshaWorker, beneficiary.asha_worker_id)

    risk = build_risk(beneficiary, pregnancies, immunizations, appointments)

    next_actions = []

    if risk["level"] == "High Risk":
        next_actions.append("Arrange PHC follow-up or supervisor review.")

    if risk["active_pregnancies"]:
        next_actions.append("Schedule next ANC/PNC home visit.")

    if risk["pending_immunizations"]:
        next_actions.append("Send immunization reminder notice.")

    if risk["missed_appointments"]:
        next_actions.append("Call beneficiary and reschedule missed appointment.")

    if not next_actions:
        next_actions.append("Continue regular monthly follow-up.")

    return {
        "beneficiary": beneficiary_json(beneficiary),
        "asha_worker": {
            "worker_id": asha_worker.worker_id if asha_worker else None,
            "name": asha_worker.name if asha_worker else "N/A",
            "phone_no": asha_worker.phone_no if asha_worker else "",
            "village": asha_worker.village if asha_worker else "",
            "role": asha_worker.role if asha_worker else "",
            "sos_id": asha_worker.sos_id if asha_worker else "",
        },
        "risk": risk,
        "next_actions": next_actions,
        "stats": {
            "pregnancy_records": len(pregnancies),
            "immunization_records": len(immunizations),
            "appointments": len(appointments),
            "notices": len(notices),
        },
        "pregnancy_records": [
            {
                "pregnancy_id": p.pregnancy_id,
                "status": p.status,
                "registration_date": safe_date(p.registration_date),
                "expected_delivery_date": safe_date(p.expected_delivery_date),
                "anc_count": p.anc_count,
                "hemoglobin_level": p.hemoglobin_level,
            }
            for p in pregnancies
        ],
        "immunization_records": [
            {
                "immunization_id": i.immunization_id,
                "vaccine_name": i.vaccine_name,
                "dose_number": i.dose_number,
                "scheduled_date": safe_date(i.scheduled_date),
                "given_date": safe_date(i.given_date),
                "status": i.status,
            }
            for i in immunizations
        ],
        "appointments": [
            {
                "appointment_id": a.appointment_id,
                "appointment_type": a.appointment_type,
                "appointment_date": safe_date(a.appointment_date),
                "appointment_time": safe_time(a.appointment_time),
                "status": a.status,
                "notes": a.notes or "",
            }
            for a in appointments
        ],
        "notices": [
            {
                "notice_id": n.notice_id,
                "message": n.message,
                "notice_date": safe_date(n.notice_date),
                "status": n.status,
                "delivery_method": n.delivery_method,
            }
            for n in notices
        ],
        "timeline": build_timeline(pregnancies, immunizations, appointments, notices),
    }

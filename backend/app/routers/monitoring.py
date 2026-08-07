from datetime import date, datetime
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.mysql import get_db
from app.deps import get_current_worker, visible_worker_ids
from app.models import (
    AshaWorker,
    Beneficiary,
    Appointment,
    PregnancyRecord,
    ImmunizationRecord,
    SOSAlert,
)

router = APIRouter(prefix="/api/monitoring", tags=["Monitoring"])


def safe_date(value):
    if value is None:
        return None

    if isinstance(value, (date, datetime)):
        return value.isoformat()

    return str(value)


def calculate_risk(beneficiary, pregnancies, immunizations, appointments):
    score = 0
    reasons = []

    missed_appointments = len([
        item for item in appointments
        if str(item.status or "").lower() == "missed"
    ])

    pending_immunizations = len([
        item for item in immunizations
        if str(item.status or "").lower() in ["scheduled", "pending", "postponed"]
    ])

    missed_immunizations = len([
        item for item in immunizations
        if str(item.status or "").lower() == "missed"
    ])

    active_pregnancies = len([
        item for item in pregnancies
        if str(item.status or "").lower() in ["active", "high_risk"]
    ])

    high_risk_pregnancies = len([
        item for item in pregnancies
        if str(item.status or "").lower() == "high_risk"
    ])

    if high_risk_pregnancies:
        score += 40
        reasons.append("High-risk pregnancy record exists.")

    if active_pregnancies:
        score += 15
        reasons.append("Active pregnancy follow-up required.")

    if missed_appointments:
        score += missed_appointments * 15
        reasons.append(f"{missed_appointments} missed appointment(s).")

    if missed_immunizations:
        score += missed_immunizations * 20
        reasons.append(f"{missed_immunizations} missed immunization(s).")

    if pending_immunizations:
        score += 10
        reasons.append(f"{pending_immunizations} pending immunization task(s).")

    if str(beneficiary.category or "").lower() == "pregnant" and not pregnancies:
        score += 20
        reasons.append("Marked pregnant but pregnancy record is missing.")

    score = min(score, 100)

    if score >= 60:
        level = "High Risk"
    elif score >= 25:
        level = "Medium Risk"
    else:
        level = "Low Risk"

    if not reasons:
        reasons.append("No major risk indicator found.")

    return {
        "score": score,
        "level": level,
        "reasons": reasons,
        "missed_appointments": missed_appointments,
        "pending_immunizations": pending_immunizations,
        "active_pregnancies": active_pregnancies,
    }


def beneficiary_card(beneficiary, risk, worker_name="N/A"):
    return {
        "beneficiary_id": beneficiary.beneficiary_id,
        "name": beneficiary.full_name,
        "age": beneficiary.age,
        "gender": beneficiary.gender,
        "category": beneficiary.category,
        "contact_no": beneficiary.contact_no or "",
        "village": beneficiary.address or "N/A",
        "asha_worker_id": beneficiary.asha_worker_id,
        "asha_worker_name": worker_name,
        "risk": risk,
    }


@router.get("/overview")
def monitoring_overview(
    db: Session = Depends(get_db),
    current: AshaWorker = Depends(get_current_worker),
):
    worker_ids = visible_worker_ids(db, current)

    workers = (
        db.query(AshaWorker)
        .filter(AshaWorker.worker_id.in_(worker_ids))
        .all()
    )

    worker_map = {worker.worker_id: worker for worker in workers}

    beneficiaries = (
        db.query(Beneficiary)
        .filter(Beneficiary.asha_worker_id.in_(worker_ids))
        .all()
    )

    beneficiary_ids = [item.beneficiary_id for item in beneficiaries]

    appointments = []
    pregnancies = []
    immunizations = []
    sos_alerts = []

    if beneficiary_ids:
        appointments = (
            db.query(Appointment)
            .filter(Appointment.beneficiary_id.in_(beneficiary_ids))
            .all()
        )

        pregnancies = (
            db.query(PregnancyRecord)
            .filter(PregnancyRecord.beneficiary_id.in_(beneficiary_ids))
            .all()
        )

        immunizations = (
            db.query(ImmunizationRecord)
            .filter(ImmunizationRecord.beneficiary_id.in_(beneficiary_ids))
            .all()
        )

    sos_alerts = (
        db.query(SOSAlert)
        .filter(SOSAlert.worker_id.in_(worker_ids))
        .all()
    )

    appointment_by_beneficiary = {}
    pregnancy_by_beneficiary = {}
    immunization_by_beneficiary = {}

    for item in appointments:
        appointment_by_beneficiary.setdefault(item.beneficiary_id, []).append(item)

    for item in pregnancies:
        pregnancy_by_beneficiary.setdefault(item.beneficiary_id, []).append(item)

    for item in immunizations:
        immunization_by_beneficiary.setdefault(item.beneficiary_id, []).append(item)

    risk_cases = []
    high_risk_cases = []
    medium_risk_cases = []
    smart_alerts = []

    total_missed_appointments = 0
    total_pending_immunizations = 0
    total_active_pregnancies = 0

    for beneficiary in beneficiaries:
        b_appointments = appointment_by_beneficiary.get(beneficiary.beneficiary_id, [])
        b_pregnancies = pregnancy_by_beneficiary.get(beneficiary.beneficiary_id, [])
        b_immunizations = immunization_by_beneficiary.get(beneficiary.beneficiary_id, [])

        risk = calculate_risk(
            beneficiary,
            b_pregnancies,
            b_immunizations,
            b_appointments,
        )

        worker = worker_map.get(beneficiary.asha_worker_id)
        worker_name = worker.name if worker else "N/A"

        card = beneficiary_card(beneficiary, risk, worker_name)

        risk_cases.append(card)

        total_missed_appointments += risk["missed_appointments"]
        total_pending_immunizations += risk["pending_immunizations"]
        total_active_pregnancies += risk["active_pregnancies"]

        if risk["level"] == "High Risk":
            high_risk_cases.append(card)
            smart_alerts.append({
                "type": "High Risk",
                "message": f"{beneficiary.full_name} needs urgent PHC/supervisor follow-up.",
                "beneficiary_id": beneficiary.beneficiary_id,
                "priority": "high",
            })

        elif risk["level"] == "Medium Risk":
            medium_risk_cases.append(card)

        if risk["missed_appointments"]:
            smart_alerts.append({
                "type": "Missed Follow-up",
                "message": f"{beneficiary.full_name} has {risk['missed_appointments']} missed appointment(s).",
                "beneficiary_id": beneficiary.beneficiary_id,
                "priority": "medium",
            })

        if risk["pending_immunizations"]:
            smart_alerts.append({
                "type": "Immunization Pending",
                "message": f"{beneficiary.full_name} has pending immunization work.",
                "beneficiary_id": beneficiary.beneficiary_id,
                "priority": "medium",
            })

    village_summary = {}

    for beneficiary in beneficiaries:
        village = beneficiary.address or "Unassigned"

        if village not in village_summary:
            village_summary[village] = {
                "village": village,
                "beneficiaries": 0,
                "pregnant": 0,
                "children": 0,
                "elderly": 0,
                "high_risk": 0,
                "medium_risk": 0,
            }

        village_summary[village]["beneficiaries"] += 1

        category = str(beneficiary.category or "").lower()

        if category == "pregnant":
            village_summary[village]["pregnant"] += 1
        elif category == "child":
            village_summary[village]["children"] += 1
        elif category == "elderly":
            village_summary[village]["elderly"] += 1

    for card in high_risk_cases:
        village = card["village"] or "Unassigned"
        if village in village_summary:
            village_summary[village]["high_risk"] += 1

    for card in medium_risk_cases:
        village = card["village"] or "Unassigned"
        if village in village_summary:
            village_summary[village]["medium_risk"] += 1

    worker_performance = []

    for worker in workers:
        worker_beneficiaries = [
            item for item in beneficiaries
            if item.asha_worker_id == worker.worker_id
        ]

        worker_beneficiary_ids = [item.beneficiary_id for item in worker_beneficiaries]

        worker_appointments = [
            item for item in appointments
            if item.beneficiary_id in worker_beneficiary_ids
        ]

        worker_missed = len([
            item for item in worker_appointments
            if str(item.status or "").lower() == "missed"
        ])

        worker_sos = len([
            item for item in sos_alerts
            if item.worker_id == worker.worker_id
        ])

        worker_high_risk = len([
            item for item in high_risk_cases
            if item["asha_worker_id"] == worker.worker_id
        ])

        worker_performance.append({
            "worker_id": worker.worker_id,
            "name": worker.name,
            "role": worker.role,
            "village": worker.village or "N/A",
            "beneficiaries": len(worker_beneficiaries),
            "appointments": len(worker_appointments),
            "missed_appointments": worker_missed,
            "sos_alerts": worker_sos,
            "high_risk_cases": worker_high_risk,
        })

    risk_cases.sort(key=lambda item: item["risk"]["score"], reverse=True)
    high_risk_cases.sort(key=lambda item: item["risk"]["score"], reverse=True)
    medium_risk_cases.sort(key=lambda item: item["risk"]["score"], reverse=True)

    return {
        "current_user": {
            "worker_id": current.worker_id,
            "name": current.name,
            "role": current.role,
            "village": current.village,
        },
        "summary": {
            "asha_workers": len(workers),
            "beneficiaries": len(beneficiaries),
            "high_risk": len(high_risk_cases),
            "medium_risk": len(medium_risk_cases),
            "missed_appointments": total_missed_appointments,
            "pending_immunizations": total_pending_immunizations,
            "active_pregnancies": total_active_pregnancies,
            "sos_alerts": len(sos_alerts),
        },
        "high_risk_cases": high_risk_cases,
        "medium_risk_cases": medium_risk_cases,
        "all_risk_cases": risk_cases,
        "village_summary": list(village_summary.values()),
        "worker_performance": worker_performance,
        "smart_alerts": smart_alerts[:15],
    }

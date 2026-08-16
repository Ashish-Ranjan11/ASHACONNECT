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

router = APIRouter(prefix="/api/families", tags=["Family Portfolio"])


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


def member_json(member):
    return {
        "beneficiary_id": member.beneficiary_id,
        "id": member.beneficiary_id,
        "name": member.full_name,
        "full_name": member.full_name,
        "age": member.age,
        "gender": member.gender,
        "category": member.category,
        "contact_no": member.contact_no or "",
        "address": member.address or "",
        "asha_worker_id": member.asha_worker_id,
        "is_active": member.is_active,
    }


def calculate_member_risk(member, pregnancies, immunizations, appointments):
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

    category = str(member.category or "").lower()

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

    if category == "pregnant" and not pregnancies:
        score += 20
        reasons.append("Marked pregnant but pregnancy record is missing.")

    if category == "elderly":
        score += 5
        reasons.append("Elderly member needs regular follow-up.")

    if category == "child" and not immunizations:
        score += 10
        reasons.append("Child has no immunization record yet.")

    score = min(score, 100)

    if score >= 60:
        level = "High Risk"
    elif score >= 25:
        level = "Medium Risk"
    else:
        level = "Low Risk"

    if not reasons:
        reasons.append("No major risk indicators found.")

    return {
        "level": level,
        "score": score,
        "reasons": reasons,
        "missed_appointments": missed_appointments,
        "pending_immunizations": pending_immunizations,
        "active_pregnancies": active_pregnancies,
    }


def build_family_risk(member_risks):
    if not member_risks:
        return {
            "level": "Low Risk",
            "score": 0,
            "reasons": ["No members found in this family."],
        }

    highest_score = max(item["score"] for item in member_risks)

    high_count = len([item for item in member_risks if item["level"] == "High Risk"])
    medium_count = len([item for item in member_risks if item["level"] == "Medium Risk"])

    if high_count:
        level = "High Risk"
    elif medium_count:
        level = "Medium Risk"
    else:
        level = "Low Risk"

    reasons = []

    if high_count:
        reasons.append(f"{high_count} high-risk family member(s).")

    if medium_count:
        reasons.append(f"{medium_count} medium-risk family member(s).")

    if not reasons:
        reasons.append("Family is currently low risk based on available records.")

    return {
        "level": level,
        "score": highest_score,
        "reasons": reasons,
        "high_risk_members": high_count,
        "medium_risk_members": medium_count,
    }


def pregnancy_json(item):
    return {
        "pregnancy_id": item.pregnancy_id,
        "beneficiary_id": item.beneficiary_id,
        "registration_date": safe_date(item.registration_date),
        "expected_delivery_date": safe_date(item.expected_delivery_date),
        "hemoglobin_level": item.hemoglobin_level,
        "blood_pressure": item.blood_pressure,
        "weight": item.weight,
        "status": item.status,
        "anc_count": item.anc_count,
    }


def immunization_json(item):
    return {
        "immunization_id": item.immunization_id,
        "beneficiary_id": item.beneficiary_id,
        "vaccine_name": item.vaccine_name,
        "dose_number": item.dose_number,
        "scheduled_date": safe_date(item.scheduled_date),
        "given_date": safe_date(item.given_date),
        "status": item.status,
    }


def appointment_json(item):
    return {
        "appointment_id": item.appointment_id,
        "beneficiary_id": item.beneficiary_id,
        "appointment_type": item.appointment_type,
        "appointment_date": safe_date(item.appointment_date),
        "appointment_time": safe_time(item.appointment_time),
        "status": item.status,
        "notes": item.notes or "",
    }


def notice_json(item):
    return {
        "notice_id": item.notice_id,
        "beneficiary_id": item.beneficiary_id,
        "message": item.message,
        "notice_date": safe_date(item.notice_date),
        "status": item.status,
        "delivery_method": item.delivery_method,
    }


@router.get("")
def list_families(
    db: Session = Depends(get_db),
    current: AshaWorker = Depends(get_current_worker),
):
    worker_ids = visible_worker_ids(db, current)

    members = (
        db.query(Beneficiary)
        .filter(Beneficiary.asha_worker_id.in_(worker_ids))
        .all()
    )

    family_map = {}

    for member in members:
        family_name = member.address or "Unassigned Family"

        if family_name not in family_map:
            family_map[family_name] = {
                "family_name": family_name,
                "members": 0,
                "children": 0,
                "elderly": 0,
                "pregnant": 0,
                "general": 0,
            }

        family_map[family_name]["members"] += 1

        category = str(member.category or "general").lower()

        if category == "child":
            family_map[family_name]["children"] += 1
        elif category == "elderly":
            family_map[family_name]["elderly"] += 1
        elif category == "pregnant":
            family_map[family_name]["pregnant"] += 1
        else:
            family_map[family_name]["general"] += 1

    return sorted(
        family_map.values(),
        key=lambda item: item["family_name"].lower(),
    )


@router.get("/{family_name}/portfolio")
def get_family_portfolio(
    family_name: str,
    db: Session = Depends(get_db),
    current: AshaWorker = Depends(get_current_worker),
):
    worker_ids = visible_worker_ids(db, current)

    members = (
        db.query(Beneficiary)
        .filter(
            Beneficiary.asha_worker_id.in_(worker_ids),
            Beneficiary.address == family_name,
        )
        .order_by(Beneficiary.age.desc())
        .all()
    )

    if not members:
        raise HTTPException(status_code=404, detail="Family not found")

    member_ids = [item.beneficiary_id for item in members]

    pregnancies = (
        db.query(PregnancyRecord)
        .filter(PregnancyRecord.beneficiary_id.in_(member_ids))
        .all()
    )

    immunizations = (
        db.query(ImmunizationRecord)
        .filter(ImmunizationRecord.beneficiary_id.in_(member_ids))
        .all()
    )

    appointments = (
        db.query(Appointment)
        .filter(Appointment.beneficiary_id.in_(member_ids))
        .all()
    )

    notices = (
        db.query(Notice)
        .filter(Notice.beneficiary_id.in_(member_ids))
        .all()
    )

    pregnancies_by_member = {}
    immunizations_by_member = {}
    appointments_by_member = {}
    notices_by_member = {}

    for item in pregnancies:
        pregnancies_by_member.setdefault(item.beneficiary_id, []).append(item)

    for item in immunizations:
        immunizations_by_member.setdefault(item.beneficiary_id, []).append(item)

    for item in appointments:
        appointments_by_member.setdefault(item.beneficiary_id, []).append(item)

    for item in notices:
        notices_by_member.setdefault(item.beneficiary_id, []).append(item)

    member_profiles = []
    member_risks = []

    for member in members:
        member_pregnancies = pregnancies_by_member.get(member.beneficiary_id, [])
        member_immunizations = immunizations_by_member.get(member.beneficiary_id, [])
        member_appointments = appointments_by_member.get(member.beneficiary_id, [])
        member_notices = notices_by_member.get(member.beneficiary_id, [])

        risk = calculate_member_risk(
            member,
            member_pregnancies,
            member_immunizations,
            member_appointments,
        )

        member_risks.append(risk)

        member_profiles.append({
            "member": member_json(member),
            "risk": risk,
            "pregnancy_records": [pregnancy_json(item) for item in member_pregnancies],
            "immunization_records": [immunization_json(item) for item in member_immunizations],
            "appointments": [appointment_json(item) for item in member_appointments],
            "notices": [notice_json(item) for item in member_notices],
        })

    children = len([m for m in members if str(m.category or "").lower() == "child"])
    elderly = len([m for m in members if str(m.category or "").lower() == "elderly"])
    pregnant = len([m for m in members if str(m.category or "").lower() == "pregnant"])

    family_risk = build_family_risk(member_risks)

    next_actions = []

    if family_risk["level"] == "High Risk":
        next_actions.append("Plan urgent family-level follow-up visit.")

    if pregnant:
        next_actions.append("Check ANC/PNC care for pregnant family member.")

    if children:
        next_actions.append("Verify immunization status of child members.")

    if elderly:
        next_actions.append("Schedule routine elderly care follow-up.")

    missed_appointments = len([
        item for item in appointments
        if str(item.status or "").lower() == "missed"
    ])

    if missed_appointments:
        next_actions.append("Reschedule missed family appointments.")

    if not next_actions:
        next_actions.append("Continue regular family health monitoring.")

    timeline = []

    for item in pregnancies:
        member = next((m for m in members if m.beneficiary_id == item.beneficiary_id), None)
        timeline.append({
            "date": safe_date(item.registration_date),
            "type": "Pregnancy",
            "member": member.full_name if member else "N/A",
            "title": f"Pregnancy record marked {item.status}",
            "detail": f"ANC count: {item.anc_count or 0}",
            "status": item.status,
        })

    for item in immunizations:
        member = next((m for m in members if m.beneficiary_id == item.beneficiary_id), None)
        timeline.append({
            "date": safe_date(item.scheduled_date),
            "type": "Immunization",
            "member": member.full_name if member else "N/A",
            "title": f"{item.vaccine_name} Dose {item.dose_number}",
            "detail": f"Status: {item.status}",
            "status": item.status,
        })

    for item in appointments:
        member = next((m for m in members if m.beneficiary_id == item.beneficiary_id), None)
        timeline.append({
            "date": safe_date(item.appointment_date),
            "type": "Appointment",
            "member": member.full_name if member else "N/A",
            "title": item.appointment_type,
            "detail": f"{safe_time(item.appointment_time) or ''} {item.notes or ''}".strip(),
            "status": item.status,
        })

    for item in notices:
        member = next((m for m in members if m.beneficiary_id == item.beneficiary_id), None)
        timeline.append({
            "date": safe_date(item.notice_date),
            "type": "Notice",
            "member": member.full_name if member else "N/A",
            "title": "Notice sent",
            "detail": item.message,
            "status": item.status,
        })

    timeline.sort(key=lambda row: row.get("date") or "", reverse=True)

    asha_worker = db.get(AshaWorker, members[0].asha_worker_id)

    return {
        "family": {
            "family_name": family_name,
            "total_members": len(members),
            "children": children,
            "elderly": elderly,
            "pregnant": pregnant,
            "general": len(members) - children - elderly - pregnant,
            "asha_worker": {
                "worker_id": asha_worker.worker_id if asha_worker else None,
                "name": asha_worker.name if asha_worker else "N/A",
                "phone_no": asha_worker.phone_no if asha_worker else "",
                "village": asha_worker.village if asha_worker else "",
            },
        },
        "family_risk": family_risk,
        "next_actions": next_actions,
        "members": member_profiles,
        "timeline": timeline,
        "stats": {
            "pregnancy_records": len(pregnancies),
            "immunization_records": len(immunizations),
            "appointments": len(appointments),
            "notices": len(notices),
            "missed_appointments": missed_appointments,
        },
    }

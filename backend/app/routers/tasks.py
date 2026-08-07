from datetime import date, datetime, timedelta
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
    Event,
)

router = APIRouter(prefix="/api/tasks", tags=["Smart Tasks"])


def safe_date(value):
    if value is None:
        return None

    if isinstance(value, (date, datetime)):
        return value.isoformat()

    return str(value)


def task(priority, title, reason, beneficiary=None, task_type="general", due_date=None, action="Review"):
    return {
        "priority": priority,
        "title": title,
        "reason": reason,
        "type": task_type,
        "due_date": safe_date(due_date),
        "action": action,
        "beneficiary_id": beneficiary.beneficiary_id if beneficiary else None,
        "beneficiary_name": beneficiary.full_name if beneficiary else None,
        "beneficiary_phone": beneficiary.contact_no if beneficiary else None,
        "village": beneficiary.address if beneficiary else None,
    }


def priority_rank(value):
    order = {
        "high": 1,
        "medium": 2,
        "low": 3,
    }

    return order.get(value, 4)


@router.get("/today")
def todays_tasks(
    db: Session = Depends(get_db),
    current: AshaWorker = Depends(get_current_worker),
):
    today = date.today()
    next_week = today + timedelta(days=7)

    worker_ids = visible_worker_ids(db, current)

    beneficiaries = (
        db.query(Beneficiary)
        .filter(Beneficiary.asha_worker_id.in_(worker_ids))
        .all()
    )

    beneficiary_ids = [item.beneficiary_id for item in beneficiaries]
    beneficiary_map = {item.beneficiary_id: item for item in beneficiaries}

    tasks = []

    if not beneficiary_ids:
        return {
            "date": safe_date(today),
            "summary": {
                "total_tasks": 0,
                "high_priority": 0,
                "medium_priority": 0,
                "low_priority": 0,
            },
            "tasks": [],
            "message": "No beneficiaries found. Add beneficiaries to generate smart daily tasks.",
        }

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

    events = (
        db.query(Event)
        .filter(Event.organizer_id.in_(worker_ids))
        .all()
    )

    pregnancy_by_beneficiary = {}

    for item in pregnancies:
        pregnancy_by_beneficiary.setdefault(item.beneficiary_id, []).append(item)

    # 1. Today's appointments and missed appointments
    for item in appointments:
        beneficiary = beneficiary_map.get(item.beneficiary_id)
        status = str(item.status or "").lower()

        if not beneficiary:
            continue

        if item.appointment_date == today and status == "scheduled":
            tasks.append(
                task(
                    priority="medium",
                    title=f"Today's appointment: {item.appointment_type}",
                    reason=f"Appointment scheduled today at {item.appointment_time or 'time not added'}.",
                    beneficiary=beneficiary,
                    task_type="appointment",
                    due_date=item.appointment_date,
                    action="Complete visit",
                )
            )

        if status == "missed":
            tasks.append(
                task(
                    priority="high",
                    title="Reschedule missed appointment",
                    reason=f"{beneficiary.full_name} has a missed appointment that needs follow-up.",
                    beneficiary=beneficiary,
                    task_type="missed_appointment",
                    due_date=item.appointment_date,
                    action="Call and reschedule",
                )
            )

    # 2. Pregnancy follow-up automation
    for beneficiary in beneficiaries:
        category = str(beneficiary.category or "").lower()
        beneficiary_pregnancies = pregnancy_by_beneficiary.get(beneficiary.beneficiary_id, [])

        if category == "pregnant" and not beneficiary_pregnancies:
            tasks.append(
                task(
                    priority="high",
                    title="Add pregnancy record",
                    reason="Beneficiary is marked pregnant but no pregnancy/ANC record exists.",
                    beneficiary=beneficiary,
                    task_type="pregnancy",
                    due_date=today,
                    action="Create ANC record",
                )
            )

        for pregnancy in beneficiary_pregnancies:
            status = str(pregnancy.status or "").lower()

            if status == "high_risk":
                tasks.append(
                    task(
                        priority="high",
                        title="High-risk pregnancy follow-up",
                        reason="High-risk pregnancy record needs PHC/supervisor attention.",
                        beneficiary=beneficiary,
                        task_type="pregnancy",
                        due_date=today,
                        action="Escalate to PHC",
                    )
                )

            elif status == "active":
                anc_count = pregnancy.anc_count or 0

                if anc_count < 4:
                    tasks.append(
                        task(
                            priority="medium",
                            title="ANC follow-up pending",
                            reason=f"ANC count is {anc_count}. Continue regular pregnancy follow-up.",
                            beneficiary=beneficiary,
                            task_type="pregnancy",
                            due_date=today,
                            action="Schedule ANC visit",
                        )
                    )

    # 3. Immunization reminders
    for item in immunizations:
        beneficiary = beneficiary_map.get(item.beneficiary_id)

        if not beneficiary:
            continue

        status = str(item.status or "").lower()
        scheduled_date = item.scheduled_date

        if status == "missed":
            tasks.append(
                task(
                    priority="high",
                    title="Missed immunization follow-up",
                    reason=f"{item.vaccine_name} dose {item.dose_number} was missed.",
                    beneficiary=beneficiary,
                    task_type="immunization",
                    due_date=scheduled_date,
                    action="Reschedule vaccination",
                )
            )

        elif status in ["scheduled", "pending", "postponed"]:
            if scheduled_date and scheduled_date <= today:
                tasks.append(
                    task(
                        priority="medium",
                        title="Immunization due today",
                        reason=f"{item.vaccine_name} dose {item.dose_number} is due.",
                        beneficiary=beneficiary,
                        task_type="immunization",
                        due_date=scheduled_date,
                        action="Send reminder",
                    )
                )

            elif scheduled_date and today < scheduled_date <= next_week:
                tasks.append(
                    task(
                        priority="low",
                        title="Upcoming immunization",
                        reason=f"{item.vaccine_name} dose {item.dose_number} is due soon.",
                        beneficiary=beneficiary,
                        task_type="immunization",
                        due_date=scheduled_date,
                        action="Prepare reminder",
                    )
                )

    # 4. SOS follow-up tasks
    for alert in sos_alerts:
        status = str(alert.status or "").lower()

        if status == "active":
            tasks.append({
                "priority": "high",
                "title": "Active SOS follow-up",
                "reason": "An SOS alert is still active and requires closure or supervisor follow-up.",
                "type": "sos",
                "due_date": safe_date(today),
                "action": "Resolve SOS",
                "beneficiary_id": None,
                "beneficiary_name": None,
                "beneficiary_phone": None,
                "village": None,
            })

    # 5. Today's events
    for item in events:
        status = str(item.status or "").lower()

        if item.event_date == today and status in ["upcoming", "ongoing"]:
            tasks.append({
                "priority": "low",
                "title": f"Community event today: {item.event_name}",
                "reason": f"Event at {item.location or 'location not added'}.",
                "type": "event",
                "due_date": safe_date(item.event_date),
                "action": "Conduct event",
                "beneficiary_id": None,
                "beneficiary_name": None,
                "beneficiary_phone": None,
                "village": item.location or None,
            })

    tasks.sort(key=lambda item: (priority_rank(item["priority"]), item.get("due_date") or ""))

    high = len([item for item in tasks if item["priority"] == "high"])
    medium = len([item for item in tasks if item["priority"] == "medium"])
    low = len([item for item in tasks if item["priority"] == "low"])

    return {
        "date": safe_date(today),
        "summary": {
            "total_tasks": len(tasks),
            "high_priority": high,
            "medium_priority": medium,
            "low_priority": low,
        },
        "tasks": tasks,
        "message": "Smart daily tasks generated successfully.",
    }

from datetime import date, time, datetime
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session

from app.db.mysql import get_db
from app.deps import get_current_worker, visible_worker_ids
from app.models import AshaWorker, Event, Beneficiary, EventParticipant

router = APIRouter(prefix="/api/events", tags=["Events"])


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


def normalize_event_type(value):
    value = str(value or "other").strip().lower()

    mapping = {
        "vaccination": "vaccination",
        "immunization": "vaccination",
        "nutrition": "nutrition",
        "awareness": "awareness",
        "checkup": "checkup",
        "health camp": "checkup",
        "health_camp": "checkup",
        "other": "other",
    }

    return mapping.get(value, "other")


def normalize_status(value):
    value = str(value or "upcoming").strip().lower()

    mapping = {
        "upcoming": "upcoming",
        "ongoing": "ongoing",
        "completed": "completed",
        "complete": "completed",
        "cancelled": "cancelled",
        "canceled": "cancelled",
    }

    return mapping.get(value, "upcoming")


def serialize_event(item: Event):
    return {
        "event_id": item.event_id,
        "id": item.event_id,
        "title": item.event_name,
        "event_name": item.event_name,
        "category": item.event_type,
        "event_type": item.event_type,
        "description": item.description or "",
        "event_date": str(item.event_date),
        "date": str(item.event_date),
        "event_time": str(item.event_time),
        "time": str(item.event_time),
        "start_time": str(item.event_time),
        "location": item.location or "",
        "organizer_id": item.organizer_id,
        "status": item.status,
    }


@router.get("")
def list_events(
    db: Session = Depends(get_db),
    current: AshaWorker = Depends(get_current_worker),
):
    worker_ids = visible_worker_ids(db, current)

    events = (
        db.query(Event)
        .filter(Event.organizer_id.in_(worker_ids))
        .order_by(Event.event_date.asc())
        .all()
    )

    return [serialize_event(item) for item in events]


@router.post("")
def create_event(
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    current: AshaWorker = Depends(get_current_worker),
):
    event_name = payload.get("event_name") or payload.get("title") or payload.get("name")

    if not event_name:
        raise HTTPException(status_code=400, detail="Event title is required")

    event = Event(
        event_name=str(event_name).strip(),
        event_type=normalize_event_type(payload.get("event_type") or payload.get("category")),
        description=str(payload.get("description") or "").strip(),
        event_date=parse_date(payload.get("event_date") or payload.get("date")),
        event_time=parse_time(payload.get("event_time") or payload.get("start_time") or payload.get("time")),
        location=str(payload.get("location") or "").strip(),
        organizer_id=current.worker_id,
        status=normalize_status(payload.get("status")),
    )

    db.add(event)
    db.flush()
    db.commit()

    return "Event created successfully"


@router.post("/{event_id}/participants")
def add_participant(
    event_id: int,
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    current: AshaWorker = Depends(get_current_worker),
):
    event = db.get(Event, event_id)

    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    if current.role == "asha" and event.organizer_id != current.worker_id:
        raise HTTPException(status_code=403, detail="Access denied")

    beneficiary_id = payload.get("beneficiary_id")

    if not beneficiary_id:
        raise HTTPException(status_code=400, detail="Beneficiary is required")

    beneficiary = db.get(Beneficiary, int(beneficiary_id))

    if not beneficiary:
        raise HTTPException(status_code=404, detail="Beneficiary not found")

    participant = EventParticipant(
        event_id=event_id,
        beneficiary_id=int(beneficiary_id),
        attended=False,
    )

    db.add(participant)
    db.commit()

    return "Participant added successfully"

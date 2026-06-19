from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.mysql import get_db
from app.deps import get_current_worker
from app.models import AshaWorker, Beneficiary, Event, EventParticipant
from app.schemas import EventCreate, EventOut, EventParticipantCreate

router = APIRouter(prefix="/api/events", tags=["Events"])


@router.get("", response_model=list[EventOut])
def list_events(db: Session = Depends(get_db), current: AshaWorker = Depends(get_current_worker)):
    query = db.query(Event)
    if current.role == "asha":
        query = query.filter(Event.organizer_id == current.worker_id)
    return query.order_by(Event.event_date.asc()).all()


@router.post("", response_model=EventOut)
def create_event(payload: EventCreate, db: Session = Depends(get_db), current: AshaWorker = Depends(get_current_worker)):
    event = Event(**payload.model_dump(), organizer_id=current.worker_id)
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


@router.post("/{event_id}/participants")
def add_participant(event_id: int, payload: EventParticipantCreate, db: Session = Depends(get_db), current: AshaWorker = Depends(get_current_worker)):
    event = db.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    if current.role == "asha" and event.organizer_id != current.worker_id:
        raise HTTPException(status_code=403, detail="Not allowed")
    beneficiary = db.get(Beneficiary, payload.beneficiary_id)
    if not beneficiary:
        raise HTTPException(status_code=404, detail="Beneficiary not found")
    participant = EventParticipant(event_id=event_id, beneficiary_id=payload.beneficiary_id)
    db.add(participant)
    db.commit()
    return {"message": "Participant added"}

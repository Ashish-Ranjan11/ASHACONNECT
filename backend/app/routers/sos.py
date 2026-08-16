from fastapi import APIRouter, Depends, Body
from sqlalchemy.orm import Session

from app.db.mysql import get_db
from app.deps import get_current_worker, visible_worker_ids
from app.models import AshaWorker, SOSAlert

router = APIRouter(prefix="/api/sos", tags=["SOS"])


def serialize_sos(item: SOSAlert):
    return {
        "sos_id": item.sos_id,
        "id": item.sos_id,
        "worker_id": item.worker_id,
        "latitude": item.latitude,
        "longitude": item.longitude,
        "location": (
            f"{item.latitude}, {item.longitude}"
            if item.latitude is not None and item.longitude is not None
            else "N/A"
        ),
        "message": "Emergency assistance required",
        "severity": "high",
        "priority": "high",
        "triggered_at": str(item.triggered_at),
        "created_at": str(item.triggered_at),
        "resolved_at": str(item.resolved_at) if item.resolved_at else None,
        "status": item.status,
    }


@router.get("")
def list_sos_alerts(
    db: Session = Depends(get_db),
    current: AshaWorker = Depends(get_current_worker),
):
    worker_ids = visible_worker_ids(db, current)

    alerts = (
        db.query(SOSAlert)
        .filter(SOSAlert.worker_id.in_(worker_ids))
        .order_by(SOSAlert.sos_id.desc())
        .all()
    )

    return [serialize_sos(item) for item in alerts]


def create_alert(payload: dict, db: Session, current: AshaWorker):
    latitude = payload.get("latitude")
    longitude = payload.get("longitude")

    alert = SOSAlert(
        worker_id=current.worker_id,
        latitude=float(latitude) if latitude not in [None, ""] else None,
        longitude=float(longitude) if longitude not in [None, ""] else None,
        status="active",
    )

    db.add(alert)
    db.flush()
    db.commit()

    return "SOS alert triggered successfully"


@router.post("")
def trigger_sos_from_frontend(
    payload: dict = Body(default={}),
    db: Session = Depends(get_db),
    current: AshaWorker = Depends(get_current_worker),
):
    return create_alert(payload, db, current)


@router.post("/trigger")
def trigger_sos(
    payload: dict = Body(default={}),
    db: Session = Depends(get_db),
    current: AshaWorker = Depends(get_current_worker),
):
    return create_alert(payload, db, current)

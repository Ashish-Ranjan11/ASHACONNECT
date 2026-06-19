from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.mysql import get_db
from app.deps import get_current_worker
from app.models import AshaWorker, SOSAlert
from app.schemas import SOSCreate, SOSOut

router = APIRouter(prefix="/api/sos", tags=["SOS"])


@router.get("", response_model=list[SOSOut])
def list_sos_alerts(db: Session = Depends(get_db), current: AshaWorker = Depends(get_current_worker)):
    query = db.query(SOSAlert)
    if current.role == "asha":
        query = query.filter(SOSAlert.worker_id == current.worker_id)
    return query.order_by(SOSAlert.sos_id.desc()).all()


@router.post("/trigger")
def trigger_sos(payload: SOSCreate, db: Session = Depends(get_db), current: AshaWorker = Depends(get_current_worker)):
    alert = SOSAlert(worker_id=current.worker_id, latitude=payload.latitude, longitude=payload.longitude, status="active")
    db.add(alert)
    db.commit()
    db.refresh(alert)

    # Placeholder for external integrations: Police/Hospital/SMS gateway.
    return {
        "message": "Help is on the way",
        "alert_id": alert.sos_id,
        "worker": current.name,
        "worker_sos_id": current.sos_id,
        "location": {"latitude": payload.latitude, "longitude": payload.longitude},
        "notified": ["PHC Admin", "Emergency Contacts", "Nearest Hospital placeholder"],
    }

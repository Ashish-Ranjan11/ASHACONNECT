from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session

from app.db.mysql import get_db
from app.deps import get_current_worker, visible_worker_ids
from app.models import AshaWorker, Beneficiary, Notice

router = APIRouter(prefix="/api/notices", tags=["Notices"])


def serialize_notice(item: Notice):
    return {
        "notice_id": item.notice_id,
        "id": item.notice_id,
        "title": "Notice",
        "beneficiary_id": item.beneficiary_id,
        "sent_by": item.sent_by,
        "message": item.message,
        "notice_date": str(item.notice_date),
        "created_at": str(item.notice_date),
        "status": item.status,
        "priority": item.status,
        "delivery_method": item.delivery_method,
    }


def get_first_visible_beneficiary(db: Session, current: AshaWorker):
    worker_ids = visible_worker_ids(db, current)

    return (
        db.query(Beneficiary)
        .filter(Beneficiary.asha_worker_id.in_(worker_ids))
        .order_by(Beneficiary.beneficiary_id.desc())
        .first()
    )


@router.get("")
def list_notices(
    db: Session = Depends(get_db),
    current: AshaWorker = Depends(get_current_worker),
):
    query = db.query(Notice)

    if current.role == "asha":
        query = query.filter(Notice.sent_by == current.worker_id)

    notices = query.order_by(Notice.notice_id.desc()).all()

    return [serialize_notice(item) for item in notices]


@router.post("")
def send_notice(
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    current: AshaWorker = Depends(get_current_worker),
):
    beneficiary_id = payload.get("beneficiary_id")

    if beneficiary_id:
        beneficiary = db.get(Beneficiary, int(beneficiary_id))
    else:
        beneficiary = get_first_visible_beneficiary(db, current)

    if not beneficiary:
        raise HTTPException(
            status_code=400,
            detail="Add at least one beneficiary before creating a notice",
        )

    worker_ids = visible_worker_ids(db, current)

    if beneficiary.asha_worker_id not in worker_ids:
        raise HTTPException(status_code=403, detail="Access denied")

    title = str(payload.get("title") or "Notice").strip()
    message = str(payload.get("message") or payload.get("description") or "").strip()

    if title and message:
        final_message = f"{title}: {message}"
    elif message:
        final_message = message
    else:
        final_message = title

    notice = Notice(
        beneficiary_id=beneficiary.beneficiary_id,
        sent_by=current.worker_id,
        message=final_message,
        notice_date=date.today(),
        status="sent",
        delivery_method=str(payload.get("delivery_method") or "sms").strip(),
    )

    db.add(notice)
    db.flush()
    db.commit()

    return "Notice sent successfully"

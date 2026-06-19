from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.mysql import get_db
from app.deps import get_current_worker
from app.models import AshaWorker, Beneficiary, Notice
from app.schemas import NoticeCreate, NoticeOut

router = APIRouter(prefix="/api/notices", tags=["Notices"])


@router.get("", response_model=list[NoticeOut])
def list_notices(db: Session = Depends(get_db), current: AshaWorker = Depends(get_current_worker)):
    query = db.query(Notice)
    if current.role == "asha":
        query = query.filter(Notice.sent_by == current.worker_id)
    return query.order_by(Notice.notice_id.desc()).all()


@router.post("", response_model=NoticeOut)
def send_notice(payload: NoticeCreate, db: Session = Depends(get_db), current: AshaWorker = Depends(get_current_worker)):
    beneficiary = db.get(Beneficiary, payload.beneficiary_id)
    if not beneficiary:
        raise HTTPException(status_code=404, detail="Beneficiary not found")
    if current.role == "asha" and beneficiary.asha_worker_id != current.worker_id:
        raise HTTPException(status_code=403, detail="Not allowed")

    data = payload.model_dump()
    data["notice_date"] = payload.notice_date or date.today()
    notice = Notice(**data, sent_by=current.worker_id, status="sent")
    db.add(notice)
    db.commit()
    db.refresh(notice)
    return notice

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.clerk_auth import authenticate_clerk_request
from app.db.mysql import get_db
from app.models import AshaWorker


def get_current_clerk_worker(
    request: Request,
    db: Session = Depends(get_db),
):
    state = authenticate_clerk_request(request)

    payload = state.payload or {}

    email = (
        payload.get("email")
        or payload.get("primary_email")
        or payload.get("email_address")
    )

    if not email:
        raise HTTPException(
            status_code=401,
            detail="Clerk session does not contain a mapped staff email",
        )

    worker = (
        db.query(AshaWorker)
        .filter(AshaWorker.email == str(email).lower())
        .first()
    )

    if not worker:
        raise HTTPException(
            status_code=403,
            detail="Clerk user is not mapped to an ASHA Connect staff account",
        )

    if not worker.is_active:
        raise HTTPException(
            status_code=403,
            detail="Staff account is inactive",
        )

    return worker

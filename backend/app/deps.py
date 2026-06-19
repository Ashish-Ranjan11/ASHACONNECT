from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.db.mysql import get_db
from app.models import AshaWorker
from app.security import decode_access_token

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_worker(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> AshaWorker:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing token")

    worker_id = decode_access_token(credentials.credentials)
    if not worker_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    worker = db.get(AshaWorker, int(worker_id))
    if not worker or not worker.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Worker not found or inactive")
    return worker

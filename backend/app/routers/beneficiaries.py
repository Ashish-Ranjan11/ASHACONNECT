from datetime import date, datetime
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session

from app.db.mysql import get_db
from app.deps import get_current_worker, visible_worker_ids
from app.models import AshaWorker, Beneficiary

router = APIRouter(prefix="/api/beneficiaries", tags=["Beneficiaries"])


def parse_date(value):
    if isinstance(value, date):
        return value

    value = str(value or "").strip()

    if not value:
        return None

    formats = ["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%m/%d/%Y"]

    for fmt in formats:
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            pass

    return None


def normalize_gender(value):
    value = str(value or "Female").strip().lower()

    mapping = {
        "male": "Male",
        "m": "Male",
        "female": "Female",
        "f": "Female",
        "other": "Other",
    }

    return mapping.get(value, "Female")


def normalize_category(value):
    value = str(value or "general").strip().lower()

    mapping = {
        "pregnant": "pregnant",
        "pregnancy": "pregnant",
        "mother": "pregnant",
        "child": "child",
        "children": "child",
        "elderly": "elderly",
        "old": "elderly",
        "general": "general",
    }

    return mapping.get(value, "general")


def safe_int(value, default=0):
    try:
        if value in [None, ""]:
            return default
        return int(value)
    except Exception:
        return default


def serialize_beneficiary(item: Beneficiary):
    return {
        "beneficiary_id": item.beneficiary_id,
        "id": item.beneficiary_id,
        "name": item.full_name,
        "full_name": item.full_name,
        "age": item.age,
        "gender": item.gender,
        "phone": item.contact_no or "",
        "phone_no": item.contact_no or "",
        "contact_no": item.contact_no or "",
        "village": item.address or "",
        "address": item.address or "",
        "category": item.category or "general",
        "asha_worker_id": item.asha_worker_id,
        "is_active": item.is_active,

        # ASHA register extended fields
        "education": item.education or "",
        "occupation_type": item.occupation_type or "",
        "occupation_detail": item.occupation_detail or "",
        "marital_status": item.marital_status or "",
        "religion": item.religion or "",
        "family_baby_count": item.family_baby_count or 0,
        "last_baby_birth_date": str(item.last_baby_birth_date) if item.last_baby_birth_date else "",
    }


def get_beneficiary_or_404(db: Session, beneficiary_id: int, current: AshaWorker):
    worker_ids = visible_worker_ids(db, current)

    beneficiary = (
        db.query(Beneficiary)
        .filter(Beneficiary.beneficiary_id == beneficiary_id)
        .first()
    )

    if not beneficiary:
        raise HTTPException(status_code=404, detail="Beneficiary not found")

    if beneficiary.asha_worker_id not in worker_ids:
        raise HTTPException(status_code=403, detail="Access denied")

    return beneficiary


def apply_register_fields(beneficiary: Beneficiary, payload: dict):
    if "education" in payload:
        beneficiary.education = str(payload.get("education") or "").strip()

    if "occupation_type" in payload:
        beneficiary.occupation_type = str(payload.get("occupation_type") or "").strip()

    if "occupation_detail" in payload:
        beneficiary.occupation_detail = str(payload.get("occupation_detail") or "").strip()

    if "marital_status" in payload:
        beneficiary.marital_status = str(payload.get("marital_status") or "").strip()

    if "religion" in payload:
        beneficiary.religion = str(payload.get("religion") or "").strip()

    if "family_baby_count" in payload:
        beneficiary.family_baby_count = safe_int(payload.get("family_baby_count"), 0)

    if "last_baby_birth_date" in payload:
        beneficiary.last_baby_birth_date = parse_date(payload.get("last_baby_birth_date"))


@router.get("")
def list_beneficiaries(
    db: Session = Depends(get_db),
    current: AshaWorker = Depends(get_current_worker),
):
    worker_ids = visible_worker_ids(db, current)

    beneficiaries = (
        db.query(Beneficiary)
        .filter(Beneficiary.asha_worker_id.in_(worker_ids))
        .order_by(Beneficiary.beneficiary_id.desc())
        .all()
    )

    return [serialize_beneficiary(item) for item in beneficiaries]


@router.post("")
def create_beneficiary(
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    current: AshaWorker = Depends(get_current_worker),
):
    name = payload.get("name") or payload.get("full_name") or payload.get("beneficiary_name")
    age = payload.get("age")

    if not name:
        raise HTTPException(status_code=400, detail="Name is required")

    if age in [None, ""]:
        raise HTTPException(status_code=400, detail="Age is required")

    phone = payload.get("phone") or payload.get("phone_no") or payload.get("contact_no") or ""
    village = payload.get("village") or ""
    address = payload.get("address") or village or ""

    beneficiary = Beneficiary(
        full_name=str(name).strip(),
        age=int(age),
        gender=normalize_gender(payload.get("gender")),
        address=str(address).strip(),
        contact_no=str(phone).strip(),
        category=normalize_category(payload.get("category")),
        asha_worker_id=current.worker_id,
        is_active=True,
    )

    apply_register_fields(beneficiary, payload)

    db.add(beneficiary)
    db.flush()
    db.commit()

    return "Beneficiary added successfully"


@router.put("/{beneficiary_id}")
def update_beneficiary(
    beneficiary_id: int,
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    current: AshaWorker = Depends(get_current_worker),
):
    beneficiary = get_beneficiary_or_404(db, beneficiary_id, current)

    name = payload.get("name") or payload.get("full_name") or payload.get("beneficiary_name")

    if name is not None:
        beneficiary.full_name = str(name).strip()

    if "age" in payload and payload.get("age") not in [None, ""]:
        beneficiary.age = int(payload.get("age"))

    if "gender" in payload:
        beneficiary.gender = normalize_gender(payload.get("gender"))

    if "category" in payload:
        beneficiary.category = normalize_category(payload.get("category"))

    phone = payload.get("phone") or payload.get("phone_no") or payload.get("contact_no")

    if phone is not None:
        beneficiary.contact_no = str(phone).strip()

    village = payload.get("village")
    address = payload.get("address")

    if address is not None:
        beneficiary.address = str(address).strip()
    elif village is not None:
        beneficiary.address = str(village).strip()

    apply_register_fields(beneficiary, payload)

    db.commit()

    return "Beneficiary updated successfully"


@router.delete("/{beneficiary_id}")
def delete_beneficiary(
    beneficiary_id: int,
    db: Session = Depends(get_db),
    current: AshaWorker = Depends(get_current_worker),
):
    beneficiary = get_beneficiary_or_404(db, beneficiary_id, current)

    db.delete(beneficiary)
    db.commit()

    return "Beneficiary deleted successfully"

from fastapi import APIRouter, Depends, HTTPException, Body
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.mysql import get_db
from app.models import Beneficiary
from app.security import (
    audit_log,
    create_access_token,
    decode_access_token,
    verify_password,
)

router = APIRouter(prefix="/api/family-auth", tags=["Family Login"])

family_oauth = OAuth2PasswordBearer(tokenUrl="/api/family-auth/login")


def get_current_family(
    token: str = Depends(family_oauth),
    db: Session = Depends(get_db),
):
    payload = decode_access_token(token)

    if not payload or payload.get("account_type") != "family":
        raise HTTPException(status_code=401, detail="Invalid family token")

    account_id = payload.get("sub")

    row = db.execute(
        text(
            """
            SELECT id, family_name, email, phone, is_active
            FROM family_accounts
            WHERE id = :id
            """
        ),
        {"id": account_id},
    ).mappings().first()

    if not row:
        raise HTTPException(status_code=401, detail="Family account not found")

    if not row["is_active"]:
        raise HTTPException(status_code=403, detail="Family account disabled")

    return dict(row)


@router.post("/login")
def family_login(payload: dict = Body(...), db: Session = Depends(get_db)):
    email = str(payload.get("email") or "").strip().lower()
    password = str(payload.get("password") or "")

    row = db.execute(
        text(
            """
            SELECT id, family_name, email, phone, password_hash, is_active
            FROM family_accounts
            WHERE email = :email
            """
        ),
        {"email": email},
    ).mappings().first()

    if not row:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not row["is_active"]:
        raise HTTPException(status_code=403, detail="Family account disabled")

    if not verify_password(password, row["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token(
        {
            "sub": str(row["id"]),
            "email": row["email"],
            "role": "family",
            "account_type": "family",
            "family_name": row["family_name"],
        }
    )

    audit_log(
        db,
        "family",
        row["id"],
        "family",
        "FAMILY_LOGIN_SUCCESS",
        "FamilyAccount",
        row["id"],
        f"Family login for {row['family_name']}",
    )

    return {
        "access_token": token,
        "token_type": "bearer",
        "role": "family",
        "family": {
            "id": row["id"],
            "family_name": row["family_name"],
            "email": row["email"],
            "phone": row["phone"],
        },
    }


@router.get("/me")
def family_me(current=Depends(get_current_family)):
    return current


@router.get("/portfolio")
def family_portfolio(
    db: Session = Depends(get_db),
    current=Depends(get_current_family),
):
    family_name = current["family_name"]

    members = (
        db.query(Beneficiary)
        .filter(Beneficiary.address == family_name)
        .order_by(Beneficiary.age.desc())
        .all()
    )

    return {
        "family_name": family_name,
        "total_members": len(members),
        "members": [
            {
                "beneficiary_id": member.beneficiary_id,
                "name": member.full_name,
                "age": member.age,
                "gender": member.gender,
                "category": member.category,
                "education": getattr(member, "education", "") or "",
                "occupation_type": getattr(member, "occupation_type", "") or "",
                "marital_status": getattr(member, "marital_status", "") or "",
                "religion": getattr(member, "religion", "") or "",
            }
            for member in members
        ],
    }

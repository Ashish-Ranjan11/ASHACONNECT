from datetime import datetime

from sqlalchemy import text

from app.db.mysql import SessionLocal
from app.models import AshaWorker, Beneficiary
from app.security import hash_password


def create_tables(db):
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                actor_type TEXT NOT NULL,
                actor_id TEXT NOT NULL,
                actor_role TEXT NOT NULL,
                action TEXT NOT NULL,
                entity_type TEXT DEFAULT '',
                entity_id TEXT DEFAULT '',
                details TEXT DEFAULT '',
                created_at TEXT NOT NULL
            )
            """
        )
    )

    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS family_accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                family_name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                phone TEXT DEFAULT '',
                password_hash TEXT NOT NULL,
                is_active INTEGER DEFAULT 1,
                created_at TEXT NOT NULL
            )
            """
        )
    )

    db.commit()


def unique_phone(db, preferred_phone, email):
    preferred_phone = str(preferred_phone or "").strip()

    if preferred_phone:
        conflict = (
            db.query(AshaWorker)
            .filter(AshaWorker.phone_no == preferred_phone)
            .filter(AshaWorker.email != email)
            .first()
        )

        if not conflict:
            return preferred_phone

    for number in range(8100000001, 8199999999):
        candidate = str(number)

        conflict = db.query(AshaWorker).filter(AshaWorker.phone_no == candidate).first()

        if not conflict:
            return candidate

    raise RuntimeError("Could not generate unique phone number")


def unique_sos_id(db, preferred_sos, email):
    preferred_sos = str(preferred_sos or "").strip()

    if preferred_sos:
        conflict = (
            db.query(AshaWorker)
            .filter(AshaWorker.sos_id == preferred_sos)
            .filter(AshaWorker.email != email)
            .first()
        )

        if not conflict:
            return preferred_sos

    base = email.split("@")[0].replace(".", "-").upper()

    for index in range(1, 10000):
        candidate = f"SOS-{base}-{index}"

        conflict = db.query(AshaWorker).filter(AshaWorker.sos_id == candidate).first()

        if not conflict:
            return candidate

    raise RuntimeError("Could not generate unique SOS ID")


def upsert_worker(db, email, password, name, role, phone, village, phc_id=None):
    email = email.strip().lower()

    worker = db.query(AshaWorker).filter(AshaWorker.email == email).first()

    safe_phone = unique_phone(db, phone, email)
    safe_sos = unique_sos_id(db, f"SOS-{email.split('@')[0].replace('.', '-').upper()}", email)

    if worker:
        worker.name = name
        worker.password_hash = hash_password(password)
        worker.role = role
        worker.phone_no = safe_phone
        worker.village = village
        worker.address = village
        worker.qualification = worker.qualification or "Community Health Operations"
        worker.is_active = True

        if phc_id is not None:
            worker.phc_id = phc_id
    else:
        worker = AshaWorker(
            name=name,
            email=email,
            phone_no=safe_phone,
            password_hash=hash_password(password),
            village=village,
            address=village,
            age=30,
            gender="Female",
            qualification="Community Health Operations",
            phc_id=phc_id,
            is_active=True,
            role=role,
            sos_id=safe_sos,
        )
        db.add(worker)

    db.commit()
    db.refresh(worker)
    return worker


def upsert_family_account(db):
    family_name_row = (
        db.query(Beneficiary.address)
        .filter(Beneficiary.address.isnot(None))
        .filter(Beneficiary.address != "")
        .first()
    )

    family_name = family_name_row[0] if family_name_row else "Demo Family"

    existing = db.execute(
        text("SELECT id FROM family_accounts WHERE email = :email"),
        {"email": "family.demo@ashaconnect.in"},
    ).first()

    if existing:
        db.execute(
            text(
                """
                UPDATE family_accounts
                SET family_name = :family_name,
                    password_hash = :password_hash,
                    is_active = 1
                WHERE email = :email
                """
            ),
            {
                "family_name": family_name,
                "password_hash": hash_password("Family@123"),
                "email": "family.demo@ashaconnect.in",
            },
        )
    else:
        db.execute(
            text(
                """
                INSERT INTO family_accounts
                (family_name, email, phone, password_hash, is_active, created_at)
                VALUES
                (:family_name, :email, :phone, :password_hash, 1, :created_at)
                """
            ),
            {
                "family_name": family_name,
                "email": "family.demo@ashaconnect.in",
                "phone": "",
                "password_hash": hash_password("Family@123"),
                "created_at": datetime.utcnow().isoformat(),
            },
        )

    db.commit()
    return family_name


def main():
    db = SessionLocal()

    try:
        create_tables(db)

        first_worker = db.query(AshaWorker).order_by(AshaWorker.worker_id.asc()).first()
        phc_id = first_worker.phc_id if first_worker else None
        village = first_worker.village if first_worker else "Majitar Village"

        asha = upsert_worker(
            db,
            email="asha@ashaconnect.in",
            password="Asha@123",
            name="ASHA Field Worker",
            role="asha",
            phone="9000000001",
            village=village,
            phc_id=phc_id,
        )

        admin = upsert_worker(
            db,
            email="phc.admin@ashaconnect.in",
            password="Admin@123",
            name="PHC Administrator",
            role="phc_admin",
            phone="9000000002",
            village=village,
            phc_id=phc_id,
        )

        supervisor = upsert_worker(
            db,
            email="supervisor@ashaconnect.in",
            password="Supervisor@123",
            name="Field Supervisor",
            role="supervisor",
            phone="9000000003",
            village=village,
            phc_id=phc_id,
        )

        family_name = upsert_family_account(db)

        print("Security upgrade complete.")
        print("")
        print("Staff logins:")
        print(f"ASHA Worker:     asha@ashaconnect.in / Asha@123 / phone: {asha.phone_no}")
        print(f"PHC Admin:       phc.admin@ashaconnect.in / Admin@123 / phone: {admin.phone_no}")
        print(f"Supervisor:      supervisor@ashaconnect.in / Supervisor@123 / phone: {supervisor.phone_no}")
        print("")
        print("Family login:")
        print("Family:          family.demo@ashaconnect.in / Family@123")
        print(f"Family mapped:   {family_name}")

    finally:
        db.close()


if __name__ == "__main__":
    main()

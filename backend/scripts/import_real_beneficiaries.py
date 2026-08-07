from app.db.mysql import SessionLocal
from app.models import (
    AshaWorker,
    Beneficiary,
    Appointment,
    PregnancyRecord,
    ImmunizationRecord,
    Notice,
)

REAL_BENEFICIARIES = [
    # Kunda Chettri family
    {"full_name": "Kunda Chettri", "age": 57, "gender": "Female", "address": "Kunda Chettri Family", "category": "general"},
    {"full_name": "Bishna Chettri", "age": 46, "gender": "Male", "address": "Kunda Chettri Family", "category": "general"},
    {"full_name": "Alia Chettri", "age": 34, "gender": "Female", "address": "Kunda Chettri Family", "category": "general"},
    {"full_name": "Aarav Chettri", "age": 3, "gender": "Male", "address": "Kunda Chettri Family", "category": "child"},

    # Saran Mohan Budathoki family
    {"full_name": "Saran Mohan Budathoki", "age": 70, "gender": "Male", "address": "Saran Mohan Budathoki Family", "category": "elderly"},
    {"full_name": "Saraswoti Mohan Budathoki", "age": 68, "gender": "Female", "address": "Saran Mohan Budathoki Family", "category": "elderly"},
    {"full_name": "Sadin Kumar Budathoki", "age": 35, "gender": "Male", "address": "Saran Mohan Budathoki Family", "category": "general"},

    # Ashok Manger family
    {"full_name": "Ashok Manger", "age": 55, "gender": "Male", "address": "Ashok Manger Family", "category": "general"},
    {"full_name": "Pashupati Manger", "age": 28, "gender": "Male", "address": "Ashok Manger Family", "category": "general"},
    {"full_name": "Bishant Manger", "age": 26, "gender": "Male", "address": "Ashok Manger Family", "category": "general"},
    {"full_name": "Diya Manger", "age": 24, "gender": "Female", "address": "Ashok Manger Family", "category": "general"},
    {"full_name": "Kusum Manger", "age": 22, "gender": "Female", "address": "Ashok Manger Family", "category": "general"},
    {"full_name": "Aditya Manger", "age": 19, "gender": "Male", "address": "Ashok Manger Family", "category": "general"},
    {"full_name": "Pratiksha Manger", "age": 14, "gender": "Female", "address": "Ashok Manger Family", "category": "child"},

    # C. B. Gurung family
    {"full_name": "Manjili Subba", "age": 78, "gender": "Male", "address": "C. B. Gurung Family", "category": "elderly"},
    {"full_name": "Pratika Gurung", "age": 35, "gender": "Female", "address": "C. B. Gurung Family", "category": "general"},
    {"full_name": "Romila Gurung", "age": 34, "gender": "Female", "address": "C. B. Gurung Family", "category": "general"},
    {"full_name": "Ronik Gurung", "age": 14, "gender": "Male", "address": "C. B. Gurung Family", "category": "child"},
    {"full_name": "Neelam Gurung", "age": 35, "gender": "Male", "address": "C. B. Gurung Family", "category": "general"},

    # Dhan Bdr Gurung family
    {"full_name": "Dhan Bdr Gurung", "age": 62, "gender": "Male", "address": "Dhan Bdr Gurung Family", "category": "elderly"},
    {"full_name": "Bhim Maya Gurung", "age": 54, "gender": "Female", "address": "Dhan Bdr Gurung Family", "category": "general"},
    {"full_name": "Sudhan Gurung", "age": 32, "gender": "Male", "address": "Dhan Bdr Gurung Family", "category": "general"},
    {"full_name": "Sulika Gurung", "age": 24, "gender": "Female", "address": "Dhan Bdr Gurung Family", "category": "general"},
    {"full_name": "Shivig Gurung", "age": 20, "gender": "Female", "address": "Dhan Bdr Gurung Family", "category": "general"},

    # Narayan Gurung family
    {"full_name": "Narayan Gurung", "age": 70, "gender": "Male", "address": "Narayan Gurung Family", "category": "elderly"},
    {"full_name": "Meena Gurung", "age": 62, "gender": "Female", "address": "Narayan Gurung Family", "category": "elderly"},
    {"full_name": "Kanjira Gurung", "age": 43, "gender": "Female", "address": "Narayan Gurung Family", "category": "general"},
]


def main():
    db = SessionLocal()

    try:
        asha = (
            db.query(AshaWorker)
            .filter(AshaWorker.role == "asha")
            .order_by(AshaWorker.worker_id.asc())
            .first()
        )

        if not asha:
            raise RuntimeError("No ASHA worker found. Run seed first.")

        print(f"Using ASHA Worker: {asha.name} | ID: {asha.worker_id}")

        # Delete dependent records first because they reference beneficiaries
        db.query(Notice).delete()
        db.query(ImmunizationRecord).delete()
        db.query(PregnancyRecord).delete()
        db.query(Appointment).delete()
        db.query(Beneficiary).delete()

        db.commit()

        inserted = 0

        for row in REAL_BENEFICIARIES:
            beneficiary = Beneficiary(
                full_name=row["full_name"],
                age=row["age"],
                gender=row["gender"],
                address=row["address"],
                contact_no="",
                category=row["category"],
                asha_worker_id=asha.worker_id,
                is_active=True,
            )

            db.add(beneficiary)
            inserted += 1

        db.commit()

        print(f"Deleted old beneficiaries and inserted {inserted} real beneficiaries.")

    except Exception as e:
        db.rollback()
        print("Import failed:", e)
        raise

    finally:
        db.close()


if __name__ == "__main__":
    main()

from datetime import date, timedelta

from app.db.mysql import Base, engine, SessionLocal
from app.models import (
    PrimaryHealthCentre,
    AshaWorker,
    Beneficiary,
    PregnancyRecord,
    ImmunizationRecord,
    Appointment,
    Event,
    Notice,
    MonthlyReport,
)
from app.security import hash_password


Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

db = SessionLocal()

try:
    today = date.today()

    phc = PrimaryHealthCentre(
        name="Majitar Primary Health Centre",
        location="Majitar, East Sikkim",
        contact_no="9876543210",
        email="phc@example.com",
    )
    db.add(phc)
    db.commit()
    db.refresh(phc)

    worker = AshaWorker(
        name="Demo ASHA Worker",
        email="asha@example.com",
        phone_no="9000000001",
        password_hash=hash_password("password123"),
        village="Majitar Village",
        address="Near PHC, Majitar",
        age=32,
        gender="Female",
        qualification="10th Pass",
        phc_id=phc.phc_id,
        is_active=True,
        role="asha",
        sos_id="SOS-MAJ-001",
    )
    db.add(worker)
    db.commit()
    db.refresh(worker)

    b1 = Beneficiary(
        full_name="Sita Sharma",
        age=24,
        gender="Female",
        address="Majitar Ward 1",
        contact_no="9100000001",
        category="pregnant",
        asha_worker_id=worker.worker_id,
    )
    b2 = Beneficiary(
        full_name="Anita Rai",
        age=27,
        gender="Female",
        address="Majitar Ward 2",
        contact_no="9100000002",
        category="pregnant",
        asha_worker_id=worker.worker_id,
    )
    b3 = Beneficiary(
        full_name="Rohan Tamang",
        age=1,
        gender="Male",
        address="Majitar Ward 3",
        contact_no="9100000003",
        category="child",
        asha_worker_id=worker.worker_id,
    )
    b4 = Beneficiary(
        full_name="Maya Lepcha",
        age=68,
        gender="Female",
        address="Majitar Ward 4",
        contact_no="9100000004",
        category="elderly",
        asha_worker_id=worker.worker_id,
    )

    db.add_all([b1, b2, b3, b4])
    db.commit()

    for b in [b1, b2, b3, b4]:
        db.refresh(b)

    db.add_all([
        PregnancyRecord(
            beneficiary_id=b1.beneficiary_id,
            registration_date=today - timedelta(days=60),
            lmp_date=today - timedelta(days=120),
            expected_delivery_date=today + timedelta(days=160),
            hemoglobin_level=9.8,
            blood_pressure="145/95",
            weight=51.5,
            status="high_risk",
            anc_count=2,
            created_by=worker.worker_id,
        ),
        PregnancyRecord(
            beneficiary_id=b2.beneficiary_id,
            registration_date=today - timedelta(days=35),
            lmp_date=today - timedelta(days=90),
            expected_delivery_date=today + timedelta(days=190),
            hemoglobin_level=11.4,
            blood_pressure="120/80",
            weight=55.0,
            status="active",
            anc_count=1,
            created_by=worker.worker_id,
        ),
        ImmunizationRecord(
            beneficiary_id=b3.beneficiary_id,
            vaccine_name="Pentavalent",
            dose_number=2,
            scheduled_date=today + timedelta(days=5),
            status="scheduled",
            created_by=worker.worker_id,
        ),
        ImmunizationRecord(
            beneficiary_id=b3.beneficiary_id,
            vaccine_name="OPV",
            dose_number=1,
            scheduled_date=today - timedelta(days=3),
            status="missed",
            created_by=worker.worker_id,
        ),
        Appointment(
            beneficiary_id=b1.beneficiary_id,
            appointment_date=today + timedelta(days=2),
            appointment_type="ANC Checkup",
            status="scheduled",
            notes="High BP follow-up required",
            created_by=worker.worker_id,
        ),
        Appointment(
            beneficiary_id=b3.beneficiary_id,
            appointment_date=today + timedelta(days=5),
            appointment_type="Immunization Visit",
            status="scheduled",
            notes="Pentavalent dose due",
            created_by=worker.worker_id,
        ),
        Event(
            event_name="Village Nutrition Awareness Drive",
            event_type="nutrition",
            description="Nutrition and anemia awareness camp for mothers and children.",
            event_date=today + timedelta(days=7),
            location="Majitar Community Hall",
            organizer_id=worker.worker_id,
            status="upcoming",
        ),
        Notice(
            beneficiary_id=b1.beneficiary_id,
            sent_by=worker.worker_id,
            message="Reminder: ANC checkup scheduled soon. Please visit PHC on time.",
            notice_date=today,
            status="sent",
            delivery_method="sms",
        ),
        MonthlyReport(
            month=today.strftime("%B"),
            year=today.year,
            total_patients=4,
            total_pregnancies=2,
            total_immunizations=2,
            total_appointments=2,
            total_events=1,
            generated_by=worker.worker_id,
            phc_id=phc.phc_id,
            status="submitted",
            notes="Demo monthly report generated for ASHACONNECT dashboard.",
        ),
    ])

    db.commit()

    print("Seed complete")
    print("Login email: asha@example.com")
    print("Login password: password123")

finally:
    db.close()

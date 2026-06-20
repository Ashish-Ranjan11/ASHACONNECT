from datetime import date, timedelta, time

from app.db.mysql import Base, engine, SessionLocal
from app.models import (
    PrimaryHealthCentre,
    AshaWorker,
    Beneficiary,
    PregnancyRecord,
    ImmunizationRecord,
    Appointment,
    Event,
    EventParticipant,
    Notice,
    MonthlyReport,
    SOSAlert,
)
from app.security import hash_password


Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

db = SessionLocal()


def create_worker(
    name,
    email,
    phone_no,
    role,
    phc_id,
    village,
    sos_id,
    gender="Female",
):
    worker = AshaWorker(
        name=name,
        email=email,
        phone_no=phone_no,
        password_hash=hash_password("password123"),
        village=village,
        address=f"{village}, Sikkim",
        age=32,
        gender=gender,
        qualification="10th Pass" if role == "asha" else "Graduate",
        phc_id=phc_id,
        is_active=True,
        role=role,
        sos_id=sos_id,
    )
    db.add(worker)
    db.commit()
    db.refresh(worker)
    return worker


try:
    today = date.today()

    phc1 = PrimaryHealthCentre(
        name="Majitar Primary Health Centre",
        location="Majitar, East Sikkim",
        contact_no="9876543210",
        email="majitar.phc@example.com",
    )

    phc2 = PrimaryHealthCentre(
        name="Rangpo Primary Health Centre",
        location="Rangpo, East Sikkim",
        contact_no="9876543211",
        email="rangpo.phc@example.com",
    )

    db.add_all([phc1, phc2])
    db.commit()
    db.refresh(phc1)
    db.refresh(phc2)

    asha1 = create_worker(
        "Demo ASHA Worker",
        "asha@example.com",
        "9000000001",
        "asha",
        phc1.phc_id,
        "Majitar Village",
        "SOS-MAJ-001",
    )

    asha2 = create_worker(
        "Second ASHA Worker",
        "asha2@example.com",
        "9000000002",
        "asha",
        phc1.phc_id,
        "Lower Majitar",
        "SOS-MAJ-002",
    )

    phc_admin = create_worker(
        "PHC Admin",
        "phcadmin@example.com",
        "9000000003",
        "phc_admin",
        phc1.phc_id,
        "Majitar PHC",
        "SOS-PHC-001",
        gender="Other",
    )

    supervisor = create_worker(
        "District Supervisor",
        "supervisor@example.com",
        "9000000004",
        "supervisor",
        phc1.phc_id,
        "East Sikkim District",
        "SOS-SUP-001",
        gender="Other",
    )

    b1 = Beneficiary(
        full_name="Sita Sharma",
        age=24,
        gender="Female",
        address="Majitar Ward 1",
        contact_no="9100000001",
        category="pregnant",
        asha_worker_id=asha1.worker_id,
    )

    b2 = Beneficiary(
        full_name="Anita Rai",
        age=27,
        gender="Female",
        address="Majitar Ward 2",
        contact_no="9100000002",
        category="pregnant",
        asha_worker_id=asha1.worker_id,
    )

    b3 = Beneficiary(
        full_name="Rohan Tamang",
        age=1,
        gender="Male",
        address="Majitar Ward 3",
        contact_no="9100000003",
        category="child",
        asha_worker_id=asha1.worker_id,
    )

    b4 = Beneficiary(
        full_name="Maya Lepcha",
        age=68,
        gender="Female",
        address="Majitar Ward 4",
        contact_no="9100000004",
        category="elderly",
        asha_worker_id=asha2.worker_id,
    )

    b5 = Beneficiary(
        full_name="Pema Bhutia",
        age=30,
        gender="Female",
        address="Lower Majitar Ward 2",
        contact_no="9100000005",
        category="general",
        asha_worker_id=asha2.worker_id,
    )

    db.add_all([b1, b2, b3, b4, b5])
    db.commit()

    for b in [b1, b2, b3, b4, b5]:
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
            created_by=asha1.worker_id,
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
            created_by=asha1.worker_id,
        ),
        ImmunizationRecord(
            beneficiary_id=b3.beneficiary_id,
            vaccine_name="Pentavalent",
            dose_number=2,
            scheduled_date=today + timedelta(days=5),
            status="scheduled",
            created_by=asha1.worker_id,
        ),
        ImmunizationRecord(
            beneficiary_id=b3.beneficiary_id,
            vaccine_name="OPV",
            dose_number=1,
            scheduled_date=today - timedelta(days=3),
            status="missed",
            created_by=asha1.worker_id,
        ),
        Appointment(
            beneficiary_id=b1.beneficiary_id,
            appointment_date=today + timedelta(days=2),
            appointment_time=time(10, 30),
            appointment_type="ANC Checkup",
            status="scheduled",
            notes="High BP follow-up required",
            created_by=asha1.worker_id,
        ),
        Appointment(
            beneficiary_id=b3.beneficiary_id,
            appointment_date=today + timedelta(days=5),
            appointment_time=time(11, 0),
            appointment_type="Immunization Visit",
            status="scheduled",
            notes="Pentavalent dose due",
            created_by=asha1.worker_id,
        ),
        Event(
            event_name="Village Nutrition Awareness Drive",
            event_type="nutrition",
            description="Nutrition and anemia awareness camp for mothers and children.",
            event_date=today + timedelta(days=7),
            event_time=time(12, 0),
            location="Majitar Community Hall",
            organizer_id=asha1.worker_id,
            status="upcoming",
        ),
        Event(
            event_name="Elderly Health Checkup Camp",
            event_type="checkup",
            description="Blood pressure and diabetes screening for elderly citizens.",
            event_date=today + timedelta(days=10),
            event_time=time(13, 0),
            location="Lower Majitar Community Centre",
            organizer_id=asha2.worker_id,
            status="upcoming",
        ),
        Notice(
            beneficiary_id=b1.beneficiary_id,
            sent_by=asha1.worker_id,
            message="Reminder: ANC checkup scheduled soon. Please visit PHC on time.",
            notice_date=today,
            status="sent",
            delivery_method="sms",
        ),
        MonthlyReport(
            month=today.strftime("%B"),
            year=today.year,
            total_patients=3,
            total_pregnancies=2,
            total_immunizations=2,
            total_appointments=2,
            total_events=1,
            generated_by=asha1.worker_id,
            phc_id=phc1.phc_id,
            status="submitted",
            notes="Demo monthly report for ASHA 1.",
        ),
        MonthlyReport(
            month=today.strftime("%B"),
            year=today.year,
            total_patients=2,
            total_pregnancies=0,
            total_immunizations=0,
            total_appointments=0,
            total_events=1,
            generated_by=asha2.worker_id,
            phc_id=phc1.phc_id,
            status="draft",
            notes="Demo monthly report for ASHA 2.",
        ),
        SOSAlert(
            worker_id=asha1.worker_id,
            latitude=27.1890,
            longitude=88.4970,
            status="resolved",
        ),
    ])

    db.commit()

    first_event = db.query(Event).filter(Event.organizer_id == asha1.worker_id).first()
    if first_event:
        db.add(EventParticipant(
            event_id=first_event.event_id,
            beneficiary_id=b1.beneficiary_id,
            attended=False,
        ))
        db.add(EventParticipant(
            event_id=first_event.event_id,
            beneficiary_id=b2.beneficiary_id,
            attended=False,
        ))
        db.commit()

    print("Seed complete")
    print("")
    print("Demo accounts:")
    print("ASHA 1      : asha@example.com / password123")
    print("ASHA 2      : asha2@example.com / password123")
    print("PHC Admin   : phcadmin@example.com / password123")
    print("Supervisor  : supervisor@example.com / password123")

finally:
    db.close()

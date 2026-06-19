from sqlalchemy import Column, Integer, String, Boolean, Enum, ForeignKey, Text, Float, Date, Time, TIMESTAMP, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.mysql import Base


class AshaWorker(Base):
    __tablename__ = "asha_workers"

    worker_id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, nullable=False, index=True)
    phone_no = Column(String(15), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    village = Column(String(150))
    address = Column(Text)
    age = Column(Integer)
    gender = Column(Enum("Male", "Female", "Other"), default="Female")
    qualification = Column(String(100))
    phc_id = Column(Integer, ForeignKey("primary_health_centres.phc_id"))
    is_active = Column(Boolean, default=True)
    role = Column(Enum("asha", "phc_admin", "supervisor"), default="asha")
    sos_id = Column(String(50), unique=True)
    created_at = Column(TIMESTAMP, server_default=func.now())

    phc = relationship("PrimaryHealthCentre", back_populates="workers")
    beneficiaries = relationship("Beneficiary", back_populates="asha_worker")
    events = relationship("Event", back_populates="organizer")
    monthly_reports = relationship("MonthlyReport", back_populates="generated_by_worker")
    sos_alerts = relationship("SOSAlert", back_populates="worker")


class PrimaryHealthCentre(Base):
    __tablename__ = "primary_health_centres"

    phc_id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    location = Column(String(300))
    contact_no = Column(String(15))
    email = Column(String(100))
    created_at = Column(TIMESTAMP, server_default=func.now())

    workers = relationship("AshaWorker", back_populates="phc")
    monthly_reports = relationship("MonthlyReport", back_populates="phc")


class Beneficiary(Base):
    __tablename__ = "beneficiaries"

    beneficiary_id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(150), nullable=False)
    age = Column(Integer)
    gender = Column(Enum("Male", "Female", "Other"))
    address = Column(Text)
    contact_no = Column(String(15))
    category = Column(Enum("pregnant", "child", "elderly", "general"), default="general")
    asha_worker_id = Column(Integer, ForeignKey("asha_workers.worker_id"), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    asha_worker = relationship("AshaWorker", back_populates="beneficiaries")
    records = relationship("Record", back_populates="beneficiary")
    pregnancy_records = relationship("PregnancyRecord", back_populates="beneficiary")
    immunization_records = relationship("ImmunizationRecord", back_populates="beneficiary")
    appointments = relationship("Appointment", back_populates="beneficiary")
    notices = relationship("Notice", back_populates="beneficiary")
    event_participants = relationship("EventParticipant", back_populates="beneficiary")


class Record(Base):
    __tablename__ = "records"

    record_id = Column(Integer, primary_key=True, index=True)
    beneficiary_id = Column(Integer, ForeignKey("beneficiaries.beneficiary_id"), nullable=False)
    record_date = Column(Date, nullable=False)
    type = Column(Enum("general", "pregnancy", "immunization", "sos", "checkup"), default="general")
    details = Column(Text)
    status = Column(Enum("active", "closed", "pending"), default="active")
    created_by = Column(Integer, ForeignKey("asha_workers.worker_id"), nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())

    beneficiary = relationship("Beneficiary", back_populates="records")
    creator = relationship("AshaWorker")


class PregnancyRecord(Base):
    __tablename__ = "pregnancy_records"

    pregnancy_id = Column(Integer, primary_key=True, index=True)
    beneficiary_id = Column(Integer, ForeignKey("beneficiaries.beneficiary_id"), nullable=False)
    registration_date = Column(Date, nullable=False)
    lmp_date = Column(Date)
    expected_delivery_date = Column(Date)
    hemoglobin_level = Column(Float)
    blood_pressure = Column(String(20))
    weight = Column(Float)
    status = Column(Enum("active", "delivered", "closed", "high_risk"), default="active")
    anc_count = Column(Integer, default=0)
    created_by = Column(Integer, ForeignKey("asha_workers.worker_id"), nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    beneficiary = relationship("Beneficiary", back_populates="pregnancy_records")
    creator = relationship("AshaWorker")


class ImmunizationRecord(Base):
    __tablename__ = "immunization_records"

    immunization_id = Column(Integer, primary_key=True, index=True)
    beneficiary_id = Column(Integer, ForeignKey("beneficiaries.beneficiary_id"), nullable=False)
    vaccine_name = Column(String(100), nullable=False)
    dose_number = Column(Integer, default=1)
    scheduled_date = Column(Date, nullable=False)
    given_date = Column(Date)
    status = Column(Enum("scheduled", "given", "missed", "postponed"), default="scheduled")
    created_by = Column(Integer, ForeignKey("asha_workers.worker_id"), nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())

    beneficiary = relationship("Beneficiary", back_populates="immunization_records")
    creator = relationship("AshaWorker")


class Appointment(Base):
    __tablename__ = "appointments"

    appointment_id = Column(Integer, primary_key=True, index=True)
    beneficiary_id = Column(Integer, ForeignKey("beneficiaries.beneficiary_id"), nullable=False)
    appointment_date = Column(Date, nullable=False)
    appointment_time = Column(Time)
    appointment_type = Column(String(100), nullable=False)
    status = Column(Enum("scheduled", "completed", "cancelled", "missed"), default="scheduled")
    notes = Column(Text)
    created_by = Column(Integer, ForeignKey("asha_workers.worker_id"), nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())

    beneficiary = relationship("Beneficiary", back_populates="appointments")
    creator = relationship("AshaWorker")


class Event(Base):
    __tablename__ = "events"

    event_id = Column(Integer, primary_key=True, index=True)
    event_name = Column(String(200), nullable=False)
    event_type = Column(Enum("vaccination", "nutrition", "awareness", "checkup", "other"), default="other")
    description = Column(Text)
    event_date = Column(Date, nullable=False)
    event_time = Column(Time)
    location = Column(String(300))
    organizer_id = Column(Integer, ForeignKey("asha_workers.worker_id"), nullable=False)
    status = Column(Enum("upcoming", "ongoing", "completed", "cancelled"), default="upcoming")
    created_at = Column(TIMESTAMP, server_default=func.now())

    organizer = relationship("AshaWorker", back_populates="events")
    participants = relationship("EventParticipant", back_populates="event")


class EventParticipant(Base):
    __tablename__ = "event_participants"
    __table_args__ = (UniqueConstraint("event_id", "beneficiary_id", name="uq_event_beneficiary"),)

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.event_id"), nullable=False)
    beneficiary_id = Column(Integer, ForeignKey("beneficiaries.beneficiary_id"), nullable=False)
    attended = Column(Boolean, default=False)

    event = relationship("Event", back_populates="participants")
    beneficiary = relationship("Beneficiary", back_populates="event_participants")


class Notice(Base):
    __tablename__ = "notices"

    notice_id = Column(Integer, primary_key=True, index=True)
    beneficiary_id = Column(Integer, ForeignKey("beneficiaries.beneficiary_id"), nullable=False)
    sent_by = Column(Integer, ForeignKey("asha_workers.worker_id"), nullable=False)
    message = Column(Text, nullable=False)
    notice_date = Column(Date)
    status = Column(Enum("sent", "pending", "failed"), default="pending")
    delivery_method = Column(Enum("sms", "push", "both"), default="sms")
    created_at = Column(TIMESTAMP, server_default=func.now())

    beneficiary = relationship("Beneficiary", back_populates="notices")
    sender = relationship("AshaWorker")


class MonthlyReport(Base):
    __tablename__ = "monthly_reports"

    report_id = Column(Integer, primary_key=True, index=True)
    month = Column(String(20), nullable=False)
    year = Column(Integer, nullable=False)
    total_patients = Column(Integer, default=0)
    total_pregnancies = Column(Integer, default=0)
    total_immunizations = Column(Integer, default=0)
    total_appointments = Column(Integer, default=0)
    total_events = Column(Integer, default=0)
    generated_by = Column(Integer, ForeignKey("asha_workers.worker_id"), nullable=False)
    phc_id = Column(Integer, ForeignKey("primary_health_centres.phc_id"))
    status = Column(Enum("draft", "submitted", "approved"), default="draft")
    notes = Column(Text)
    created_at = Column(TIMESTAMP, server_default=func.now())

    generated_by_worker = relationship("AshaWorker", back_populates="monthly_reports")
    phc = relationship("PrimaryHealthCentre", back_populates="monthly_reports")


class SOSAlert(Base):
    __tablename__ = "sos_alerts"

    sos_id = Column(Integer, primary_key=True, index=True)
    worker_id = Column(Integer, ForeignKey("asha_workers.worker_id"), nullable=False)
    latitude = Column(Float)
    longitude = Column(Float)
    triggered_at = Column(TIMESTAMP, server_default=func.now())
    resolved_at = Column(TIMESTAMP, nullable=True)
    status = Column(Enum("active", "resolved"), default="active")

    worker = relationship("AshaWorker", back_populates="sos_alerts")

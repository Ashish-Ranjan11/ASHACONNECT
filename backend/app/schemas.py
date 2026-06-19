from datetime import date, time, datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict


class LoginRequest(BaseModel):
    email: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    worker: dict


class AshaWorkerCreate(BaseModel):
    name: str
    email: str
    phone_no: str
    password: str
    village: Optional[str] = None
    address: Optional[str] = None
    age: Optional[int] = None
    gender: str = "Female"
    qualification: Optional[str] = None
    phc_id: Optional[int] = None
    role: str = "asha"
    sos_id: Optional[str] = None


class AshaWorkerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    worker_id: int
    name: str
    email: str
    phone_no: str
    village: Optional[str] = None
    role: str
    sos_id: Optional[str] = None


class PHCCreate(BaseModel):
    name: str
    location: Optional[str] = None
    contact_no: Optional[str] = None
    email: Optional[str] = None


class PHCOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    phc_id: int
    name: str
    location: Optional[str] = None
    contact_no: Optional[str] = None
    email: Optional[str] = None


class BeneficiaryCreate(BaseModel):
    full_name: str
    age: Optional[int] = None
    gender: Optional[str] = None
    address: Optional[str] = None
    contact_no: Optional[str] = None
    category: str = "general"


class BeneficiaryUpdate(BaseModel):
    full_name: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    address: Optional[str] = None
    contact_no: Optional[str] = None
    category: Optional[str] = None
    is_active: Optional[bool] = None


class BeneficiaryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    beneficiary_id: int
    full_name: str
    age: Optional[int] = None
    gender: Optional[str] = None
    address: Optional[str] = None
    contact_no: Optional[str] = None
    category: str
    asha_worker_id: int
    is_active: bool


class RecordCreate(BaseModel):
    beneficiary_id: int
    record_date: date
    type: str = "general"
    details: Optional[str] = None
    status: str = "active"


class RecordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    record_id: int
    beneficiary_id: int
    record_date: date
    type: str
    details: Optional[str] = None
    status: str
    created_by: int


class PregnancyRecordCreate(BaseModel):
    beneficiary_id: int
    registration_date: date
    lmp_date: Optional[date] = None
    expected_delivery_date: Optional[date] = None
    hemoglobin_level: Optional[float] = None
    blood_pressure: Optional[str] = None
    weight: Optional[float] = None
    status: str = "active"
    anc_count: int = 0


class PregnancyRecordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    pregnancy_id: int
    beneficiary_id: int
    registration_date: date
    lmp_date: Optional[date] = None
    expected_delivery_date: Optional[date] = None
    hemoglobin_level: Optional[float] = None
    blood_pressure: Optional[str] = None
    weight: Optional[float] = None
    status: str
    anc_count: int
    created_by: int


class ImmunizationRecordCreate(BaseModel):
    beneficiary_id: int
    vaccine_name: str
    dose_number: int = 1
    scheduled_date: date
    given_date: Optional[date] = None
    status: str = "scheduled"


class ImmunizationRecordUpdate(BaseModel):
    given_date: Optional[date] = None
    status: Optional[str] = None
    scheduled_date: Optional[date] = None


class ImmunizationRecordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    immunization_id: int
    beneficiary_id: int
    vaccine_name: str
    dose_number: int
    scheduled_date: date
    given_date: Optional[date] = None
    status: str
    created_by: int


class AppointmentCreate(BaseModel):
    beneficiary_id: int
    appointment_date: date
    appointment_time: Optional[time] = None
    appointment_type: str
    status: str = "scheduled"
    notes: Optional[str] = None


class AppointmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    appointment_id: int
    beneficiary_id: int
    appointment_date: date
    appointment_time: Optional[time] = None
    appointment_type: str
    status: str
    notes: Optional[str] = None
    created_by: int


class EventCreate(BaseModel):
    event_name: str
    event_type: str = "other"
    description: Optional[str] = None
    event_date: date
    event_time: Optional[time] = None
    location: Optional[str] = None
    status: str = "upcoming"


class EventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    event_id: int
    event_name: str
    event_type: str
    description: Optional[str] = None
    event_date: date
    event_time: Optional[time] = None
    location: Optional[str] = None
    organizer_id: int
    status: str


class EventParticipantCreate(BaseModel):
    beneficiary_id: int


class NoticeCreate(BaseModel):
    beneficiary_id: int
    message: str
    notice_date: Optional[date] = None
    delivery_method: str = "sms"


class NoticeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    notice_id: int
    beneficiary_id: int
    sent_by: int
    message: str
    notice_date: Optional[date] = None
    status: str
    delivery_method: str


class MonthlyReportCreate(BaseModel):
    month: str
    year: int
    status: str = "draft"
    notes: Optional[str] = None


class MonthlyReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    report_id: int
    month: str
    year: int
    total_patients: int
    total_pregnancies: int
    total_immunizations: int
    total_appointments: int
    total_events: int
    generated_by: int
    phc_id: Optional[int] = None
    status: str
    notes: Optional[str] = None


class SOSCreate(BaseModel):
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class SOSOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    sos_id: int
    worker_id: int
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    triggered_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    status: str

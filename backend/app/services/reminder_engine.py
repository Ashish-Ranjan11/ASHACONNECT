from datetime import date, datetime, timedelta
import re

from sqlalchemy import text, bindparam
from sqlalchemy.orm import Session

from app.models import AshaWorker
from app.deps import visible_worker_ids
from app.security import role_value


def now_iso():
    return datetime.utcnow().isoformat()


def clean_phone(phone):
    phone = re.sub(r"\D+", "", str(phone or ""))
    if not phone:
        return ""
    if len(phone) == 10:
        return "91" + phone
    return phone


def table_exists(db: Session, table_name: str) -> bool:
    row = db.execute(
        text("SELECT name FROM sqlite_master WHERE type='table' AND name=:name"),
        {"name": table_name},
    ).first()
    return bool(row)


def ensure_tables(db: Session):
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS outbound_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel TEXT NOT NULL,
                recipient_name TEXT DEFAULT '',
                recipient_phone TEXT DEFAULT '',
                message TEXT NOT NULL,
                attachment_path TEXT DEFAULT '',
                related_report_uid TEXT DEFAULT '',
                status TEXT NOT NULL DEFAULT 'queued',
                delivery_mode TEXT NOT NULL DEFAULT 'mock',
                created_by INTEGER,
                created_at TEXT NOT NULL,
                sent_at TEXT
            )
            """
        )
    )

    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS reminder_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                worker_id INTEGER NOT NULL,
                reminder_type TEXT NOT NULL,
                enabled INTEGER DEFAULT 1,
                one_day_before INTEGER DEFAULT 1,
                few_hours_before INTEGER DEFAULT 1,
                hours_before INTEGER DEFAULT 3,
                channel TEXT DEFAULT 'whatsapp',
                template TEXT DEFAULT '',
                updated_at TEXT NOT NULL
            )
            """
        )
    )

    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS reminder_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_type TEXT NOT NULL,
                source_id TEXT NOT NULL,
                beneficiary_id INTEGER,
                reminder_stage TEXT NOT NULL,
                scheduled_for TEXT NOT NULL,
                message_id INTEGER,
                created_at TEXT NOT NULL,
                UNIQUE(source_type, source_id, reminder_stage)
            )
            """
        )
    )

    db.commit()


def seed_default_settings(db: Session, worker_id: int):
    existing = db.execute(
        text("SELECT COUNT(*) FROM reminder_settings WHERE worker_id=:worker_id"),
        {"worker_id": worker_id},
    ).scalar()

    if existing:
        return

    defaults = [
        (
            "appointment",
            "Namaste {name}, reminder: you have a healthcare appointment on {date}. Please be available.",
        ),
        (
            "immunization",
            "Namaste {name}, reminder: vaccination is due on {date}. Please visit as advised.",
        ),
        (
            "pregnancy",
            "Namaste {name}, reminder: ANC/PNC follow-up is due on {date}. Please contact your ASHA worker.",
        ),
    ]

    for reminder_type, template in defaults:
        db.execute(
            text(
                """
                INSERT INTO reminder_settings
                (worker_id, reminder_type, enabled, one_day_before, few_hours_before,
                 hours_before, channel, template, updated_at)
                VALUES
                (:worker_id, :reminder_type, 1, 1, 1, 3, 'whatsapp', :template, :updated_at)
                """
            ),
            {
                "worker_id": worker_id,
                "reminder_type": reminder_type,
                "template": template,
                "updated_at": now_iso(),
            },
        )

    db.commit()


def get_settings(db: Session, worker_id: int):
    ensure_tables(db)
    seed_default_settings(db, worker_id)

    rows = db.execute(
        text(
            """
            SELECT reminder_type, enabled, one_day_before, few_hours_before,
                   hours_before, channel, template
            FROM reminder_settings
            WHERE worker_id=:worker_id
            """
        ),
        {"worker_id": worker_id},
    ).mappings().all()

    return {row["reminder_type"]: dict(row) for row in rows if row["enabled"]}


def format_message(template, name, due_date, reminder_type):
    if not template:
        template = "Namaste {name}, reminder: your {type} is scheduled on {date}."

    return (
        template.replace("{name}", name or "beneficiary")
        .replace("{date}", str(due_date or "scheduled date"))
        .replace("{type}", reminder_type)
    )


def queue_message(
    db: Session,
    current: AshaWorker,
    recipient_name: str,
    recipient_phone: str,
    message: str,
):
    db.execute(
        text(
            """
            INSERT INTO outbound_messages
            (channel, recipient_name, recipient_phone, message, attachment_path,
             related_report_uid, status, delivery_mode, created_by, created_at, sent_at)
            VALUES
            ('whatsapp', :recipient_name, :recipient_phone, :message, '',
             '', 'queued', 'mock', :created_by, :created_at, NULL)
            """
        ),
        {
            "recipient_name": recipient_name or "",
            "recipient_phone": clean_phone(recipient_phone),
            "message": message,
            "created_by": current.worker_id,
            "created_at": now_iso(),
        },
    )

    db.commit()

    msg_id = db.execute(text("SELECT last_insert_rowid()")).scalar()
    return msg_id


def create_reminder_event(
    db: Session,
    current: AshaWorker,
    source_type: str,
    source_id: str,
    beneficiary_id: int,
    beneficiary_name: str,
    phone: str,
    due_date,
    reminder_stage: str,
    template: str,
):
    ensure_tables(db)

    existing = db.execute(
        text(
            """
            SELECT id FROM reminder_events
            WHERE source_type=:source_type
              AND source_id=:source_id
              AND reminder_stage=:reminder_stage
            """
        ),
        {
            "source_type": source_type,
            "source_id": str(source_id),
            "reminder_stage": reminder_stage,
        },
    ).first()

    if existing:
        return False

    message = format_message(template, beneficiary_name, due_date, source_type)

    msg_id = queue_message(
        db,
        current,
        recipient_name=beneficiary_name,
        recipient_phone=phone,
        message=message,
    )

    db.execute(
        text(
            """
            INSERT INTO reminder_events
            (source_type, source_id, beneficiary_id, reminder_stage, scheduled_for,
             message_id, created_at)
            VALUES
            (:source_type, :source_id, :beneficiary_id, :reminder_stage, :scheduled_for,
             :message_id, :created_at)
            """
        ),
        {
            "source_type": source_type,
            "source_id": str(source_id),
            "beneficiary_id": beneficiary_id,
            "reminder_stage": reminder_stage,
            "scheduled_for": str(due_date),
            "message_id": msg_id,
            "created_at": now_iso(),
        },
    )

    db.commit()
    return True


def scan_appointments(db: Session, current: AshaWorker, worker_ids, target_date, stage, template):
    if not table_exists(db, "appointments"):
        return 0

    rows = db.execute(
        text(
            """
            SELECT a.appointment_id, a.beneficiary_id, a.appointment_date,
                   b.full_name, b.contact_no
            FROM appointments a
            JOIN beneficiaries b ON b.beneficiary_id = a.beneficiary_id
            WHERE b.asha_worker_id IN :worker_ids
              AND date(a.appointment_date) = :target_date
              AND lower(COALESCE(a.status, 'scheduled')) NOT IN ('completed', 'cancelled')
            """
        ).bindparams(bindparam("worker_ids", expanding=True)),
        {
            "worker_ids": worker_ids,
            "target_date": target_date.isoformat(),
        },
    ).mappings().all()

    created = 0

    for row in rows:
        if create_reminder_event(
            db,
            current,
            "appointment",
            row["appointment_id"],
            row["beneficiary_id"],
            row["full_name"],
            row["contact_no"],
            row["appointment_date"],
            stage,
            template,
        ):
            created += 1

    return created


def scan_immunizations(db: Session, current: AshaWorker, worker_ids, target_date, stage, template):
    if not table_exists(db, "immunization_records"):
        return 0

    rows = db.execute(
        text(
            """
            SELECT i.immunization_id, i.beneficiary_id, i.scheduled_date,
                   i.vaccine_name, b.full_name, b.contact_no
            FROM immunization_records i
            JOIN beneficiaries b ON b.beneficiary_id = i.beneficiary_id
            WHERE b.asha_worker_id IN :worker_ids
              AND date(i.scheduled_date) = :target_date
              AND lower(COALESCE(i.status, 'scheduled')) NOT IN ('given', 'completed', 'cancelled')
            """
        ).bindparams(bindparam("worker_ids", expanding=True)),
        {
            "worker_ids": worker_ids,
            "target_date": target_date.isoformat(),
        },
    ).mappings().all()

    created = 0

    for row in rows:
        if create_reminder_event(
            db,
            current,
            "immunization",
            row["immunization_id"],
            row["beneficiary_id"],
            row["full_name"],
            row["contact_no"],
            row["scheduled_date"],
            stage,
            template,
        ):
            created += 1

    return created


def scan_pregnancy(db: Session, current: AshaWorker, worker_ids, target_date, stage, template):
    if not table_exists(db, "pregnancy_records"):
        return 0

    rows = db.execute(
        text(
            """
            SELECT p.pregnancy_id, p.beneficiary_id, p.expected_delivery_date,
                   b.full_name, b.contact_no
            FROM pregnancy_records p
            JOIN beneficiaries b ON b.beneficiary_id = p.beneficiary_id
            WHERE b.asha_worker_id IN :worker_ids
              AND date(p.expected_delivery_date) = :target_date
              AND lower(COALESCE(p.status, 'active')) NOT IN ('closed', 'completed', 'cancelled')
            """
        ).bindparams(bindparam("worker_ids", expanding=True)),
        {
            "worker_ids": worker_ids,
            "target_date": target_date.isoformat(),
        },
    ).mappings().all()

    created = 0

    for row in rows:
        if create_reminder_event(
            db,
            current,
            "pregnancy",
            row["pregnancy_id"],
            row["beneficiary_id"],
            row["full_name"],
            row["contact_no"],
            row["expected_delivery_date"],
            stage,
            template,
        ):
            created += 1

    return created


def run_reminders_for_current_user(db: Session, current: AshaWorker):
    ensure_tables(db)

    worker_ids = visible_worker_ids(db, current)

    if not worker_ids:
        return {
            "message": "Reminder scan completed",
            "created_messages": 0,
            "details": {},
        }

    settings = get_settings(db, current.worker_id)

    today = date.today()
    tomorrow = today + timedelta(days=1)

    created = 0
    details = {
        "appointment": 0,
        "immunization": 0,
        "pregnancy": 0,
        "today": today.isoformat(),
        "tomorrow": tomorrow.isoformat(),
    }

    appointment = settings.get("appointment")
    if appointment:
        if appointment.get("one_day_before"):
            count = scan_appointments(
                db,
                current,
                worker_ids,
                tomorrow,
                "one_day_before",
                appointment.get("template") or "",
            )
            created += count
            details["appointment"] += count

        if appointment.get("few_hours_before"):
            count = scan_appointments(
                db,
                current,
                worker_ids,
                today,
                "few_hours_before",
                appointment.get("template") or "",
            )
            created += count
            details["appointment"] += count

    immunization = settings.get("immunization")
    if immunization:
        if immunization.get("one_day_before"):
            count = scan_immunizations(
                db,
                current,
                worker_ids,
                tomorrow,
                "one_day_before",
                immunization.get("template") or "",
            )
            created += count
            details["immunization"] += count

        if immunization.get("few_hours_before"):
            count = scan_immunizations(
                db,
                current,
                worker_ids,
                today,
                "few_hours_before",
                immunization.get("template") or "",
            )
            created += count
            details["immunization"] += count

    pregnancy = settings.get("pregnancy")
    if pregnancy:
        if pregnancy.get("one_day_before"):
            count = scan_pregnancy(
                db,
                current,
                worker_ids,
                tomorrow,
                "one_day_before",
                pregnancy.get("template") or "",
            )
            created += count
            details["pregnancy"] += count

        if pregnancy.get("few_hours_before"):
            count = scan_pregnancy(
                db,
                current,
                worker_ids,
                today,
                "few_hours_before",
                pregnancy.get("template") or "",
            )
            created += count
            details["pregnancy"] += count

    care_event_count = 0
    care_event_count += scan_care_events(db, current, worker_ids, tomorrow, "one_day_before")
    care_event_count += scan_care_events(db, current, worker_ids, today, "few_hours_before")

    created += care_event_count
    details["care_events"] = care_event_count

    return {
        "message": "Reminder scan completed",
        "created_messages": created,
        "details": details,
    }


def run_reminders_for_all_asha(db: Session):
    ensure_tables(db)

    workers = db.query(AshaWorker).all()

    total_created = 0
    scanned_workers = 0
    worker_results = []

    for worker in workers:
        if role_value(worker.role) != "asha":
            continue

        if hasattr(worker, "is_active") and not worker.is_active:
            continue

        scanned_workers += 1

        try:
            result = run_reminders_for_current_user(db, worker)
            total_created += result.get("created_messages", 0)
            worker_results.append(
                {
                    "worker_id": worker.worker_id,
                    "name": worker.name,
                    "created_messages": result.get("created_messages", 0),
                }
            )
        except Exception as exc:
            worker_results.append(
                {
                    "worker_id": worker.worker_id,
                    "name": worker.name,
                    "error": str(exc),
                }
            )

    return {
        "message": "Automatic reminder scheduler completed",
        "scanned_workers": scanned_workers,
        "created_messages": total_created,
        "workers": worker_results,
    }



def ensure_care_events_table(db: Session):
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS care_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_uid TEXT UNIQUE NOT NULL,
                event_type TEXT NOT NULL,
                title TEXT NOT NULL,
                beneficiary_id INTEGER NOT NULL,
                worker_id INTEGER NOT NULL,
                scheduled_at TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'scheduled',
                priority TEXT DEFAULT 'normal',
                notes TEXT DEFAULT '',
                reminder_enabled INTEGER DEFAULT 1,
                created_by INTEGER,
                created_at TEXT NOT NULL
            )
            """
        )
    )
    db.commit()


def scan_care_events(db: Session, current: AshaWorker, worker_ids, target_date, stage):
    ensure_care_events_table(db)

    rows = db.execute(
        text(
            """
            SELECT e.event_uid, e.event_type, e.title, e.beneficiary_id,
                   e.scheduled_at, b.full_name, b.contact_no
            FROM care_events e
            JOIN beneficiaries b ON b.beneficiary_id = e.beneficiary_id
            WHERE e.worker_id IN :worker_ids
              AND date(e.scheduled_at) = :target_date
              AND lower(COALESCE(e.status, 'scheduled')) NOT IN ('completed', 'cancelled')
              AND COALESCE(e.reminder_enabled, 1) = 1
            """
        ).bindparams(bindparam("worker_ids", expanding=True)),
        {
            "worker_ids": worker_ids,
            "target_date": target_date.isoformat(),
        },
    ).mappings().all()

    created = 0

    for row in rows:
        template = (
            f"Namaste {{name}}, reminder: {row['title']} is scheduled on {{date}}. "
            f"Please be available. - ASHA CONNECT"
        )

        if create_reminder_event(
            db,
            current,
            row["event_type"] or "care_event",
            row["event_uid"],
            row["beneficiary_id"],
            row["full_name"],
            row["contact_no"],
            row["scheduled_at"],
            stage,
            template,
        ):
            created += 1

    return created

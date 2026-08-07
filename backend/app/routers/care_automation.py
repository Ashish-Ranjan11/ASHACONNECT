import asyncio
import os
from datetime import datetime, date, timedelta
from pathlib import Path
import re
import uuid

from fastapi import APIRouter, Depends, HTTPException, Body
from fastapi.responses import FileResponse
from sqlalchemy import text, bindparam
from sqlalchemy.orm import Session

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

from app.db.mysql import get_db, SessionLocal
from app.deps import get_current_worker, visible_worker_ids
from app.models import AshaWorker, Beneficiary
from app.security import audit_log, role_value
from app.services.reminder_engine import run_reminders_for_current_user, run_reminders_for_all_asha

router = APIRouter(prefix="/api/care-automation", tags=["Care Automation"])

BASE_DIR = Path(__file__).resolve().parents[2]
REPORT_DIR = BASE_DIR / "generated_reports"
REPORT_DIR.mkdir(parents=True, exist_ok=True)


def now_iso():
    return datetime.utcnow().isoformat()


def safe_filename(value: str):
    value = re.sub(r"[^A-Za-z0-9_-]+", "_", str(value or "report"))
    return value.strip("_")[:80] or "report"


def create_tables(db: Session):
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS generated_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                report_uid TEXT UNIQUE NOT NULL,
                report_type TEXT NOT NULL,
                scope TEXT NOT NULL,
                title TEXT NOT NULL,
                file_path TEXT NOT NULL,
                beneficiary_id INTEGER,
                family_name TEXT,
                generated_by INTEGER,
                generated_for TEXT,
                notes TEXT DEFAULT '',
                created_at TEXT NOT NULL
            )
            """
        )
    )

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


def clean_phone(phone):
    phone = re.sub(r"\D+", "", str(phone or ""))
    if not phone:
        return ""
    if len(phone) == 10:
        return "91" + phone
    return phone


def beneficiary_json(item: Beneficiary):
    return {
        "beneficiary_id": item.beneficiary_id,
        "name": item.full_name,
        "age": item.age,
        "gender": item.gender,
        "category": item.category,
        "family_name": item.address,
        "phone": item.contact_no,
        "education": getattr(item, "education", "") or "",
        "occupation_type": getattr(item, "occupation_type", "") or "",
        "marital_status": getattr(item, "marital_status", "") or "",
        "religion": getattr(item, "religion", "") or "",
    }


def get_visible_beneficiaries(db: Session, current: AshaWorker):
    ids = visible_worker_ids(db, current)
    query = db.query(Beneficiary)

    if hasattr(Beneficiary, "asha_worker_id"):
        query = query.filter(Beneficiary.asha_worker_id.in_(ids))

    return query.order_by(Beneficiary.beneficiary_id.desc())


def get_beneficiary_or_403(db: Session, current: AshaWorker, beneficiary_id: int):
    ids = visible_worker_ids(db, current)
    item = db.get(Beneficiary, beneficiary_id)

    if not item:
        raise HTTPException(status_code=404, detail="Beneficiary not found")

    if hasattr(item, "asha_worker_id") and item.asha_worker_id not in ids:
        raise HTTPException(status_code=403, detail="You do not have access to this beneficiary")

    return item


def get_family_members(db: Session, current: AshaWorker, family_name: str):
    ids = visible_worker_ids(db, current)
    query = db.query(Beneficiary).filter(Beneficiary.address == family_name)

    if hasattr(Beneficiary, "asha_worker_id"):
        query = query.filter(Beneficiary.asha_worker_id.in_(ids))

    return query.order_by(Beneficiary.age.desc()).all()


def build_report_pdf(title, subtitle, sections, filename):
    path = REPORT_DIR / filename

    doc = SimpleDocTemplate(
        str(path),
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36,
    )

    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="ReportTitle",
            parent=styles["Title"],
            fontSize=22,
            leading=26,
            textColor=colors.HexColor("#061527"),
            spaceAfter=10,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Subtle",
            parent=styles["BodyText"],
            fontSize=9,
            textColor=colors.HexColor("#66758c"),
            leading=13,
        )
    )
    styles.add(
        ParagraphStyle(
            name="SectionHeading",
            parent=styles["Heading2"],
            fontSize=14,
            textColor=colors.HexColor("#0f766e"),
            spaceBefore=12,
            spaceAfter=8,
        )
    )

    story = []

    story.append(Paragraph("ASHA CONNECT", styles["Subtle"]))
    story.append(Paragraph(title, styles["ReportTitle"]))
    story.append(Paragraph(subtitle, styles["Subtle"]))
    story.append(Spacer(1, 0.18 * inch))

    for section in sections:
        story.append(Paragraph(section["heading"], styles["SectionHeading"]))

        if section.get("paragraph"):
            story.append(Paragraph(section["paragraph"], styles["BodyText"]))
            story.append(Spacer(1, 0.12 * inch))

        if section.get("table"):
            table = Table(section["table"], hAlign="LEFT")
            table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eef4f8")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#061527")),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, -1), 8),
                        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#dbe7f0")),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fbfc")]),
                        ("LEFTPADDING", (0, 0), (-1, -1), 6),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                        ("TOPPADDING", (0, 0), (-1, -1), 6),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ]
                )
            )
            story.append(table)
            story.append(Spacer(1, 0.12 * inch))

    story.append(Spacer(1, 0.24 * inch))
    story.append(
        Paragraph(
            "Generated digitally by ASHA CONNECT. This report is for field follow-up and PHC review support.",
            styles["Subtle"],
        )
    )

    doc.build(story)
    return path


def insert_report(
    db,
    report_uid,
    report_type,
    scope,
    title,
    file_path,
    current,
    beneficiary_id=None,
    family_name=None,
    generated_for="beneficiary",
    notes="",
):
    db.execute(
        text(
            """
            INSERT INTO generated_reports
            (report_uid, report_type, scope, title, file_path, beneficiary_id, family_name,
             generated_by, generated_for, notes, created_at)
            VALUES
            (:report_uid, :report_type, :scope, :title, :file_path, :beneficiary_id, :family_name,
             :generated_by, :generated_for, :notes, :created_at)
            """
        ),
        {
            "report_uid": report_uid,
            "report_type": report_type,
            "scope": scope,
            "title": title,
            "file_path": str(file_path),
            "beneficiary_id": beneficiary_id,
            "family_name": family_name,
            "generated_by": current.worker_id,
            "generated_for": generated_for,
            "notes": notes or "",
            "created_at": now_iso(),
        },
    )
    db.commit()


def queue_message(
    db,
    current,
    recipient_name,
    recipient_phone,
    message,
    attachment_path="",
    related_report_uid="",
    channel="whatsapp",
):
    db.execute(
        text(
            """
            INSERT INTO outbound_messages
            (channel, recipient_name, recipient_phone, message, attachment_path,
             related_report_uid, status, delivery_mode, created_by, created_at, sent_at)
            VALUES
            (:channel, :recipient_name, :recipient_phone, :message, :attachment_path,
             :related_report_uid, 'queued', 'mock', :created_by, :created_at, NULL)
            """
        ),
        {
            "channel": channel,
            "recipient_name": recipient_name or "",
            "recipient_phone": clean_phone(recipient_phone),
            "message": message,
            "attachment_path": str(attachment_path or ""),
            "related_report_uid": related_report_uid or "",
            "created_by": current.worker_id,
            "created_at": now_iso(),
        },
    )
    db.commit()


def report_url(report_uid):
    return f"/api/care-automation/reports/{report_uid}/download"


@router.on_event("startup")
def startup():
    # Created also inside routes to be safe with reload order.
    pass


@router.get("/beneficiaries")
def automation_beneficiaries(
    db: Session = Depends(get_db),
    current: AshaWorker = Depends(get_current_worker),
):
    create_tables(db)
    rows = get_visible_beneficiaries(db, current).all()
    return [beneficiary_json(row) for row in rows]


@router.get("/families")
def automation_families(
    db: Session = Depends(get_db),
    current: AshaWorker = Depends(get_current_worker),
):
    create_tables(db)
    rows = get_visible_beneficiaries(db, current).all()

    families = {}
    for item in rows:
        family = item.address or "Unassigned Family"
        families.setdefault(
            family,
            {
                "family_name": family,
                "members": 0,
                "phones": set(),
            },
        )
        families[family]["members"] += 1
        if item.contact_no:
            families[family]["phones"].add(item.contact_no)

    result = []
    for value in families.values():
        result.append(
            {
                "family_name": value["family_name"],
                "members": value["members"],
                "phones": list(value["phones"]),
            }
        )

    return sorted(result, key=lambda item: item["family_name"])


@router.post("/reports/individual")
def generate_individual_report(
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    current: AshaWorker = Depends(get_current_worker),
):
    create_tables(db)

    beneficiary_id = int(payload.get("beneficiary_id") or 0)
    report_type = str(payload.get("report_type") or "routine").lower()
    notes = str(payload.get("notes") or "")
    send_to_beneficiary = bool(payload.get("send_to_beneficiary", False))

    item = get_beneficiary_or_403(db, current, beneficiary_id)

    title = f"{item.full_name} - {report_type.title()} Health Report"
    subtitle = f"Generated on {date.today().isoformat()} by {current.name}"

    sections = [
        {
            "heading": "Beneficiary Profile",
            "table": [
                ["Field", "Value"],
                ["Name", item.full_name or "N/A"],
                ["Age", str(item.age or "N/A")],
                ["Gender", item.gender or "N/A"],
                ["Category", item.category or "N/A"],
                ["Family", item.address or "N/A"],
                ["Phone", item.contact_no or "N/A"],
            ],
        },
        {
            "heading": "ASHA Register Details",
            "table": [
                ["Field", "Value"],
                ["Education", getattr(item, "education", "") or "N/A"],
                ["Occupation", getattr(item, "occupation_type", "") or "N/A"],
                ["Marital Status", getattr(item, "marital_status", "") or "N/A"],
                ["Religion", getattr(item, "religion", "") or "N/A"],
                ["Babies in Family", str(getattr(item, "family_baby_count", "") or "N/A")],
                ["Last Baby Birth Date", str(getattr(item, "last_baby_birth_date", "") or "N/A")],
            ],
        },
        {
            "heading": "ASHA / Doctor Notes",
            "paragraph": notes or "No additional notes were added.",
        },
        {
            "heading": "Recommended Follow-up",
            "paragraph": "Attend scheduled appointments, complete pending vaccination or ANC/PNC follow-ups, and contact the ASHA worker for any urgent symptoms.",
        },
    ]

    report_uid = str(uuid.uuid4())
    filename = f"individual_{safe_filename(item.full_name)}_{report_uid[:8]}.pdf"
    file_path = build_report_pdf(title, subtitle, sections, filename)

    insert_report(
        db,
        report_uid=report_uid,
        report_type=report_type,
        scope="individual",
        title=title,
        file_path=file_path,
        current=current,
        beneficiary_id=item.beneficiary_id,
        family_name=item.address,
        generated_for="beneficiary",
        notes=notes,
    )

    if send_to_beneficiary:
        message = (
            f"Namaste {item.full_name}, your {report_type} health report has been generated "
            f"by ASHA CONNECT. Please review it with your ASHA worker/doctor if required."
        )
        queue_message(
            db,
            current,
            recipient_name=item.full_name,
            recipient_phone=item.contact_no,
            message=message,
            attachment_path=file_path,
            related_report_uid=report_uid,
        )

    audit_log(
        db,
        "staff",
        current.worker_id,
        role_value(current.role),
        "GENERATE_INDIVIDUAL_REPORT",
        "Beneficiary",
        item.beneficiary_id,
        title,
    )

    return {
        "message": "Individual report generated successfully",
        "report_uid": report_uid,
        "download_url": report_url(report_uid),
        "sent_to_beneficiary": send_to_beneficiary,
    }


@router.post("/reports/family")
def generate_family_report(
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    current: AshaWorker = Depends(get_current_worker),
):
    create_tables(db)

    family_name = str(payload.get("family_name") or "").strip()
    report_type = str(payload.get("report_type") or "monthly").lower()
    notes = str(payload.get("notes") or "")
    send_to_family = bool(payload.get("send_to_family", False))
    send_copy_to_phc = bool(payload.get("send_copy_to_phc", False))

    if not family_name:
        raise HTTPException(status_code=400, detail="family_name is required")

    members = get_family_members(db, current, family_name)

    if not members:
        raise HTTPException(status_code=404, detail="No visible members found for this family")

    title = f"{family_name} - {report_type.title()} Family Health Report"
    subtitle = f"Generated on {date.today().isoformat()} by {current.name}"

    member_table = [["Name", "Age", "Gender", "Category", "Phone", "Education", "Occupation"]]
    for member in members:
        member_table.append(
            [
                member.full_name or "N/A",
                str(member.age or "N/A"),
                member.gender or "N/A",
                member.category or "N/A",
                member.contact_no or "N/A",
                getattr(member, "education", "") or "N/A",
                getattr(member, "occupation_type", "") or "N/A",
            ]
        )

    sections = [
        {
            "heading": "Family Summary",
            "table": [
                ["Field", "Value"],
                ["Family Name", family_name],
                ["Total Members", str(len(members))],
                ["Generated By", current.name],
                ["Report Type", report_type.title()],
            ],
        },
        {
            "heading": "Family Members",
            "table": member_table,
        },
        {
            "heading": "Family Care Notes",
            "paragraph": notes or "No additional family notes were added.",
        },
        {
            "heading": "Recommended ASHA Follow-up",
            "paragraph": "Review pending immunization, pregnancy follow-up, elderly care needs, appointments and emergency risks for this household.",
        },
    ]

    report_uid = str(uuid.uuid4())
    filename = f"family_{safe_filename(family_name)}_{report_uid[:8]}.pdf"
    file_path = build_report_pdf(title, subtitle, sections, filename)

    insert_report(
        db,
        report_uid=report_uid,
        report_type=report_type,
        scope="family",
        title=title,
        file_path=file_path,
        current=current,
        family_name=family_name,
        generated_for="family_and_phc" if send_copy_to_phc else "family",
        notes=notes,
    )

    if send_to_family:
        phones = []
        for member in members:
            if member.contact_no and member.contact_no not in phones:
                phones.append(member.contact_no)

        for phone in phones:
            queue_message(
                db,
                current,
                recipient_name=family_name,
                recipient_phone=phone,
                message=(
                    f"Namaste, your {report_type} family health report for {family_name} "
                    f"has been generated by ASHA CONNECT."
                ),
                attachment_path=file_path,
                related_report_uid=report_uid,
            )

    if send_copy_to_phc:
        phc_admins = (
            db.query(AshaWorker)
            .filter(AshaWorker.role == "phc_admin")
            .filter(AshaWorker.phc_id == current.phc_id)
            .all()
        )

        for admin in phc_admins:
            queue_message(
                db,
                current,
                recipient_name=admin.name,
                recipient_phone=admin.phone_no,
                message=(
                    f"PHC copy: {report_type} family health report generated for {family_name} "
                    f"by {current.name}."
                ),
                attachment_path=file_path,
                related_report_uid=report_uid,
            )

    audit_log(
        db,
        "staff",
        current.worker_id,
        role_value(current.role),
        "GENERATE_FAMILY_REPORT",
        "Family",
        family_name,
        title,
    )

    return {
        "message": "Family report generated successfully",
        "report_uid": report_uid,
        "download_url": report_url(report_uid),
        "sent_to_family": send_to_family,
        "sent_copy_to_phc": send_copy_to_phc,
    }


@router.post("/reports/all-families-phc-summary")
def all_families_phc_summary(
    payload: dict = Body(default={}),
    db: Session = Depends(get_db),
    current: AshaWorker = Depends(get_current_worker),
):
    create_tables(db)

    report_type = str(payload.get("report_type") or "monthly").lower()
    notes = str(payload.get("notes") or "")
    send_copy_to_phc = bool(payload.get("send_copy_to_phc", True))

    rows = get_visible_beneficiaries(db, current).all()

    family_map = {}
    for item in rows:
        family = item.address or "Unassigned Family"
        family_map.setdefault(family, {"members": 0, "children": 0, "pregnant": 0, "elderly": 0})
        family_map[family]["members"] += 1

        category = str(item.category or "").lower()
        if "child" in category:
            family_map[family]["children"] += 1
        if "pregnant" in category:
            family_map[family]["pregnant"] += 1
        if item.age and item.age >= 60:
            family_map[family]["elderly"] += 1

    summary_table = [["Family", "Members", "Children", "Pregnant", "Elderly"]]
    for family, value in sorted(family_map.items()):
        summary_table.append(
            [
                family,
                str(value["members"]),
                str(value["children"]),
                str(value["pregnant"]),
                str(value["elderly"]),
            ]
        )

    title = f"{current.name} - {report_type.title()} All-Families PHC Summary"
    subtitle = f"Generated on {date.today().isoformat()}"

    sections = [
        {
            "heading": "ASHA Worker Summary",
            "table": [
                ["Field", "Value"],
                ["ASHA Worker", current.name],
                ["Village", current.village or "N/A"],
                ["Total Families", str(len(family_map))],
                ["Total Beneficiaries", str(len(rows))],
            ],
        },
        {
            "heading": "Family-wise Summary",
            "table": summary_table,
        },
        {
            "heading": "ASHA Notes",
            "paragraph": notes or "No additional notes were added.",
        },
    ]

    report_uid = str(uuid.uuid4())
    filename = f"all_families_{safe_filename(current.name)}_{report_uid[:8]}.pdf"
    file_path = build_report_pdf(title, subtitle, sections, filename)

    insert_report(
        db,
        report_uid=report_uid,
        report_type=report_type,
        scope="all_families",
        title=title,
        file_path=file_path,
        current=current,
        generated_for="phc_admin",
        notes=notes,
    )

    if send_copy_to_phc:
        phc_admins = (
            db.query(AshaWorker)
            .filter(AshaWorker.role == "phc_admin")
            .filter(AshaWorker.phc_id == current.phc_id)
            .all()
        )

        for admin in phc_admins:
            queue_message(
                db,
                current,
                recipient_name=admin.name,
                recipient_phone=admin.phone_no,
                message=f"PHC copy: {report_type} all-family summary generated by {current.name}.",
                attachment_path=file_path,
                related_report_uid=report_uid,
            )

    audit_log(
        db,
        "staff",
        current.worker_id,
        role_value(current.role),
        "GENERATE_ALL_FAMILIES_PHC_SUMMARY",
        "AshaWorker",
        current.worker_id,
        title,
    )

    return {
        "message": "All-families PHC summary generated successfully",
        "report_uid": report_uid,
        "download_url": report_url(report_uid),
        "sent_copy_to_phc": send_copy_to_phc,
    }


@router.get("/reports")
def report_history(
    db: Session = Depends(get_db),
    current: AshaWorker = Depends(get_current_worker),
):
    create_tables(db)

    rows = db.execute(
        text(
            """
            SELECT report_uid, report_type, scope, title, beneficiary_id, family_name,
                   generated_for, notes, created_at
            FROM generated_reports
            WHERE generated_by = :worker_id
            ORDER BY id DESC
            LIMIT 100
            """
        ),
        {"worker_id": current.worker_id},
    ).mappings().all()

    return [dict(row) for row in rows]


@router.get("/reports/{report_uid}/download")
def download_report(
    report_uid: str,
    db: Session = Depends(get_db),
    current: AshaWorker = Depends(get_current_worker),
):
    create_tables(db)

    row = db.execute(
        text(
            """
            SELECT file_path, title, generated_by
            FROM generated_reports
            WHERE report_uid = :report_uid
            """
        ),
        {"report_uid": report_uid},
    ).mappings().first()

    if not row:
        raise HTTPException(status_code=404, detail="Report not found")

    # ASHA can download own reports. Admin/supervisor can also download reports in PHC later.
    if int(row["generated_by"]) != int(current.worker_id) and role_value(current.role) == "asha":
        raise HTTPException(status_code=403, detail="You do not have access to this report")

    path = Path(row["file_path"])

    if not path.exists():
        raise HTTPException(status_code=404, detail="Report file missing")

    return FileResponse(
        str(path),
        media_type="application/pdf",
        filename=path.name,
    )


@router.get("/messages")
def outbound_messages(
    db: Session = Depends(get_db),
    current: AshaWorker = Depends(get_current_worker),
):
    create_tables(db)

    rows = db.execute(
        text(
            """
            SELECT id, channel, recipient_name, recipient_phone, message, attachment_path,
                   related_report_uid, status, delivery_mode, created_at, sent_at
            FROM outbound_messages
            WHERE created_by = :worker_id
            ORDER BY id DESC
            LIMIT 100
            """
        ),
        {"worker_id": current.worker_id},
    ).mappings().all()

    result = []
    for row in rows:
        item = dict(row)
        phone = clean_phone(item.get("recipient_phone"))
        item["whatsapp_link"] = (
            f"https://wa.me/{phone}?text={item['message'].replace(' ', '%20')}"
            if phone
            else ""
        )
        result.append(item)

    return result


@router.post("/messages/{message_id}/mark-sent")
def mark_message_sent(
    message_id: int,
    db: Session = Depends(get_db),
    current: AshaWorker = Depends(get_current_worker),
):
    create_tables(db)

    db.execute(
        text(
            """
            UPDATE outbound_messages
            SET status = 'sent', sent_at = :sent_at
            WHERE id = :id AND created_by = :worker_id
            """
        ),
        {
            "id": message_id,
            "worker_id": current.worker_id,
            "sent_at": now_iso(),
        },
    )
    db.commit()

    return "Message marked as sent"


@router.get("/reminders/settings")
def get_reminder_settings(
    db: Session = Depends(get_db),
    current: AshaWorker = Depends(get_current_worker),
):
    create_tables(db)

    rows = db.execute(
        text(
            """
            SELECT id, reminder_type, enabled, one_day_before, few_hours_before,
                   hours_before, channel, template, updated_at
            FROM reminder_settings
            WHERE worker_id = :worker_id
            ORDER BY reminder_type
            """
        ),
        {"worker_id": current.worker_id},
    ).mappings().all()

    if rows:
        return [dict(row) for row in rows]

    defaults = [
        ("appointment", "Namaste {name}, reminder: you have a healthcare appointment on {date}."),
        ("immunization", "Namaste {name}, reminder: vaccination is due on {date}."),
        ("pregnancy", "Namaste {name}, reminder: ANC/PNC follow-up is due on {date}."),
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
                "worker_id": current.worker_id,
                "reminder_type": reminder_type,
                "template": template,
                "updated_at": now_iso(),
            },
        )

    db.commit()

    rows = db.execute(
        text(
            """
            SELECT id, reminder_type, enabled, one_day_before, few_hours_before,
                   hours_before, channel, template, updated_at
            FROM reminder_settings
            WHERE worker_id = :worker_id
            ORDER BY reminder_type
            """
        ),
        {"worker_id": current.worker_id},
    ).mappings().all()

    return [dict(row) for row in rows]


@router.post("/reminders/settings")
def save_reminder_settings(
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    current: AshaWorker = Depends(get_current_worker),
):
    create_tables(db)

    reminder_type = str(payload.get("reminder_type") or "").strip().lower()

    if reminder_type not in ["appointment", "immunization", "pregnancy"]:
        raise HTTPException(status_code=400, detail="Invalid reminder_type")

    db.execute(
        text(
            """
            DELETE FROM reminder_settings
            WHERE worker_id = :worker_id AND reminder_type = :reminder_type
            """
        ),
        {
            "worker_id": current.worker_id,
            "reminder_type": reminder_type,
        },
    )

    db.execute(
        text(
            """
            INSERT INTO reminder_settings
            (worker_id, reminder_type, enabled, one_day_before, few_hours_before,
             hours_before, channel, template, updated_at)
            VALUES
            (:worker_id, :reminder_type, :enabled, :one_day_before, :few_hours_before,
             :hours_before, :channel, :template, :updated_at)
            """
        ),
        {
            "worker_id": current.worker_id,
            "reminder_type": reminder_type,
            "enabled": 1 if payload.get("enabled", True) else 0,
            "one_day_before": 1 if payload.get("one_day_before", True) else 0,
            "few_hours_before": 1 if payload.get("few_hours_before", True) else 0,
            "hours_before": int(payload.get("hours_before") or 3),
            "channel": str(payload.get("channel") or "whatsapp"),
            "template": str(payload.get("template") or ""),
            "updated_at": now_iso(),
        },
    )

    db.commit()

    return "Reminder settings saved"


def format_message(template, beneficiary_name, due_date, reminder_type):
    if not template:
        template = "Namaste {name}, reminder: your {type} is scheduled on {date}."

    return (
        template.replace("{name}", beneficiary_name or "beneficiary")
        .replace("{date}", str(due_date or "scheduled date"))
        .replace("{type}", reminder_type)
    )


def create_reminder_if_needed(
    db,
    current,
    source_type,
    source_id,
    beneficiary_id,
    beneficiary_name,
    phone,
    due_date,
    reminder_stage,
    template,
):
    existing = db.execute(
        text(
            """
            SELECT id FROM reminder_events
            WHERE source_type = :source_type
              AND source_id = :source_id
              AND reminder_stage = :reminder_stage
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

    queue_message(
        db,
        current,
        recipient_name=beneficiary_name,
        recipient_phone=phone,
        message=message,
        attachment_path="",
        related_report_uid="",
        channel="whatsapp",
    )

    msg_id = db.execute(text("SELECT last_insert_rowid()")).scalar()

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


@router.post("/reminders/run-now")
def run_reminder_scan(
    db: Session = Depends(get_db),
    current: AshaWorker = Depends(get_current_worker),
):
    create_tables(db)

    settings = get_reminder_settings(db, current)
    setting_map = {item["reminder_type"]: item for item in settings if item.get("enabled")}

    ids = visible_worker_ids(db, current)
    tomorrow = date.today() + timedelta(days=1)

    created = 0

    if "appointment" in setting_map:
        template = setting_map["appointment"].get("template") or ""
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
            {"worker_ids": ids, "target_date": tomorrow.isoformat()},
        ).mappings().all()

        for row in rows:
            if create_reminder_if_needed(
                db,
                current,
                "appointment",
                row["appointment_id"],
                row["beneficiary_id"],
                row["full_name"],
                row["contact_no"],
                row["appointment_date"],
                "one_day_before",
                template,
            ):
                created += 1

    if "immunization" in setting_map:
        template = setting_map["immunization"].get("template") or ""
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
            {"worker_ids": ids, "target_date": tomorrow.isoformat()},
        ).mappings().all()

        for row in rows:
            if create_reminder_if_needed(
                db,
                current,
                "immunization",
                row["immunization_id"],
                row["beneficiary_id"],
                row["full_name"],
                row["contact_no"],
                row["scheduled_date"],
                "one_day_before",
                template,
            ):
                created += 1

    audit_log(
        db,
        "staff",
        current.worker_id,
        role_value(current.role),
        "RUN_REMINDER_SCAN",
        "Reminder",
        "",
        f"Created {created} reminder messages",
    )

    return {
        "message": "Reminder scan completed",
        "created_messages": created,
        "target_date": tomorrow.isoformat(),
    }


# -------------------------------------------------------------------
# Automatic Reminder Scheduler
# -------------------------------------------------------------------

CARE_REMINDER_SCHEDULER_STARTED = False


@router.post("/reminders/auto-run-now")
def auto_run_reminder_scan(
    db: Session = Depends(get_db),
    current: AshaWorker = Depends(get_current_worker),
):
    """
    Manual trigger for the upgraded reminder engine.
    This checks one-day-before and same-day reminders.
    """
    create_tables(db)
    result = run_reminders_for_current_user(db, current)

    audit_log(
        db,
        "staff",
        current.worker_id,
        role_value(current.role),
        "RUN_AUTO_REMINDER_SCAN",
        "Reminder",
        "",
        f"Created {result.get('created_messages', 0)} reminder messages",
    )

    return result


@router.get("/reminders/scheduler/status")
def reminder_scheduler_status():
    return {
        "enabled": os.getenv("ASHACONNECT_REMINDER_SCHEDULER", "1") == "1",
        "started": CARE_REMINDER_SCHEDULER_STARTED,
        "interval_seconds": int(os.getenv("ASHACONNECT_REMINDER_INTERVAL_SECONDS", "3600")),
        "note": "Scheduler runs while FastAPI backend is running.",
    }


async def care_reminder_scheduler_loop():
    interval = int(os.getenv("ASHACONNECT_REMINDER_INTERVAL_SECONDS", "3600"))

    # small delay so app boots first
    await asyncio.sleep(8)

    while True:
        db = SessionLocal()

        try:
            create_tables(db)
            result = run_reminders_for_all_asha(db)
            print("[ASHACONNECT Reminder Scheduler]", result)
        except Exception as exc:
            print("[ASHACONNECT Reminder Scheduler ERROR]", str(exc))
        finally:
            db.close()

        await asyncio.sleep(interval)


@router.on_event("startup")
async def start_care_reminder_scheduler():
    global CARE_REMINDER_SCHEDULER_STARTED

    if os.getenv("ASHACONNECT_REMINDER_SCHEDULER", "1") != "1":
        print("[ASHACONNECT Reminder Scheduler] disabled")
        return

    if CARE_REMINDER_SCHEDULER_STARTED:
        return

    CARE_REMINDER_SCHEDULER_STARTED = True
    asyncio.create_task(care_reminder_scheduler_loop())
    print("[ASHACONNECT Reminder Scheduler] started")


# -------------------------------------------------------------------
# Care Events: source records for appointments, vaccination, follow-ups
# -------------------------------------------------------------------

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


@router.get("/events")
def list_care_events(
    db: Session = Depends(get_db),
    current: AshaWorker = Depends(get_current_worker),
):
    create_tables(db)
    ensure_care_events_table(db)

    ids = visible_worker_ids(db, current)

    rows = db.execute(
        text(
            """
            SELECT e.id, e.event_uid, e.event_type, e.title, e.beneficiary_id,
                   e.worker_id, e.scheduled_at, e.status, e.priority,
                   e.notes, e.reminder_enabled, e.created_at,
                   b.full_name AS beneficiary_name,
                   b.contact_no AS beneficiary_phone
            FROM care_events e
            JOIN beneficiaries b ON b.beneficiary_id = e.beneficiary_id
            WHERE e.worker_id IN :worker_ids
            ORDER BY datetime(e.scheduled_at) ASC
            LIMIT 200
            """
        ).bindparams(bindparam("worker_ids", expanding=True)),
        {"worker_ids": ids},
    ).mappings().all()

    return [dict(row) for row in rows]


@router.post("/events")
def create_care_event(
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    current: AshaWorker = Depends(get_current_worker),
):
    create_tables(db)
    ensure_care_events_table(db)

    beneficiary_id = int(payload.get("beneficiary_id") or 0)
    beneficiary = get_beneficiary_or_403(db, current, beneficiary_id)

    event_type = str(payload.get("event_type") or "appointment").strip().lower()
    title = str(payload.get("title") or "").strip()
    scheduled_at = str(payload.get("scheduled_at") or "").strip()
    priority = str(payload.get("priority") or "normal").strip().lower()
    notes = str(payload.get("notes") or "").strip()

    if not scheduled_at:
        scheduled_at = (date.today() + timedelta(days=1)).isoformat()

    if not title:
        if event_type == "immunization":
            title = "Vaccination Due"
        elif event_type == "pregnancy":
            title = "Pregnancy Follow-up"
        elif event_type == "checkup":
            title = "Routine Health Checkup"
        else:
            title = "Healthcare Appointment"

    event_uid = str(uuid.uuid4())
    worker_id = getattr(beneficiary, "asha_worker_id", None) or current.worker_id

    db.execute(
        text(
            """
            INSERT INTO care_events
            (event_uid, event_type, title, beneficiary_id, worker_id, scheduled_at,
             status, priority, notes, reminder_enabled, created_by, created_at)
            VALUES
            (:event_uid, :event_type, :title, :beneficiary_id, :worker_id, :scheduled_at,
             'scheduled', :priority, :notes, 1, :created_by, :created_at)
            """
        ),
        {
            "event_uid": event_uid,
            "event_type": event_type,
            "title": title,
            "beneficiary_id": beneficiary.beneficiary_id,
            "worker_id": worker_id,
            "scheduled_at": scheduled_at,
            "priority": priority,
            "notes": notes,
            "created_by": current.worker_id,
            "created_at": now_iso(),
        },
    )

    db.commit()

    audit_log(
        db,
        "staff",
        current.worker_id,
        role_value(current.role),
        "CREATE_CARE_EVENT",
        "CareEvent",
        event_uid,
        f"{title} for {beneficiary.full_name}",
    )

    return {
        "message": "Care event created successfully",
        "event_uid": event_uid,
        "title": title,
        "scheduled_at": scheduled_at,
    }


@router.post("/events/seed-demo")
def seed_demo_care_events(
    db: Session = Depends(get_db),
    current: AshaWorker = Depends(get_current_worker),
):
    """
    Demo helper: creates due events for today/tomorrow so reminder scan can be tested.
    """
    create_tables(db)
    ensure_care_events_table(db)

    beneficiaries = get_visible_beneficiaries(db, current).limit(3).all()

    if not beneficiaries:
        raise HTTPException(status_code=404, detail="No beneficiaries available to seed care events")

    tomorrow = date.today() + timedelta(days=1)
    today = date.today()

    templates = [
        ("appointment", "Healthcare Appointment", tomorrow.isoformat()),
        ("immunization", "Vaccination Due", tomorrow.isoformat()),
        ("checkup", "Routine Health Checkup", today.isoformat()),
    ]

    created = []

    for index, beneficiary in enumerate(beneficiaries):
        event_type, title, scheduled_at = templates[index % len(templates)]
        event_uid = str(uuid.uuid4())
        worker_id = getattr(beneficiary, "asha_worker_id", None) or current.worker_id

        db.execute(
            text(
                """
                INSERT INTO care_events
                (event_uid, event_type, title, beneficiary_id, worker_id, scheduled_at,
                 status, priority, notes, reminder_enabled, created_by, created_at)
                VALUES
                (:event_uid, :event_type, :title, :beneficiary_id, :worker_id, :scheduled_at,
                 'scheduled', 'normal', 'Demo due event for reminder testing', 1, :created_by, :created_at)
                """
            ),
            {
                "event_uid": event_uid,
                "event_type": event_type,
                "title": title,
                "beneficiary_id": beneficiary.beneficiary_id,
                "worker_id": worker_id,
                "scheduled_at": scheduled_at,
                "created_by": current.worker_id,
                "created_at": now_iso(),
            },
        )

        created.append(
            {
                "event_uid": event_uid,
                "beneficiary": beneficiary.full_name,
                "event_type": event_type,
                "title": title,
                "scheduled_at": scheduled_at,
            }
        )

    db.commit()

    return {
        "message": "Demo care events created",
        "created": created,
    }

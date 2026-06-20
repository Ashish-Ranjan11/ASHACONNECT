from datetime import date
from io import BytesIO

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

from app.db.mysql import get_db
from app.deps import get_current_worker, visible_worker_ids
from app.models import (
    AshaWorker,
    Beneficiary,
    PregnancyRecord,
    ImmunizationRecord,
    Appointment,
    Event,
    MonthlyReport,
)

router = APIRouter(prefix="/api/reports", tags=["Reports"])


@router.get("")
def list_reports(
    db: Session = Depends(get_db),
    current: AshaWorker = Depends(get_current_worker),
):
    worker_ids = visible_worker_ids(db, current)

    return (
        db.query(MonthlyReport)
        .filter(MonthlyReport.generated_by.in_(worker_ids))
        .order_by(MonthlyReport.report_id.desc())
        .all()
    )


@router.post("/generate")
def generate_report(
    db: Session = Depends(get_db),
    current: AshaWorker = Depends(get_current_worker),
):
    worker_ids = visible_worker_ids(db, current)

    beneficiaries = (
        db.query(Beneficiary)
        .filter(Beneficiary.asha_worker_id.in_(worker_ids))
        .all()
    )

    beneficiary_ids = [b.beneficiary_id for b in beneficiaries] or [0]

    total_pregnancies = (
        db.query(PregnancyRecord)
        .filter(PregnancyRecord.beneficiary_id.in_(beneficiary_ids))
        .count()
    )

    total_immunizations = (
        db.query(ImmunizationRecord)
        .filter(ImmunizationRecord.beneficiary_id.in_(beneficiary_ids))
        .count()
    )

    total_appointments = (
        db.query(Appointment)
        .filter(Appointment.beneficiary_id.in_(beneficiary_ids))
        .count()
    )

    total_events = (
        db.query(Event)
        .filter(Event.organizer_id.in_(worker_ids))
        .count()
    )

    today = date.today()

    report = MonthlyReport(
        month=today.strftime("%B"),
        year=today.year,
        total_patients=len(beneficiaries),
        total_pregnancies=total_pregnancies,
        total_immunizations=total_immunizations,
        total_appointments=total_appointments,
        total_events=total_events,
        generated_by=current.worker_id,
        phc_id=current.phc_id,
        status="submitted",
        notes=f"Auto-generated monthly report for {current.name}.",
    )

    db.add(report)
    db.commit()
    db.refresh(report)

    return {
        "message": "Monthly report generated successfully",
        "report_id": report.report_id,
    }


@router.get("/download-pdf")
def download_latest_report_pdf(
    db: Session = Depends(get_db),
    current: AshaWorker = Depends(get_current_worker),
):
    worker_ids = visible_worker_ids(db, current)

    beneficiaries = (
        db.query(Beneficiary)
        .filter(Beneficiary.asha_worker_id.in_(worker_ids))
        .all()
    )

    beneficiary_ids = [b.beneficiary_id for b in beneficiaries] or [0]

    pregnancies = (
        db.query(PregnancyRecord)
        .filter(PregnancyRecord.beneficiary_id.in_(beneficiary_ids))
        .all()
    )

    immunizations = (
        db.query(ImmunizationRecord)
        .filter(ImmunizationRecord.beneficiary_id.in_(beneficiary_ids))
        .all()
    )

    appointments = (
        db.query(Appointment)
        .filter(Appointment.beneficiary_id.in_(beneficiary_ids))
        .all()
    )

    events = (
        db.query(Event)
        .filter(Event.organizer_id.in_(worker_ids))
        .all()
    )

    high_risk = sum(1 for p in pregnancies if p.status == "high_risk")
    missed_immunizations = sum(1 for i in immunizations if i.status == "missed")
    upcoming_appointments = sum(1 for a in appointments if a.status == "scheduled")

    buffer = BytesIO()

    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36,
    )

    styles = getSampleStyleSheet()
    elements = []

    title = Paragraph("ASHACONNECT Monthly Health Workflow Report", styles["Title"])
    subtitle = Paragraph(
        "ASHA Workers Workflow Automation and Database Management",
        styles["Normal"],
    )

    elements.append(title)
    elements.append(Spacer(1, 8))
    elements.append(subtitle)
    elements.append(Spacer(1, 18))

    worker_info = [
        ["Generated For", current.name],
        ["Role", current.role],
        ["PHC", current.phc.name if current.phc else "N/A"],
        ["Village", current.village or "N/A"],
        ["Date", date.today().strftime("%d %B %Y")],
    ]

    worker_table = Table(worker_info, colWidths=[130, 340])
    worker_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#E8F7F2")),
                ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#0B1830")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("PADDING", (0, 0), (-1, -1), 9),
            ]
        )
    )

    elements.append(worker_table)
    elements.append(Spacer(1, 20))

    summary_data = [
        ["Metric", "Count"],
        ["Total Beneficiaries", len(beneficiaries)],
        ["Pregnancy Records", len(pregnancies)],
        ["High Risk Pregnancies", high_risk],
        ["Immunization Records", len(immunizations)],
        ["Missed Immunizations", missed_immunizations],
        ["Appointments", len(appointments)],
        ["Upcoming Appointments", upcoming_appointments],
        ["Community Events", len(events)],
    ]

    summary_table = Table(summary_data, colWidths=[300, 170])
    summary_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F9F83")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("PADDING", (0, 0), (-1, -1), 9),
                ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#F8FAFC")),
            ]
        )
    )

    elements.append(Paragraph("Monthly Summary", styles["Heading2"]))
    elements.append(Spacer(1, 8))
    elements.append(summary_table)
    elements.append(Spacer(1, 20))

    category_counts = {
        "Pregnant": sum(1 for b in beneficiaries if b.category == "pregnant"),
        "Child": sum(1 for b in beneficiaries if b.category == "child"),
        "Elderly": sum(1 for b in beneficiaries if b.category == "elderly"),
        "General": sum(1 for b in beneficiaries if b.category == "general"),
    }

    category_data = [["Beneficiary Category", "Count"]]
    for key, value in category_counts.items():
        category_data.append([key, value])

    category_table = Table(category_data, colWidths=[300, 170])
    category_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#172345")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("PADDING", (0, 0), (-1, -1), 9),
            ]
        )
    )

    elements.append(Paragraph("Beneficiary Category Breakdown", styles["Heading2"]))
    elements.append(Spacer(1, 8))
    elements.append(category_table)
    elements.append(Spacer(1, 20))

    risk_notes = [
        "High-risk pregnancy cases should be prioritized for ANC follow-up.",
        "Missed immunization cases should be contacted and rescheduled.",
        "Upcoming appointments should be monitored to reduce missed visits.",
        "Community events should be used for nutrition, awareness and vaccination outreach.",
    ]

    elements.append(Paragraph("Recommended Follow-up Actions", styles["Heading2"]))
    for note in risk_notes:
        elements.append(Paragraph(f"• {note}", styles["Normal"]))
        elements.append(Spacer(1, 5))

    document.build(elements)

    buffer.seek(0)

    filename = f"ashaconnect_report_{date.today().isoformat()}.pdf"

    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        },
    )
import os
from typing import Any

import httpx


BACKEND_URL = os.getenv(
    "ASHA_BACKEND_URL",
    "http://127.0.0.1:8000",
)


async def backend_request(
    method: str,
    path: str,
    authorization: str,
    *,
    params: dict[str, Any] | None = None,
    json: dict[str, Any] | None = None,
):
    if not authorization:
        raise ValueError("Authorization token is required")

    url = f"{BACKEND_URL}{path}"

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.request(
            method,
            url,
            headers={
                "Authorization": authorization,
                "Content-Type": "application/json",
            },
            params=params,
            json=json,
        )

        response.raise_for_status()

        if not response.content:
            return {}

        return response.json()


# ============================================================
# READ ACTIONS
# ============================================================

async def list_appointments(payload, authorization):
    return await backend_request(
        "GET",
        "/api/appointments",
        authorization,
        params={
            "date": payload.get("date")
        } if payload.get("date") else None,
    )


async def list_beneficiaries(payload, authorization):
    return await backend_request(
        "GET",
        "/api/beneficiaries",
        authorization,
    )


async def get_beneficiary_profile(payload, authorization):
    beneficiary_id = payload["beneficiary_id"]

    return await backend_request(
        "GET",
        f"/api/beneficiaries/{beneficiary_id}/profile",
        authorization,
    )


async def list_pregnancy_records(payload, authorization):
    return await backend_request(
        "GET",
        "/api/pregnancy-records",
        authorization,
    )


async def list_immunization_records(payload, authorization):
    return await backend_request(
        "GET",
        "/api/immunization-records",
        authorization,
    )


async def list_care_messages(payload, authorization):
    return await backend_request(
        "GET",
        "/api/care-automation/messages",
        authorization,
    )


async def get_reminder_status(payload, authorization):
    return await backend_request(
        "GET",
        "/api/care-automation/reminders/scheduler/status",
        authorization,
    )


async def list_care_reports(payload, authorization):
    return await backend_request(
        "GET",
        "/api/care-automation/reports",
        authorization,
    )


async def list_reports(payload, authorization):
    return await backend_request(
        "GET",
        "/api/reports",
        authorization,
    )


# ============================================================
# WRITE ACTIONS
# ============================================================

async def create_appointment(payload, authorization):
    return await backend_request(
        "POST",
        "/api/appointments",
        authorization,
        json=payload,
    )


async def create_beneficiary(payload, authorization):
    return await backend_request(
        "POST",
        "/api/beneficiaries",
        authorization,
        json=payload,
    )


async def update_beneficiary(payload, authorization):
    beneficiary_id = payload["beneficiary_id"]

    body = {
        k: v
        for k, v in payload.items()
        if k != "beneficiary_id"
    }

    return await backend_request(
        "PUT",
        f"/api/beneficiaries/{beneficiary_id}",
        authorization,
        json=body,
    )


async def delete_beneficiary(payload, authorization):
    beneficiary_id = payload["beneficiary_id"]

    return await backend_request(
        "DELETE",
        f"/api/beneficiaries/{beneficiary_id}",
        authorization,
    )


async def create_pregnancy_record(payload, authorization):
    return await backend_request(
        "POST",
        "/api/pregnancy-records",
        authorization,
        json=payload,
    )


async def create_immunization_record(payload, authorization):
    return await backend_request(
        "POST",
        "/api/immunization-records",
        authorization,
        json=payload,
    )


async def run_reminders(payload, authorization):
    return await backend_request(
        "POST",
        "/api/care-automation/reminders/run-now",
        authorization,
    )


async def run_auto_reminders(payload, authorization):
    return await backend_request(
        "POST",
        "/api/care-automation/reminders/auto-run-now",
        authorization,
    )


async def mark_message_sent(payload, authorization):
    message_id = payload["message_id"]

    return await backend_request(
        "POST",
        f"/api/care-automation/messages/{message_id}/mark-sent",
        authorization,
    )


async def generate_individual_report(payload, authorization):
    return await backend_request(
        "POST",
        "/api/care-automation/reports/individual",
        authorization,
        json=payload,
    )


async def generate_family_report(payload, authorization):
    return await backend_request(
        "POST",
        "/api/care-automation/reports/family",
        authorization,
        json=payload,
    )


async def generate_phc_summary(payload, authorization):
    return await backend_request(
        "POST",
        "/api/care-automation/reports/all-families-phc-summary",
        authorization,
        json=payload,
    )


async def generate_report(payload, authorization):
    return await backend_request(
        "POST",
        "/api/reports/generate",
        authorization,
    )


# ============================================================
# CENTRAL ACTION REGISTRY
# ============================================================

ACTION_HANDLERS = {
    # READ
    "list_appointments": list_appointments,
    "list_beneficiaries": list_beneficiaries,
    "get_beneficiary_profile": get_beneficiary_profile,
    "list_pregnancy_records": list_pregnancy_records,
    "list_immunization_records": list_immunization_records,
    "list_care_messages": list_care_messages,
    "get_reminder_status": get_reminder_status,
    "list_care_reports": list_care_reports,
    "list_reports": list_reports,

    # WRITE
    "create_appointment": create_appointment,
    "create_beneficiary": create_beneficiary,
    "update_beneficiary": update_beneficiary,
    "delete_beneficiary": delete_beneficiary,
    "create_pregnancy_record": create_pregnancy_record,
    "create_immunization_record": create_immunization_record,
    "run_reminders": run_reminders,
    "run_auto_reminders": run_auto_reminders,
    "mark_message_sent": mark_message_sent,
    "generate_individual_report": generate_individual_report,
    "generate_family_report": generate_family_report,
    "generate_phc_summary": generate_phc_summary,
    "generate_report": generate_report,
}


async def execute_asha_action(
    action: str,
    payload: dict[str, Any],
    authorization: str,
):
    """
    Single controlled gateway between Gemini and ASHA Connect.
    """

    if action not in ACTION_HANDLERS:
        raise ValueError(
            f"Unsupported ASHA Connect action: {action}"
        )

    handler = ACTION_HANDLERS[action]

    if payload is None:
        payload = {}

    return await handler(
        payload,
        authorization,
    )
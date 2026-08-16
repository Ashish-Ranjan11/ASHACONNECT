import os
import httpx


ASHA_BACKEND_URL = os.getenv(
    "ASHA_BACKEND_URL",
    "http://127.0.0.1:8000"
)


async def backend_request(
    method: str,
    path: str,
    authorization: str,
    params: dict | None = None,
    json: dict | None = None,
):
    """
    Authenticated request from Voice Agent -> ASHA backend.

    The JWT received from the frontend/voice request is forwarded
    unchanged to the backend.
    """

    if not authorization:
        raise ValueError("Authentication required")

    url = f"{ASHA_BACKEND_URL}{path}"

    headers = {
        "Authorization": authorization,
        "Accept": "application/json",
    }

    if json is not None:
        headers["Content-Type"] = "application/json"

    async with httpx.AsyncClient(timeout=15.0) as client:

        response = await client.request(
            method=method,
            url=url,
            params=params,
            json=json,
            headers=headers,
        )

        response.raise_for_status()

        if not response.content:
            return {}

        return response.json()


# ============================================================
# APPOINTMENTS
# ============================================================

async def list_appointments(
    authorization: str,
    date: str | None = None,
):
    params = {}

    if date:
        params["date"] = date

    return await backend_request(
        "GET",
        "/api/appointments",
        authorization,
        params=params,
    )


async def create_appointment(
    authorization: str,
    payload: dict,
):
    return await backend_request(
        "POST",
        "/api/appointments",
        authorization,
        json=payload,
    )


# ============================================================
# BENEFICIARIES
# ============================================================

async def list_beneficiaries(
    authorization: str,
):
    return await backend_request(
        "GET",
        "/api/beneficiaries",
        authorization,
    )


async def create_beneficiary(
    authorization: str,
    payload: dict,
):
    return await backend_request(
        "POST",
        "/api/beneficiaries",
        authorization,
        json=payload,
    )


async def get_beneficiary(
    authorization: str,
    beneficiary_id: int,
):
    return await backend_request(
        "GET",
        f"/api/beneficiaries/{beneficiary_id}/profile",
        authorization,
    )


# ============================================================
# PREGNANCY
# ============================================================

async def list_pregnancy_records(
    authorization: str,
):
    return await backend_request(
        "GET",
        "/api/pregnancy-records",
        authorization,
    )


async def create_pregnancy_record(
    authorization: str,
    payload: dict,
):
    return await backend_request(
        "POST",
        "/api/pregnancy-records",
        authorization,
        json=payload,
    )


# ============================================================
# IMMUNIZATION
# ============================================================

async def list_immunization_records(
    authorization: str,
):
    return await backend_request(
        "GET",
        "/api/immunization-records",
        authorization,
    )


async def create_immunization_record(
    authorization: str,
    payload: dict,
):
    return await backend_request(
        "POST",
        "/api/immunization-records",
        authorization,
        json=payload,
    )


# ============================================================
# REMINDERS / MESSAGES
# ============================================================

async def list_messages(
    authorization: str,
):
    return await backend_request(
        "GET",
        "/api/care-automation/messages",
        authorization,
    )


async def run_reminders(
    authorization: str,
):
    return await backend_request(
        "POST",
        "/api/care-automation/reminders/run-now",
        authorization,
    )


async def auto_run_reminders(
    authorization: str,
):
    return await backend_request(
        "POST",
        "/api/care-automation/reminders/auto-run-now",
        authorization,
    )


# ============================================================
# REPORTS
# ============================================================

async def list_reports(
    authorization: str,
):
    return await backend_request(
        "GET",
        "/api/care-automation/reports",
        authorization,
    )


async def generate_individual_report(
    authorization: str,
    payload: dict,
):
    return await backend_request(
        "POST",
        "/api/care-automation/reports/individual",
        authorization,
        json=payload,
    )


async def generate_family_report(
    authorization: str,
    payload: dict,
):
    return await backend_request(
        "POST",
        "/api/care-automation/reports/family",
        authorization,
        json=payload,
    )


async def generate_phc_summary(
    authorization: str,
    payload: dict,
):
    return await backend_request(
        "POST",
        "/api/care-automation/reports/all-families-phc-summary",
        authorization,
        json=payload,
    )

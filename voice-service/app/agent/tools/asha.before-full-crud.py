import os
from typing import Any

import httpx
import re
import unicodedata

from rapidfuzz import fuzz
from unidecode import unidecode


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
    """
    Retrieve the complete beneficiary health profile.

    Accepted identifiers:
    - beneficiary_id
    - beneficiary_name
    - person_name
    - name

    Spoken names are resolved against the actual ASHA Connect
    beneficiary database before requesting the profile.
    """

    payload = dict(payload or {})

    beneficiary_id = payload.get("beneficiary_id")

    # --------------------------------------------------
    # Resolve name -> real database beneficiary_id
    # --------------------------------------------------

    if not beneficiary_id:

        spoken_name = (
            payload.get("beneficiary_name")
            or payload.get("person_name")
            or payload.get("name")
        )

        if not spoken_name:
            raise ValueError(
                "Beneficiary name or beneficiary_id is required"
            )

        resolution = await resolve_beneficiary(
            {
                "name": spoken_name,
            },
            authorization,
        )

        if not resolution.get("found"):

            if resolution.get("ambiguous"):

                matches = resolution.get(
                    "matches",
                    [],
                )

                names = [
                    str(item.get("name"))
                    for item in matches
                    if item.get("name")
                ]

                raise ValueError(
                    "Multiple beneficiaries matched"
                    + (
                        ": " + ", ".join(names)
                        if names
                        else ""
                    )
                )

            raise ValueError(
                f"No beneficiary record found for {spoken_name}"
            )

        beneficiary_id = resolution.get(
            "beneficiary_id"
        )

    if not beneficiary_id:
        raise ValueError(
            "Resolved beneficiary has no beneficiary_id"
        )

    # --------------------------------------------------
    # Load canonical profile from ASHA backend/database
    # --------------------------------------------------

    return await backend_request(
        "GET",
        f"/api/beneficiaries/{int(beneficiary_id)}/profile",
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
    """
    Schedule an appointment using either beneficiary_id
    or a spoken beneficiary name.

    The database remains the source of truth.
    """

    payload = dict(payload or {})

    beneficiary_id = payload.get("beneficiary_id")

    # --------------------------------------------------
    # Resolve spoken beneficiary name automatically
    # --------------------------------------------------

    if not beneficiary_id:

        spoken_name = (
            payload.get("beneficiary_name")
            or payload.get("person_name")
            or payload.get("name")
        )

        if not spoken_name:
            raise ValueError(
                "Beneficiary name or beneficiary_id is required"
            )

        resolution = await resolve_beneficiary(
            {
                "name": spoken_name
            },
            authorization,
        )

        if not resolution.get("found"):

            if resolution.get("ambiguous"):
                names = [
                    item.get("name")
                    for item in resolution.get("matches", [])
                    if item.get("name")
                ]

                raise ValueError(
                    "Multiple beneficiaries matched: "
                    + ", ".join(names)
                )

            raise ValueError(
                f"Beneficiary not found: {spoken_name}"
            )

        beneficiary_id = resolution["beneficiary_id"]

    # --------------------------------------------------
    # Backend receives only canonical beneficiary_id
    # --------------------------------------------------

    payload["beneficiary_id"] = int(beneficiary_id)

    payload.pop("beneficiary_name", None)
    payload.pop("person_name", None)
    payload.pop("name", None)

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
# BENEFICIARY NAME RESOLUTION
# ============================================================

def _normalize_person_name(value: str) -> str:
    """
    Normalize beneficiary names coming from voice/STT.

    Handles:
    - Devanagari -> Latin transliteration
    - punctuation
    - possessives
    - common Hindi/Hinglish filler/suffix words
    - duplicate whitespace
    """

    value = str(value or "").strip()

    if not value:
        return ""

    # Unicode normalization
    value = unicodedata.normalize("NFKC", value)

    # Voice may produce Hindi/Devanagari names.
    # Unidecode gives us a comparable Latin representation.
    value = unidecode(value)

    value = value.lower()

    # English possessives
    value = re.sub(r"'s\b", "", value)

    # Remove punctuation but preserve spaces
    value = re.sub(r"[^a-z0-9\s]", " ", value)

    # Common conversational words that may get attached to names
    noise_words = {
        "ji",
        "jee",
        "ka",
        "ki",
        "ke",
        "ko",
        "kaa",
        "kii",
        "hai",
        "hain",
        "ka",
        "appointment",
        "report",
        "beneficiary",
        "patient",
        "record",
        "profile",
        "health",
        "status",
        "please",
    }

    words = [
        word
        for word in value.split()
        if word not in noise_words
    ]

    value = " ".join(words)

    value = re.sub(r"\s+", " ", value)

    return value.strip()


def _name_similarity(query: str, candidate: str) -> float:
    """
    Return a 0-100 similarity score.
    """

    q = _normalize_person_name(query)
    c = _normalize_person_name(candidate)

    if not q or not c:
        return 0.0

    if q == c:
        return 100.0

    # Strong result when one side contains the complete other side.
    if q in c or c in q:
        return 97.0

    return max(
        fuzz.ratio(q, c),
        fuzz.token_sort_ratio(q, c),
        fuzz.token_set_ratio(q, c),
    )


async def resolve_beneficiary(payload, authorization):
    """
    Resolve a spoken beneficiary name against actual ASHA Connect
    beneficiary records.

    Never invents beneficiary IDs.
    """

    raw_name = str(
        payload.get("name")
        or payload.get("person_name")
        or payload.get("beneficiary_name")
        or ""
    ).strip()

    if not raw_name:
        raise ValueError("Beneficiary name is required")

    data = await list_beneficiaries({}, authorization)

    if isinstance(data, dict):
        beneficiaries = (
            data.get("beneficiaries")
            or data.get("data")
            or data.get("items")
            or []
        )

    elif isinstance(data, list):
        beneficiaries = data

    else:
        beneficiaries = []

    if not beneficiaries:
        return {
            "found": False,
            "ambiguous": False,
            "name": raw_name,
            "reason": "No beneficiaries were available to search.",
        }

    normalized_query = _normalize_person_name(raw_name)

    scored = []

    for person in beneficiaries:

        candidate = str(
            person.get("full_name")
            or person.get("name")
            or person.get("beneficiary_name")
            or ""
        ).strip()

        if not candidate:
            continue

        score = _name_similarity(
            raw_name,
            candidate,
        )

        scored.append(
            {
                "score": float(score),
                "candidate": candidate,
                "person": person,
            }
        )

    scored.sort(
        key=lambda item: item["score"],
        reverse=True,
    )

    if not scored:
        return {
            "found": False,
            "ambiguous": False,
            "name": raw_name,
        }

    best = scored[0]

    second_score = (
        scored[1]["score"]
        if len(scored) > 1
        else 0
    )

    best_score = best["score"]

    # --------------------------------------------------------
    # High-confidence unique match
    # --------------------------------------------------------

    # 82 works well for small spelling/STT differences,
    # but we also require a margin over the second candidate.
    if (
        best_score >= 82
        and (
            second_score < 82
            or best_score - second_score >= 7
        )
    ):

        person = best["person"]

        beneficiary_id = (
            person.get("beneficiary_id")
            or person.get("id")
        )

        return {
            "found": True,
            "beneficiary_id": beneficiary_id,
            "public_id": (
                f"ASHA-BEN-{int(beneficiary_id):06d}"
            ),
            "name": best["candidate"],
            "spoken_name": raw_name,
            "normalized_name": normalized_query,
            "match_score": round(best_score, 1),
            "beneficiary": person,
        }

    # --------------------------------------------------------
    # Ambiguous candidates
    # --------------------------------------------------------

    plausible = [
        item
        for item in scored[:5]
        if item["score"] >= 68
    ]

    if plausible:

        return {
            "found": False,
            "ambiguous": True,
            "name": raw_name,
            "normalized_name": normalized_query,
            "matches": [
                {
                    "beneficiary_id": (
                        item["person"].get("beneficiary_id")
                        or item["person"].get("id")
                    ),
                    "name": item["candidate"],
                    "score": round(
                        item["score"],
                        1,
                    ),
                    "family": (
                        item["person"].get("village")
                        or item["person"].get("address")
                        or ""
                    ),
                }
                for item in plausible
            ],
        }

    return {
        "found": False,
        "ambiguous": False,
        "name": raw_name,
        "normalized_name": normalized_query,
        "best_candidate": best["candidate"],
        "best_score": round(best_score, 1),
    }


# ============================================================
# CENTRAL ACTION REGISTRY
# ============================================================

ACTION_HANDLERS = {
    # READ
    "list_appointments": list_appointments,
    "list_beneficiaries": list_beneficiaries,
    "resolve_beneficiary": resolve_beneficiary,
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

    print("\n========== ASHA TOOL CALL ==========")
    print("ACTION :", action)
    print("PAYLOAD:", payload)
    print("====================================\n")

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


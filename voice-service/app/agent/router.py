import httpx
from fastapi import APIRouter, Header
from pydantic import BaseModel

from app.agent.intent import detect_intent
from app.agent.tools.asha import (
    list_appointments,
    list_beneficiaries,
    get_beneficiary_profile,
    create_beneficiary,
    list_pregnancy_records,
    list_immunization_records,
    list_care_messages,
    run_reminders,
    list_reports,
    generate_individual_report,
    generate_family_report,
    generate_phc_summary,
)


router = APIRouter(
    prefix="/voice",
    tags=["Voice Agent"],
)


class CommandRequest(BaseModel):
    text: str


# ============================================================
# RESPONSE FORMATTERS
# ============================================================

def format_appointments(data, date_label=None):

    if isinstance(data, dict):
        appointments = (
            data.get("appointments")
            or data.get("data")
            or data.get("items")
            or []
        )
    elif isinstance(data, list):
        appointments = data
    else:
        appointments = []

    if not appointments:
        if date_label == "tomorrow":
            return "कल कोई अपॉइंटमेंट नहीं है।"

        if date_label == "today":
            return "आज कोई अपॉइंटमेंट नहीं है।"

        return "कोई अपॉइंटमेंट नहीं मिला।"

    count = len(appointments)

    if date_label == "tomorrow":
        response = f"कल {count} अपॉइंटमेंट हैं।"
    elif date_label == "today":
        response = f"आज {count} अपॉइंटमेंट हैं।"
    else:
        response = f"{count} अपॉइंटमेंट मिले हैं।"

    for appointment in appointments[:5]:

        name = (
            appointment.get("beneficiary_name")
            or appointment.get("name")
            or appointment.get("patient_name")
            or appointment.get("beneficiary")
        )

        time = (
            appointment.get("time")
            or appointment.get("appointment_time")
            or appointment.get("scheduled_time")
        )

        if name and time:
            response += (
                f" {name} का अपॉइंटमेंट "
                f"{format_time(time)} बजे है।"
            )

        elif name:
            response += f" {name} का अपॉइंटमेंट है।"

    return response


def format_time(value):

    if not value:
        return ""

    value = str(value)

    if value.startswith("07:"):
        return "सुबह 7"

    if value.startswith("08:"):
        return "सुबह 8"

    if value.startswith("09:"):
        return "सुबह 9"

    if value.startswith("10:"):
        return "सुबह 10"

    if value.startswith("11:"):
        return "सुबह 11"

    if value.startswith("12:"):
        return "दोपहर 12"

    if value.startswith("13:"):
        return "दोपहर 1"

    if value.startswith("14:"):
        return "दोपहर 2"

    if value.startswith("15:"):
        return "दोपहर 3"

    if value.startswith("16:"):
        return "शाम 4"

    if value.startswith("17:"):
        return "शाम 5"

    if value.startswith("18:"):
        return "शाम 6"

    if value.startswith("19:"):
        return "शाम 7"

    if value.startswith("20:"):
        return "रात 8"

    return value


def format_beneficiaries(data):

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
        return "कोई लाभार्थी नहीं मिला।"

    response = f"{len(beneficiaries)} लाभार्थी मिले हैं।"

    for person in beneficiaries[:5]:

        name = (
            person.get("full_name")
            or person.get("name")
            or person.get("beneficiary_name")
        )

        if name:
            response += f" {name}।"

    return response


def format_generic(data, success_message, empty_message):

    if not data:
        return empty_message

    return success_message


def format_health_profile(profile, fallback_name):
    """
    Convert the backend health profile into a short,
    natural Hindi response suitable for TTS.
    """

    beneficiary = profile.get("beneficiary", {})
    risk = profile.get("risk", {})
    next_actions = profile.get("next_actions", [])

    name = (
        beneficiary.get("full_name")
        or beneficiary.get("name")
        or fallback_name
    )

    risk_level = risk.get("level", "")

    risk_labels = {
        "Low Risk": "कम जोखिम",
        "Medium Risk": "मध्यम जोखिम",
        "High Risk": "अधिक जोखिम",
        "No Risk": "कोई जोखिम नहीं",
    }

    risk_text = risk_labels.get(
        risk_level,
        risk_level or "जानकारी उपलब्ध नहीं है",
    )

    score = risk.get("score", 0)

    reasons = risk.get("reasons") or []

    reason_map = {
        "No major risk indicators found from current records.":
            "वर्तमान रिकॉर्ड में कोई प्रमुख जोखिम संकेत नहीं मिले हैं।",
    }

    response = (
        f"{name} की स्वास्थ्य स्थिति {risk_text} है। "
        f"जोखिम स्कोर {score} है।"
    )

    if reasons:
        reason = reason_map.get(
            reasons[0],
            reasons[0],
        )
        response += f" {reason}"

    if next_actions:
        action_map = {
            "Continue regular monthly follow-up.":
                "नियमित मासिक फॉलो-अप जारी रखें।",
        }

        action = action_map.get(
            next_actions[0],
            next_actions[0],
        )

        response += f" अगला सुझाव है कि {action}"

    return response


# ============================================================
# VOICE COMMAND
# ============================================================

@router.post("/command")
async def process_command(
    request: CommandRequest,
    authorization: str | None = Header(default=None),
):

    result = detect_intent(request.text)

    intent = result["intent"]
    entities = result.get("entities", {})

    # --------------------------------------------------------
    # AUTHENTICATION
    # --------------------------------------------------------

    if not authorization:

        return {
            "success": False,
            "intent": intent,
            "error": "Authentication required",
            "message": (
                "ASHA Connect authentication token "
                "is required."
            ),
        }

    # ========================================================
    # APPOINTMENTS
    # ========================================================

    if intent == "appointments.list":

        try:

            data = await list_appointments(
                authorization=authorization,
                date=entities.get("date"),
            )

            response = format_appointments(
                data,
                entities.get("date_label"),
            )

            return {
                "success": True,
                "input": request.text,
                "intent": intent,
                "confidence": result["confidence"],
                "entities": entities,
                "normalized_text": result["normalized_text"],
                "response": response,
                "data": data,
            }

        except httpx.HTTPStatusError as exc:

            return {
                "success": False,
                "intent": intent,
                "error": "ASHA backend error",
                "status_code": exc.response.status_code,
            }

        except Exception as exc:

            return {
                "success": False,
                "intent": intent,
                "error": "Could not connect to ASHA backend",
                "details": str(exc),
            }

    # ========================================================
    # BENEFICIARY PROFILE
    # ========================================================

    if intent == "beneficiary.profile":

        try:
            person_name = entities.get("person_name")

            if not person_name:
                return {
                    "success": False,
                    "intent": intent,
                    "error": "Beneficiary name is required",
                    "response": "कृपया लाभार्थी का नाम बताइए।",
                }

            # ------------------------------------------------
            # Resolve beneficiary name against backend records
            # ------------------------------------------------

            beneficiaries_data = await list_beneficiaries(
                {},
                authorization,
            )

            if isinstance(beneficiaries_data, dict):
                beneficiaries = (
                    beneficiaries_data.get("beneficiaries")
                    or beneficiaries_data.get("data")
                    or beneficiaries_data.get("items")
                    or []
                )
            elif isinstance(beneficiaries_data, list):
                beneficiaries = beneficiaries_data
            else:
                beneficiaries = []

            target = person_name.strip().lower()

            beneficiary = None

            for person in beneficiaries:

                candidate_names = [
                    person.get("full_name"),
                    person.get("name"),
                    person.get("beneficiary_name"),
                ]

                for candidate in candidate_names:

                    if candidate and candidate.strip().lower() == target:
                        beneficiary = person
                        break

                if beneficiary:
                    break

            # ------------------------------------------------
            # Beneficiary not found
            # ------------------------------------------------

            if not beneficiary:

                return {
                    "success": False,
                    "input": request.text,
                    "intent": intent,
                    "confidence": result["confidence"],
                    "entities": entities,
                    "normalized_text": result["normalized_text"],
                    "response": (
                        f"{person_name} नाम का लाभार्थी नहीं मिला।"
                    ),
                }

            beneficiary_id = (
                beneficiary.get("beneficiary_id")
                or beneficiary.get("id")
            )

            if not beneficiary_id:

                return {
                    "success": False,
                    "intent": intent,
                    "error": "Beneficiary ID not found",
                    "response": (
                        "लाभार्थी की पहचान तो मिली, "
                        "लेकिन प्रोफाइल आईडी उपलब्ध नहीं है।"
                    ),
                }

            # ------------------------------------------------
            # Load complete health profile
            # ------------------------------------------------

            profile = await get_beneficiary_profile(
                {
                    "beneficiary_id": beneficiary_id
                },
                authorization,
            )

            # ------------------------------------------------
            # Build natural voice response
            # ------------------------------------------------

            beneficiary_info = profile.get(
                "beneficiary",
                {}
            )

            risk = profile.get(
                "risk",
                {}
            )

            next_actions = profile.get(
                "next_actions",
                []
            )

            name = (
                beneficiary_info.get("full_name")
                or beneficiary_info.get("name")
                or person_name
            )

            risk_level = risk.get(
                "level",
                "जानकारी उपलब्ध नहीं है"
            )

            risk_score = risk.get(
                "score",
                0
            )

            reasons = risk.get(
                "reasons",
                []
            )

            response = (
                f"{name} की स्वास्थ्य स्थिति {risk_level} है। "
                f"जोखिम स्कोर {risk_score} है।"
            )

            if reasons:
                response += f" {reasons[0]}"

            if next_actions:
                response += f" अगला सुझाव: {next_actions[0]}"

            return {
                "success": True,
                "input": request.text,
                "intent": intent,
                "confidence": result["confidence"],
                "entities": entities,
                "normalized_text": result["normalized_text"],
                "response": response,
                "data": profile,
            }

        except httpx.HTTPStatusError as exc:

            return {
                "success": False,
                "intent": intent,
                "error": "ASHA backend error",
                "status_code": exc.response.status_code,
            }

        except Exception as exc:

            return {
                "success": False,
                "intent": intent,
                "error": "Could not load beneficiary profile",
                "details": str(exc),
            }

    # ========================================================
    # BENEFICIARIES
    # ========================================================

    if intent == "beneficiary.lookup":

        try:

            data = await list_beneficiaries(
                authorization=authorization,
            )

            return {
                "success": True,
                "input": request.text,
                "intent": intent,
                "confidence": result["confidence"],
                "entities": entities,
                "normalized_text": result["normalized_text"],
                "response": format_beneficiaries(data),
                "data": data,
            }

        except Exception as exc:

            return {
                "success": False,
                "intent": intent,
                "error": "Could not load beneficiaries",
                "details": str(exc),
            }

    # ========================================================
    # PREGNANCY
    # ========================================================

    if intent == "pregnancy.list":

        try:

            data = await list_pregnancy_records(
                authorization=authorization,
            )

            response = (
                "गर्भावस्था से जुड़े रिकॉर्ड मिल गए हैं।"
                if data
                else "कोई गर्भावस्था रिकॉर्ड नहीं मिला।"
            )

            return {
                "success": True,
                "intent": intent,
                "confidence": result["confidence"],
                "entities": entities,
                "normalized_text": result["normalized_text"],
                "response": response,
                "data": data,
            }

        except Exception as exc:

            return {
                "success": False,
                "intent": intent,
                "error": "Could not load pregnancy records",
                "details": str(exc),
            }

    # ========================================================
    # IMMUNIZATION
    # ========================================================

    if intent == "immunization.list":

        try:

            data = await list_immunization_records(
                authorization=authorization,
            )

            response = (
                "टीकाकरण के रिकॉर्ड मिल गए हैं।"
                if data
                else "कोई टीकाकरण रिकॉर्ड नहीं मिला।"
            )

            return {
                "success": True,
                "intent": intent,
                "confidence": result["confidence"],
                "entities": entities,
                "normalized_text": result["normalized_text"],
                "response": response,
                "data": data,
            }

        except Exception as exc:

            return {
                "success": False,
                "intent": intent,
                "error": "Could not load immunization records",
                "details": str(exc),
            }

    # ========================================================
    # REMINDERS
    # ========================================================

    if intent == "reminders.run":

        try:

            data = await run_reminders(
                authorization=authorization,
            )

            return {
                "success": True,
                "intent": intent,
                "confidence": result["confidence"],
                "entities": entities,
                "normalized_text": result["normalized_text"],
                "response": (
                    "रिमाइंडर प्रक्रिया पूरी हो गई है।"
                ),
                "data": data,
            }

        except Exception as exc:

            return {
                "success": False,
                "intent": intent,
                "error": "Could not run reminders",
                "details": str(exc),
            }

    # ========================================================
    # MESSAGES
    # ========================================================

    if intent == "messages.list":

        try:

            data = await list_care_messages(
                authorization=authorization,
            )

            return {
                "success": True,
                "intent": intent,
                "confidence": result["confidence"],
                "entities": entities,
                "normalized_text": result["normalized_text"],
                "response": (
                    "मैसेज और रिमाइंडर की सूची मिल गई है।"
                    if data
                    else "कोई pending message नहीं है।"
                ),
                "data": data,
            }

        except Exception as exc:

            return {
                "success": False,
                "intent": intent,
                "error": "Could not load messages",
                "details": str(exc),
            }

    # ========================================================
    # REPORTS
    # ========================================================

    if intent == "reports.list":

        try:

            data = await list_reports(
                authorization=authorization,
            )

            return {
                "success": True,
                "intent": intent,
                "confidence": result["confidence"],
                "entities": entities,
                "normalized_text": result["normalized_text"],
                "response": (
                    "रिपोर्ट की सूची मिल गई है।"
                    if data
                    else "कोई रिपोर्ट नहीं मिली।"
                ),
                "data": data,
            }

        except Exception as exc:

            return {
                "success": False,
                "intent": intent,
                "error": "Could not load reports",
                "details": str(exc),
            }

    # ========================================================
    # UNKNOWN
    # ========================================================

    return {
        "success": True,
        "input": request.text,
        "intent": intent,
        "confidence": result["confidence"],
        "entities": entities,
        "normalized_text": result["normalized_text"],
        "response": (
            "मैं आपकी बात समझ नहीं पाई। "
            "आप अपॉइंटमेंट, लाभार्थी, रिपोर्ट, "
            "टीकाकरण या रिमाइंडर के बारे में पूछ सकते हैं।"
        ),
    }

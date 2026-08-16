import os
import json

from google import genai
from google.genai import types

from app.agent.intent import detect_date
from app.agent.tools.asha import execute_asha_action
from app.agent.core.state import (
    set_pending_action,
    get_pending_action,
    clear_pending_action,
)
from app.agent.core.confirmation import (
    requires_confirmation,
    detect_confirmation,
    confirmation_message,
)


api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise RuntimeError("GEMINI_API_KEY is not set")


client = genai.Client(api_key=api_key)


asha_tool = types.Tool(
    function_declarations=[
        types.FunctionDeclaration(
            name="execute_asha_action",
            description=(
                "Execute an authenticated ASHA Connect operation. "
                "Use this tool whenever the ASHA worker wants to "
                "retrieve, create, update, delete, schedule, manage "
                "reminders, or generate reports. "
                "Never invent database information."
            ),
            parameters=types.Schema(
                type="OBJECT",
                properties={
                    "action": types.Schema(
                        type="STRING",
                        description=(
                            "Allowed ASHA Connect action name."
                        ),
                    ),
                    "payload": types.Schema(
                        type="STRING",
                        description=(
                            "JSON object containing the parameters "
                            "required by the selected action."
                        ),
                    ),
                },
                required=[
                    "action",
                    "payload",
                ],
            ),
        )
    ]
)


ACTION_REFERENCE = """
ASHA CONNECT ACTIONS

READ:

list_appointments
- Get appointments.
- payload example:
  {"date":"2026-06-26"}

list_beneficiaries
- List beneficiaries.
- payload: {}

get_beneficiary_profile
- Get beneficiary profile.
- payload:
  {"beneficiary_id":23}

list_pregnancy_records
- Get pregnancy records.
- payload may contain filtering parameters.

list_immunization_records
- Get immunization records.
- payload may contain filtering parameters.

list_care_messages
- Get reminder/message queue.
- payload: {}

get_reminder_status
- Get reminder scheduler status.
- payload: {}

list_care_reports
- Get care automation reports.
- payload: {}

list_reports
- Get generated reports.
- payload: {}


WRITE:

create_appointment
- Schedule an appointment for an existing beneficiary.
- NEVER invent beneficiary_id.
- If the user gives a beneficiary name instead of beneficiary_id:
  1. call list_beneficiaries first,
  2. find the matching beneficiary from the returned database records,
  3. use that beneficiary's beneficiary_id,
  4. then call create_appointment.
- payload:
  {
    "beneficiary_id": 27,
    "appointment_date": "YYYY-MM-DD",
    "appointment_time": "HH:MM",
    "appointment_type": "Follow-up Visit",
    "notes": ""
  }
- appointment_type may be omitted when the user does not specify one;
  the backend defaults it to Follow-up Visit.
- If the appointment date is supplied by the deterministic date resolver,
  use that exact date and NEVER change its year.
- If appointment time is genuinely required but the user did not provide it,
  ask the user naturally for the time instead of inventing one.

create_beneficiary
- Add a new beneficiary.
- payload contains the beneficiary information.

update_beneficiary
- Update beneficiary.
- payload:
  {"beneficiary_id":23,...fields to update...}

delete_beneficiary
- Delete beneficiary.
- payload:
  {"beneficiary_id":23}

create_pregnancy_record
- Add pregnancy record.

create_immunization_record
- Add immunization record.

run_reminders
- Run reminders immediately.
- payload: {}

run_auto_reminders
- Run automatic reminder process.
- payload: {}

mark_message_sent
- Mark a message as sent.
- payload:
  {"message_id":123}

generate_individual_report
- Generate an individual beneficiary report.

generate_family_report
- Generate a family report.

generate_phc_summary
- Generate PHC-wide family summary.

generate_report
- Generate a general report.
"""


SYSTEM_PROMPT = f"""
You are ASHA Connect, an intelligent voice assistant
for ASHA healthcare workers.

You understand Hindi, Nepali and English.

Your job is to act like a helpful human assistant.

You can:

- manage appointments
- find beneficiaries
- manage beneficiary records
- manage pregnancy records
- manage immunization records
- run reminders
- inspect message queues
- generate reports
- manage other ASHA Connect operations

{ACTION_REFERENCE}

IMPORTANT RULES:

1. Never invent database information.

2. Use execute_asha_action whenever information must come
   from ASHA Connect.

3. Use execute_asha_action for database operations.

4. Never claim an operation succeeded unless the backend
   tool returned successfully.

5. Keep responses short and natural because the response
   will eventually be spoken through TTS.

6. Respond in the same language as the ASHA worker when possible.

7. For destructive operations such as deleting a beneficiary,
   ask for confirmation before executing.

8. ALL write operations require explicit user confirmation
   before execution. This includes appointments, beneficiaries,
   health records, reminders, messages and report generation.
   Never execute a write operation before confirmation.

9. Never expose technical implementation details to the ASHA worker.

10. DATE RULE:
    Dates are resolved by ASHA Connect's deterministic date parser.
    If the system provides a resolved date, NEVER change its year.

11. If the user says something conversational like:
    "कल किसका अपॉइंटमेंट है?"
    resolve the date and use the appointment tool.

12. If required information is missing, ask a natural follow-up question.

13. BENEFICIARY RESOLUTION RULE:
    Users normally identify beneficiaries by name, not database ID.
    For any operation requiring beneficiary_id, first use
    list_beneficiaries when the ID is not already known.
    Match the requested person's name only against actual returned
    beneficiary records. Never fabricate an ID.

14. APPOINTMENT WORKFLOW:
    For requests such as:
    "कल Kanjira Gurung का appointment schedule करो"
    or
    "Schedule Kanjira Gurung's appointment tomorrow":
    - resolve the date using the deterministic resolved date,
    - call list_beneficiaries,
    - identify the beneficiary,
    - obtain beneficiary_id from the tool result,
    - then call create_appointment.
    If essential information is still missing, ask a short follow-up.
    Do not fail merely because the user spoke a name instead of an ID.

15. MULTI-STEP RULE:
    You may call execute_asha_action multiple times to complete one
    user request. Results from an earlier tool call may be used to
    construct the payload of a later tool call.

16. DATABASE SAFETY:
    Never guess beneficiary_id, message_id, report identifiers,
    pregnancy IDs, immunization IDs, appointment IDs, or any other
    database identifier. Resolve them from ASHA Connect first.
"""


async def ask_gemini(
    text: str,
    authorization: str | None = None,
):

    if not authorization:
        raise ValueError(
            "ASHA Connect authentication token is required."
        )

    # --------------------------------------------------
    # Pending write confirmation
    # --------------------------------------------------

    pending = get_pending_action(authorization)

    if pending:

        decision = detect_confirmation(text)

        if decision is True:

            clear_pending_action(authorization)

            action_result = await execute_asha_action(
                action=pending["action"],
                payload=pending["payload"],
                authorization=authorization,
            )

            hindi = any(
                "\u0900" <= ch <= "\u097f"
                for ch in text
            )

            return {
                "type": "action_executed",
                "action": pending["action"],
                "response": (
                    "कार्य सफलतापूर्वक पूरा हो गया है।"
                    if hindi
                    else "The action was completed successfully."
                ),
                "data": action_result,
            }

        if decision is False:

            clear_pending_action(authorization)

            hindi = any(
                "\u0900" <= ch <= "\u097f"
                for ch in text
            )

            return {
                "type": "action_cancelled",
                "action": pending["action"],
                "response": (
                    "ठीक है, कार्रवाई रद्द कर दी गई है।"
                    if hindi
                    else "Okay, the action has been cancelled."
                ),
            }

        hindi = any(
            "\u0900" <= ch <= "\u097f"
            for ch in text
        )

        return {
            "type": "confirmation_required",
            "action": pending["action"],
            "response": (
                "कृपया हाँ या नहीं में पुष्टि करें।"
                if hindi
                else "Please confirm yes or no before I continue."
            ),
            "pending": True,
        }


    # --------------------------------------------------
    # Deterministic date resolution
    # --------------------------------------------------

    date_info = detect_date(text)

    resolved_date = None

    if date_info:
        resolved_date = date_info.get("date")


    date_context = ""

    if resolved_date:

        date_context = (
            f"\nSYSTEM RESOLVED DATE: {resolved_date}\n"
            "Use this exact date. Do not change the year.\n"
        )


    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part(
                    text=text + date_context
                )
            ],
        )
    ]


    config = types.GenerateContentConfig(
        tools=[asha_tool],
        system_instruction=SYSTEM_PROMPT,
    )


    # --------------------------------------------------
    # Agent loop
    # --------------------------------------------------

    max_turns = 5

    for _ in range(max_turns):

        response = client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=contents,
            config=config,
        )


        function_calls = []

        for candidate in response.candidates or []:

            content = candidate.content

            if not content:
                continue

            for part in content.parts or []:

                if part.function_call:
                    function_calls.append(
                        part.function_call
                    )


        # No more tools required
        if not function_calls:

            return {
                "type": "text",
                "response": response.text,
                "resolved_date": resolved_date,
            }


        # Preserve Gemini's tool call
        contents.append(
            response.candidates[0].content
        )


        tool_parts = []


        for call in function_calls:

            if call.name != "execute_asha_action":
                continue


            args = dict(call.args or {})

            action = args.get("action")

            payload_raw = args.get(
                "payload",
                "{}",
            )


            try:

                payload = json.loads(
                    payload_raw
                )

            except Exception:

                payload = {}


            # Force deterministic date into appointment requests
            if (
                action == "list_appointments"
                and resolved_date
            ):

                payload["date"] = resolved_date


            # --------------------------------------------------
            # Never execute write operations immediately.
            # Store them and require explicit confirmation.
            # --------------------------------------------------

            if requires_confirmation(action):

                set_pending_action(
                    authorization=authorization,
                    action=action,
                    payload=payload,
                )

                hindi = any(
                    "\u0900" <= ch <= "\u097f"
                    for ch in text
                )

                return {
                    "type": "confirmation_required",
                    "action": action,
                    "payload": payload,
                    "response": confirmation_message(
                        action,
                        payload,
                        hindi=hindi,
                    ),
                    "resolved_date": resolved_date,
                }


            result = await execute_asha_action(
                action=action,
                payload=payload,
                authorization=authorization,
            )


            tool_parts.append(
                types.Part(
                    function_response=types.FunctionResponse(
                        name="execute_asha_action",
                        response={
                            "action": action,
                            "result": result,
                        },
                    )
                )
            )


        contents.append(
            types.Content(
                role="user",
                parts=tool_parts,
            )
        )


    return {
        "type": "error",
        "response": (
            "माफ़ कीजिए, मैं इस अनुरोध को पूरा नहीं कर पाई।"
        ),
    }

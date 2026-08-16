import asyncio
import json
import os

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from google import genai
from google.genai import types

from app.agent.tools.asha import execute_asha_action


router = APIRouter(
    prefix="/voice",
    tags=["Gemini Live Voice"],
)


MODEL = os.getenv(
    "GEMINI_LIVE_MODEL",
    "gemini-3.1-flash-live-preview",
)


api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise RuntimeError("GEMINI_API_KEY is not set")


client = genai.Client(
    api_key=api_key,
)


TOOL_DECLARATIONS = [
    {
        "name": "execute_asha_action",
        "description": (
            "Execute an authenticated ASHA Connect database operation. "
            "Use this whenever information must be read from or changed "
            "in ASHA Connect. Never invent database identifiers."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "enum": [
                        "resolve_beneficiary",
                        "get_beneficiary_profile",
                        "list_beneficiaries",
                        "list_appointments",
                        "create_appointment",
                        "list_pregnancy_records",
                        "list_immunization_records",
                        "list_care_messages",
                        "get_reminder_status",
                        "list_care_reports",
                        "list_reports",
                        "generate_individual_report",
                        "generate_family_report",
                        "generate_phc_summary",
                        "run_reminders",
                        "run_auto_reminders",
                        "mark_message_sent"
                    ],
                    "description": (
                        "Exact ASHA Connect action. "
                        "For beneficiary details or health status use "
                        "get_beneficiary_profile. "
                        "For resolving a spoken name use resolve_beneficiary."
                    ),
                },
                "payload": {
                    "type": "OBJECT",
                    "description": (
                        "Parameters required by the selected ASHA action."
                    ),
                },
            },
            "required": [
                "action",
                "payload",
            ],
        },
    }
]


SYSTEM_INSTRUCTION = """
You are ASHA Connect, a realtime voice assistant for ASHA healthcare workers.

Speak naturally and briefly.

VOICE UX:
- Do not repeatedly greet the worker during an active session.
- Do not give generic menus such as "beneficiary ya koi dusra kaam".
- Respond directly to the current request.
- Prefer one or two short spoken sentences.
- When using records, say only verified information returned by tools.

Understand Hindi, Hinglish, Nepali and English.

AVAILABLE BENEFICIARY RESOLUTION:

resolve_beneficiary
- payload: {"name": "Kanjira Gurung"}
- Resolves spoken beneficiary names against actual database records.
- Handles Hindi/Hinglish transliteration and minor STT variation.
- Returns beneficiary_id and canonical database name.
- Use this instead of guessing IDs.

CRITICAL TOOL GROUNDING RULE:

- You have NO independent knowledge of which beneficiaries exist in ASHA Connect.
- NEVER say that a beneficiary exists, does not exist, is listed, or is not listed
  without first calling execute_asha_action.
- For requests such as:
  "Tell me the details of Kanjira Gurung"
  "Kanjira Gurung ka health status batao"
  "Show Kanjira Gurung's record"
  call:
    action = "get_beneficiary_profile"
    payload = {"name": "<spoken beneficiary name>"}
- get_beneficiary_profile already resolves the spoken name against the real database.
- If the tool succeeds, use ONLY the returned profile.
- Only say that no record exists when the tool itself returns a genuine not-found result.
- Never infer database absence from conversation context or model knowledge.

NAME AND DATABASE GROUNDING — MANDATORY:

- Speech transcription is NOT proof of a beneficiary's canonical name.
- NEVER conclude that a person is absent from ASHA Connect based only on
  the spoken/transcribed name.
- Whenever a beneficiary name is mentioned, first call:
    action = "resolve_beneficiary"
    payload = {"name": "<name exactly as heard>"}
- Use the canonical name and beneficiary_id returned by the resolver.
- After successful resolution, use get_beneficiary_profile for details.
- If spelling/pronunciation differs slightly, trust the database resolver,
  not your own spelling assumptions.
- Example: a spoken "Aarav Kshetri" may correspond to database
  "Aarav Chettri"; resolve it through the tool rather than rejecting it.
- Only state that no beneficiary exists when resolve_beneficiary explicitly
  returns found=false with no sufficiently plausible candidate.
- If the result is ambiguous, ask which returned candidate the worker means.
- Never fabricate a replacement name.
- Never expose raw backend exceptions to the ASHA worker.

ASHA CONNECT OPERATION MAP:

Beneficiaries:
- list_beneficiaries
- resolve_beneficiary
- get_beneficiary_profile
- create_beneficiary
- update_beneficiary_ai
- delete_beneficiary_ai

Appointments:
- list_appointments
- create_appointment
- update_appointment
- delete_appointment

Notices:
- list_notices
- create_notice

Pregnancy:
- list_pregnancy_records
- create_pregnancy_record

Immunization:
- list_immunization_records
- create_immunization_record

Reports:
- list_reports
- list_care_reports
- generate_individual_report
- generate_family_report
- generate_phc_summary

Reminders:
- get_reminder_status
- run_reminders
- run_auto_reminders

Messages:
- list_care_messages
- mark_message_sent

OPERATION RULES:

- Always use tools for ASHA Connect data.
- Never claim an operation succeeded unless the tool returned success.
- Spoken beneficiary names may be used; the gateway resolves them.
- For update/delete operations, first resolve the relevant record.
- Before deleting a beneficiary or appointment, ask for confirmation.
- Before important writes such as creating appointments or publishing
  notices, confirm when details are ambiguous.
- After successful writes, continue the same voice session.
- Never expose backend exceptions directly to the worker.

IMPORTANT DATABASE RULES:

- Never invent beneficiary information.
- Never invent database IDs.
- Use execute_asha_action whenever data must come from ASHA Connect.
- If a beneficiary is mentioned by name, use the
  resolve_beneficiary action to resolve the spoken name against
  the actual ASHA Connect database.
- Never perform your own guessed name-to-ID mapping.
- The resolver supports Hindi/Hinglish pronunciation variations,
  transliteration and minor STT spelling differences.
- Use returned database records as the source of truth.

APPOINTMENTS:
- Resolve the beneficiary using resolve_beneficiary first whenever
  the person's identity is not already established.
- create_appointment also accepts beneficiary_name and performs
  database resolution as a safety fallback.
- Use exact date supplied by the application when available.
- Never invent appointment time.
- If time is missing, ask the worker naturally.

WRITES:
- Do not claim success unless the backend tool succeeded.
- Before destructive or important write operations, ask for confirmation.
- Keep confirmations short.

REPORTS:
- Resolve beneficiary or family before generating the report.
- Never claim a report was sent unless the backend/message operation succeeded.

BENEFICIARY CONTEXT RESOLUTION:

- If a beneficiary name is unclear but the worker provides a family,
  village, household or address, call resolve_beneficiary with both.
- Example:
  {
    "action": "resolve_beneficiary",
    "payload": {
      "name": "Sulika Gurung",
      "family_name": "Dhan Bdr Gurung Family"
    }
  }
- Never ask the ASHA worker for beneficiary_id when a name/family lookup
  can resolve the person from the database.
- Never ask for contact number or registration number before attempting
  name + family resolution.
- Prefer the canonical beneficiary name returned by the tool.

CONVERSATION MEMORY:

- This is one continuous conversation until the worker ends the session.
- Preserve the currently discussed beneficiary across turns.
- If the worker says "iska", "iski", "isko", "uska", "uski",
  "his", "her", "them", or similar references, use the beneficiary
  established in the immediately preceding conversation when unambiguous.
- If the reference could mean more than one person, ask for clarification.
- Do not force the worker to repeat the beneficiary name unnecessarily.

APPOINTMENT WORKFLOW:

- Workers normally speak beneficiary names, not database IDs.
- create_appointment may receive beneficiary_name directly.
- Example:
  {
    "action": "create_appointment",
    "payload": {
      "beneficiary_name": "Kanjira Gurung",
      "appointment_date": "YYYY-MM-DD",
      "appointment_time": "10:00",
      "appointment_type": "Follow-up Visit"
    }
  }
- Never fabricate a person.
- If time is omitted, ask for it naturally.
- If the beneficiary is ambiguous, ask which beneficiary.
- Important writes require confirmation before execution.

MULTI-STEP CONVERSATION:

- After completing one operation, stay available for the next spoken request.
- Never end the conversation simply because one answer has been given.
- Use tool results from earlier turns as conversational context.
- A later request such as "iski report bana do" refers to the active
  beneficiary when that reference is unambiguous.

You are an operational assistant, not a medical diagnosis system.
Do not invent diagnoses.
"""


@router.websocket("/live")
async def gemini_live_socket(websocket: WebSocket):

    await websocket.accept()

    authorization = websocket.headers.get("authorization")

    # Browser WebSocket clients cannot set arbitrary Authorization
    # headers, so allow the logged-in ASHA JWT through the query
    # string for the local/MVP implementation.
    if not authorization:
        token = websocket.query_params.get("token")
        if token:
            authorization = f"Bearer {token}"

    if not authorization:
        await websocket.send_json(
            {
                "type": "error",
                "message": "Authentication required",
            }
        )
        await websocket.close(code=4401)
        return

    config = {
        "response_modalities": ["AUDIO"],

        # Keep written transcripts in the UI while using
        # Gemini native speech/audio.
        "input_audio_transcription": {},
        "output_audio_transcription": {},

        # Continuous conversational audio.
        # Gemini automatically detects when the worker
        # starts/stops speaking.
        "realtime_input_config": {
            "automatic_activity_detection": {
                "disabled": False,
                "prefix_padding_ms": 40,
                "silence_duration_ms": 500,
            }
        },

        "system_instruction": SYSTEM_INSTRUCTION,

        "tools": [
            {
                "function_declarations": TOOL_DECLARATIONS
            }
        ],
    }

    try:

        async with client.aio.live.connect(
            model=MODEL,
            config=config,
        ) as session:

            await websocket.send_json(
                {
                    "type": "live_ready",
                    "model": MODEL,
                }
            )


            async def receive_browser():

                while True:

                    message = await websocket.receive()

                    if message.get("bytes") is not None:

                        audio_bytes = message["bytes"]

                        await session.send_realtime_input(
                            audio=types.Blob(
                                data=audio_bytes,
                                mime_type="audio/pcm;rate=16000",
                            )
                        )

                        continue


                    text = message.get("text")

                    if not text:
                        continue

                    try:
                        payload = json.loads(text)
                    except Exception:
                        payload = {
                            "type": "text",
                            "text": text,
                        }


                    message_type = payload.get("type")


                    if message_type == "text":

                        await session.send_client_content(
                            turns=types.Content(
                                role="user",
                                parts=[
                                    types.Part(
                                        text=payload.get("text", "")
                                    )
                                ],
                            ),
                            turn_complete=True,
                        )


                    elif message_type == "audio_end":
                        # Continuous mode:
                        # silence/VAD ends a conversational turn.
                        # Do NOT terminate the Gemini audio stream.
                        continue


            async def receive_gemini():

                # session.receive() represents the current
                # Gemini model turn. When that turn completes,
                # call receive() again so the Live session
                # remains available for turn 2, 3, 4, ...
                while True:

                    async for message in session.receive():

                            # -----------------------------------------
                            # Input transcription
                        # -----------------------------------------

                        if (
                            message.server_content
                            and message.server_content.input_transcription
                        ):

                            transcript = (
                                message.server_content
                                .input_transcription
                                .text
                            )

                            if transcript:
                                await websocket.send_json(
                                    {
                                        "type": "input_transcript",
                                        "text": transcript,
                                    }
                                )


                        # -----------------------------------------
                        # Output transcription
                        # -----------------------------------------

                        if (
                            message.server_content
                            and message.server_content.output_transcription
                        ):

                            transcript = (
                                message.server_content
                                .output_transcription
                                .text
                            )

                            if transcript:
                                await websocket.send_json(
                                    {
                                        "type": "output_transcript",
                                        "text": transcript,
                                    }
                                )


                        # -----------------------------------------
                        # Native audio from Gemini
                        # -----------------------------------------

                        if message.data:

                            await websocket.send_bytes(
                                message.data
                            )


                        # -----------------------------------------
                        # Gemini tool call
                        # -----------------------------------------

                        if message.tool_call:

                            responses = []

                            for call in message.tool_call.function_calls:

                                try:

                                    args = dict(call.args or {})

                                    action = args.get("action")
                                    payload = args.get("payload") or {}

                                    print("\n========== GEMINI LIVE TOOL ==========")
                                    print("ACTION :", action)
                                    print("PAYLOAD:", payload)
                                    print("======================================\n")

                                    print("\n========== GEMINI LIVE TOOL ==========")
                                    print("ACTION :", action)
                                    print("PAYLOAD:", payload)

                                    result = await execute_asha_action(
                                        action=action,
                                        payload=payload,
                                        authorization=authorization,
                                    )

                                    print("RESULT :", result)
                                    print("======================================\n")

                                    response_data = {
                                        "ok": True,
                                        "result": result,
                                    }

                                    WRITE_ACTIONS = {
                                        "create_beneficiary",
                                        "update_beneficiary_ai",
                                        "delete_beneficiary_ai",
                                        "create_appointment",
                                        "update_appointment",
                                        "delete_appointment",
                                        "create_notice",
                                        "create_pregnancy_record",
                                        "create_immunization_record",
                                        "generate_individual_report",
                                        "generate_family_report",
                                        "generate_phc_summary",
                                        "run_reminders",
                                        "run_auto_reminders",
                                        "mark_message_sent",
                                    }

                                    if action in WRITE_ACTIONS:
                                        await websocket.send_json(
                                            {
                                                "type": "action_executed",
                                                "action": action,
                                                "success": True,
                                            }
                                        )

                                except Exception as exc:

                                    print("\n========== GEMINI LIVE TOOL ERROR ==========")
                                    print("ACTION :", locals().get("action"))
                                    print("PAYLOAD:", locals().get("payload"))
                                    print("ERROR  :", repr(exc))
                                    print("=============================================\n")

                                    response_data = {
                                        "ok": False,
                                        "error": str(exc),
                                    }


                                responses.append(
                                    types.FunctionResponse(
                                        id=call.id,
                                        name=call.name,
                                        response=response_data,
                                    )
                                )


                            await session.send_tool_response(
                                function_responses=responses
                            )

            await asyncio.gather(
                receive_browser(),
                receive_gemini(),
            )


    except WebSocketDisconnect:
        pass

    except Exception as exc:

        try:
            await websocket.send_json(
                {
                    "type": "error",
                    "message": str(exc),
                }
            )
        except Exception:
            pass

        try:
            await websocket.close()
        except Exception:
            pass

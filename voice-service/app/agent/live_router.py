import asyncio
import json
import os
import httpx

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from google import genai
from google.genai import types

from app.agent.tools.asha import execute_asha_action


router = APIRouter(prefix="/voice", tags=["Gemini Live Voice"])

MODEL = os.getenv("GEMINI_LIVE_MODEL", "gemini-3.1-flash-live-preview")
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise RuntimeError("GEMINI_API_KEY is not set")

client = genai.Client(api_key=api_key)


TOOL_DECLARATIONS = [
    {
        "name": "resolve_beneficiary",
        "description": "Resolve a beneficiary name against the real ASHA Connect database. Never ask the worker for beneficiary_id before using this.",
        "parameters": {
            "type": "OBJECT",
            "properties": {"name": {"type": "STRING"}},
            "required": ["name"],
        },
    },
    {
        "name": "get_beneficiary_profile",
        "description": "Fetch verified beneficiary details. Prefer the spoken beneficiary name; never ask the worker for an internal ID.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "name": {"type": "STRING"},
                "beneficiary_id": {"type": "INTEGER"},
            },
        },
    },
    {
        "name": "list_beneficiaries",
        "description": "List beneficiaries visible to the logged-in ASHA worker.",
        "parameters": {"type": "OBJECT", "properties": {}},
    },
    {
        "name": "create_beneficiary",
        "description": "Create a beneficiary from worker-provided fields.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "name": {"type": "STRING"},
                "phone": {"type": "STRING"},
                "village": {"type": "STRING"},
                "address": {"type": "STRING"},
                "age": {"type": "INTEGER"},
                "gender": {"type": "STRING"},
                "family_id": {"type": "INTEGER"},
            },
            "required": ["name"],
        },
    },
    {
        "name": "update_beneficiary_ai",
        "description": "Update an existing beneficiary by human-readable name or already-resolved internal ID.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "beneficiary_name": {"type": "STRING"},
                "beneficiary_id": {"type": "INTEGER"},
                "updates": {"type": "OBJECT"},
            },
        },
    },
    {
        "name": "delete_beneficiary_ai",
        "description": "Delete a beneficiary after explicit confirmation. Prefer beneficiary_name.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "beneficiary_name": {"type": "STRING"},
                "beneficiary_id": {"type": "INTEGER"},
            },
        },
    },
    {
        "name": "list_appointments",
        "description": "List appointments, optionally filtered.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "date": {"type": "STRING"},
                "beneficiary_name": {"type": "STRING"},
                "beneficiary_id": {"type": "INTEGER"},
            },
        },
    },
    {
        "name": "create_appointment",
        "description": "Schedule an appointment. Pass beneficiary_name directly; the tool layer resolves the database ID.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "beneficiary_name": {"type": "STRING"},
                "beneficiary_id": {"type": "INTEGER"},
                "appointment_date": {"type": "STRING"},
                "appointment_time": {"type": "STRING"},
                "appointment_type": {"type": "STRING"},
                "notes": {"type": "STRING"},
            },
            "required": ["appointment_date", "appointment_time", "appointment_type"],
        },
    },
    {
        "name": "update_appointment",
        "description": "Update or reschedule an appointment.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "appointment_id": {"type": "INTEGER"},
                "beneficiary_name": {"type": "STRING"},
                "appointment_date": {"type": "STRING"},
                "appointment_time": {"type": "STRING"},
                "appointment_type": {"type": "STRING"},
                "notes": {"type": "STRING"},
                "status": {"type": "STRING"},
            },
        },
    },
    {
        "name": "delete_appointment",
        "description": "Delete/cancel an appointment after explicit confirmation.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "appointment_id": {"type": "INTEGER"},
                "beneficiary_name": {"type": "STRING"},
            },
        },
    },
    {
        "name": "list_pregnancy_records",
        "description": "List pregnancy records.",
        "parameters": {"type": "OBJECT", "properties": {"beneficiary_name": {"type": "STRING"}, "beneficiary_id": {"type": "INTEGER"}}},
    },
    {
        "name": "create_pregnancy_record",
        "description": "Create a pregnancy record.",
        "parameters": {"type": "OBJECT", "properties": {"beneficiary_name": {"type": "STRING"}, "beneficiary_id": {"type": "INTEGER"}, "lmp_date": {"type": "STRING"}, "edd": {"type": "STRING"}, "notes": {"type": "STRING"}}},
    },
    {
        "name": "list_immunization_records",
        "description": "List immunization records.",
        "parameters": {"type": "OBJECT", "properties": {"beneficiary_name": {"type": "STRING"}, "beneficiary_id": {"type": "INTEGER"}}},
    },
    {
        "name": "create_immunization_record",
        "description": "Create an immunization record.",
        "parameters": {"type": "OBJECT", "properties": {"beneficiary_name": {"type": "STRING"}, "beneficiary_id": {"type": "INTEGER"}, "vaccine_name": {"type": "STRING"}, "due_date": {"type": "STRING"}, "given_date": {"type": "STRING"}, "notes": {"type": "STRING"}}},
    },
    {
        "name": "list_reports",
        "description": "List generated reports.",
        "parameters": {"type": "OBJECT", "properties": {}},
    },
    {
        "name": "list_care_reports",
        "description": "List care automation reports.",
        "parameters": {"type": "OBJECT", "properties": {}},
    },
    {
        "name": "generate_individual_report",
        "description": "Generate an individual beneficiary report.",
        "parameters": {"type": "OBJECT", "properties": {"beneficiary_name": {"type": "STRING"}, "beneficiary_id": {"type": "INTEGER"}}},
    },
    {
        "name": "generate_family_report",
        "description": "Generate a family report.",
        "parameters": {"type": "OBJECT", "properties": {"family_id": {"type": "INTEGER"}, "family_name": {"type": "STRING"}}},
    },
    {
        "name": "generate_phc_summary",
        "description": "Generate PHC summary.",
        "parameters": {"type": "OBJECT", "properties": {}},
    },
    {
        "name": "get_reminder_status",
        "description": "Fetch reminder status.",
        "parameters": {"type": "OBJECT", "properties": {}},
    },
    {
        "name": "run_reminders",
        "description": "Run reminders now.",
        "parameters": {"type": "OBJECT", "properties": {}},
    },
    {
        "name": "run_auto_reminders",
        "description": "Run automatic reminders now.",
        "parameters": {"type": "OBJECT", "properties": {}},
    },
    {
        "name": "list_notices",
        "description": "List notices.",
        "parameters": {"type": "OBJECT", "properties": {}},
    },
    {
        "name": "create_notice",
        "description": "Create a notice.",
        "parameters": {"type": "OBJECT", "properties": {"title": {"type": "STRING"}, "message": {"type": "STRING"}}, "required": ["title", "message"]},
    },
    {
        "name": "list_care_messages",
        "description": "List care automation messages.",
        "parameters": {"type": "OBJECT", "properties": {}},
    },
    {
        "name": "mark_message_sent",
        "description": "Mark a message sent.",
        "parameters": {"type": "OBJECT", "properties": {"message_id": {"type": "INTEGER"}}, "required": ["message_id"]},
    },
]




# === VERIFIED LIVE CAPABILITY FILTER ===
VERIFIED_LIVE_ACTIONS = {
    "resolve_beneficiary",
    "get_beneficiary_profile",
    "list_beneficiaries",
    "create_beneficiary",
    "update_beneficiary_ai",
    "delete_beneficiary_ai",
    "list_appointments",
    "create_appointment",
    "list_pregnancy_records",
    "create_pregnancy_record",
    "list_immunization_records",
    "create_immunization_record",
    "list_reports",
    "list_care_reports",
    "generate_individual_report",
    "generate_family_report",
    "generate_phc_summary",
    "get_reminder_status",
    "run_reminders",
    "run_auto_reminders",
    "list_care_messages",
    "mark_message_sent",
}

TOOL_DECLARATIONS = [
    declaration
    for declaration in TOOL_DECLARATIONS
    if declaration.get("name") in VERIFIED_LIVE_ACTIONS
]
# === END VERIFIED LIVE CAPABILITY FILTER ===

SYSTEM_INSTRUCTION = r"""
You are ASHA AI inside ASHA Connect, an operational voice assistant for authenticated ASHA workers.

LANGUAGE
- Match the worker's latest language/style: Hindi, Hinglish, English or Nepali.
- Keep responses short and natural.

DATABASE FIRST
- Any beneficiary/appointment/pregnancy/immunization/report/reminder/notice/message request must use the relevant tool.
- Never answer database questions from memory.
- Never invent records, IDs, dates or operation success.
- Never ask the worker for beneficiary_id.
- When a beneficiary name is spoken, pass that name directly to the relevant tool.
- Ask a clarification only if a genuinely required human-readable field is missing or the database returns an ambiguous match.

DETAIL REQUESTS
- "X ka detail/record/profile/status batao" -> immediately call get_beneficiary_profile with {"name": "X"}.
- Do not ask for ID, family name, village or phone before trying the tool.

CONTEXT
- Preserve the latest verified beneficiary across turns.
- Pronouns like unka/uska/iski/iska/her/his refer to that beneficiary when unambiguous.
- Do not force the worker to repeat a resolved name.

APPOINTMENTS
- If beneficiary, date, time and appointment type are already present, do not ask for them again.
- Important writes may be confirmed once.
- After confirmation, execute immediately.
- Never claim success until the tool succeeds.

VOICE UX
- Do not repeatedly greet.
- Do not give generic menus.
- Do not explain IDs, JSON or internal tools.
- Give the verified result or ask only the one missing piece.
- If a tool fails, give one short failure message; no apology loops.
- Destructive delete/cancel actions require confirmation.
- Do not invent medical diagnoses.
"""


UI_OPERATIONS = {item["name"] for item in TOOL_DECLARATIONS}


@router.websocket("/live")
async def gemini_live_socket(websocket: WebSocket):
    await websocket.accept()

    authorization = websocket.headers.get("authorization")
    if not authorization:
        token = websocket.query_params.get("token")
        if token:
            authorization = f"Bearer {token}"

    if not authorization:
        await websocket.send_json({"type": "error", "message": "Authentication required"})
        await websocket.close(code=4401)
        return

    try:
        async with httpx.AsyncClient(timeout=10) as auth_client:
            response = await auth_client.get(
                os.getenv("ASHA_BACKEND_URL", "http://127.0.0.1:8000").rstrip("/") + "/api/auth/me",
                headers={"Authorization": authorization},
            )
        if response.status_code != 200:
            await websocket.close(code=4401)
            return
    except httpx.HTTPError:
        await websocket.close(code=1011)
        return

    config = {
        "response_modalities": ["AUDIO"],
        "input_audio_transcription": {},
        "output_audio_transcription": {},
        "realtime_input_config": {
            "automatic_activity_detection": {
                "disabled": False,
                "prefix_padding_ms": 40,
                "silence_duration_ms": 500,
            }
        },
        "system_instruction": SYSTEM_INSTRUCTION,
        "tools": [{"function_declarations": TOOL_DECLARATIONS}],
    }

    try:
        async with client.aio.live.connect(model=MODEL, config=config) as session:
            await websocket.send_json({"type": "live_ready", "model": MODEL})

            async def receive_browser():
                while True:
                    try:
                        message = await websocket.receive()
                    except (WebSocketDisconnect, RuntimeError) as exc:
                        if isinstance(exc, RuntimeError) and 'disconnect message' not in str(exc).lower():
                            raise
                        print('ASHA AI browser disconnected; ending receive loop')
                        return
                    if message.get('type') == 'websocket.disconnect':
                        return
                    if message.get("bytes") is not None:
                        await session.send_realtime_input(
                            audio=types.Blob(
                                data=message["bytes"],
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
                        payload = {"type": "text", "text": text}

                    message_type = payload.get("type")

                    if message_type == "text":
                        await session.send_client_content(
                            turns=types.Content(
                                role="user",
                                parts=[types.Part(text=payload.get("text", ""))],
                            ),
                            turn_complete=True,
                        )
                    elif message_type in {"audio_end", "end_session"}:
                        if message_type == "end_session":
                            return
                        continue

            async def receive_gemini():
                while True:
                    async for message in session.receive():
                        server_content = message.server_content

                        if server_content and server_content.input_transcription:
                            text = server_content.input_transcription.text
                            if text:
                                await websocket.send_json({"type": "input_transcript", "text": text})

                        if server_content and server_content.output_transcription:
                            text = server_content.output_transcription.text
                            if text:
                                await websocket.send_json({"type": "output_transcript", "text": text})

                        if message.data:
                            await websocket.send_bytes(message.data)

                        if not message.tool_call:
                            continue

                        responses = []

                        for call in message.tool_call.function_calls:
                            action = call.name
                            payload = dict(call.args or {})

                            print("\n========== ASHA LIVE TOOL ==========")
                            print("ACTION :", action)

                            try:
                                result = await execute_asha_action(
                                    action=action,
                                    payload=payload,
                                    authorization=authorization,
                                )

                                print("====================================\n")

                                response_data = {"ok": True, "result": result}

                                await websocket.send_json({
                                    "type": "action_executed",
                                    "action": action,
                                    "success": True,
                                    "payload": payload,
                                    "result": result,
                                })

                            except Exception as exc:
                                print("ERROR  :", type(exc).__name__)
                                print("====================================\n")

                                response_data = {
                                    "ok": False,
                                    "error": "ASHA Connect could not complete the requested database operation.",
                                }

                                try:
                                    await websocket.send_json({
                                        "type": "action_executed",
                                        "action": action,
                                        "success": False,
                                        "payload": payload,
                                        "error": str(exc),
                                    })
                                except Exception:
                                    pass

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

            await asyncio.gather(receive_browser(), receive_gemini())

    except WebSocketDisconnect:
        pass
    except Exception as exc:
        print("ASHA LIVE SOCKET ERROR:", type(exc).__name__)
        try:
            await websocket.send_json({"type": "error", "message": str(exc)})
        except Exception:
            pass
        try:
            await websocket.close()
        except Exception:
            pass


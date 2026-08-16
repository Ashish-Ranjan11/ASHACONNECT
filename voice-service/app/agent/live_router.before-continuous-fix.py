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
                    "description": "Allowed ASHA Connect action name.",
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

Understand Hindi, Hinglish, Nepali and English.

IMPORTANT DATABASE RULES:

- Never invent beneficiary information.
- Never invent database IDs.
- Use execute_asha_action whenever data must come from ASHA Connect.
- If a beneficiary is mentioned by name and an action requires beneficiary_id,
  first call list_beneficiaries and resolve the actual beneficiary.
- Use returned database records as the source of truth.

APPOINTMENTS:
- Resolve beneficiary first.
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

                        await session.send_realtime_input(
                            audio_stream_end=True
                        )


            async def receive_gemini():

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

                                result = await execute_asha_action(
                                    action=action,
                                    payload=payload,
                                    authorization=authorization,
                                )

                                response_data = {
                                    "ok": True,
                                    "result": result,
                                }

                            except Exception as exc:

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

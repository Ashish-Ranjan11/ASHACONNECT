import os
import httpx


BACKEND_URL = os.getenv(
    "ASHA_BACKEND_URL",
    "http://127.0.0.1:8000"
)


async def get_reminder_status(
    authorization: str
):

    async with httpx.AsyncClient(
        timeout=10
    ) as client:

        response = await client.get(
            f"{BACKEND_URL}/api/reminders",
            headers={
                "Authorization": authorization
            }
        )

        response.raise_for_status()

        return response.json()

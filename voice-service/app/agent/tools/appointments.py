import os
import httpx


ASHA_BACKEND_URL = os.getenv(
    "ASHA_BACKEND_URL",
    "http://127.0.0.1:8000"
)


async def list_appointments(
    date: str | None = None,
    authorization: str | None = None,
):
    """
    Get appointments visible to the authenticated ASHA worker.
    """

    url = f"{ASHA_BACKEND_URL}/api/appointments"

    params = {}

    if date:
        params["date"] = date

    headers = {}

    if authorization:
        headers["Authorization"] = authorization

    async with httpx.AsyncClient(timeout=10.0) as client:

        response = await client.get(
            url,
            params=params,
            headers=headers,
        )

        response.raise_for_status()

        return response.json()

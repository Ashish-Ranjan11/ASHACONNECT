import os
import httpx


BACKEND_URL = os.getenv(
    "ASHA_BACKEND_URL",
    "http://127.0.0.1:8000"
)


async def get_report(
    authorization: str,
    endpoint: str
):

    async with httpx.AsyncClient(
        timeout=30
    ) as client:

        response = await client.get(
            f"{BACKEND_URL}{endpoint}",
            headers={
                "Authorization": authorization
            }
        )

        response.raise_for_status()

        return response.json()

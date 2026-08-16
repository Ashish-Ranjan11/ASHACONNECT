import os
import httpx


ASHA_BACKEND_URL = os.getenv(
    "ASHA_BACKEND_URL",
    "http://127.0.0.1:8000"
)


async def list_beneficiaries(
    authorization: str,
):
    """
    Return beneficiaries visible to the authenticated ASHA worker.
    """

    url = f"{ASHA_BACKEND_URL}/api/beneficiaries"

    headers = {
        "Authorization": authorization
    }

    async with httpx.AsyncClient(timeout=10.0) as client:

        response = await client.get(
            url,
            headers=headers,
        )

        response.raise_for_status()

        return response.json()


async def get_beneficiary(
    beneficiary_id: int,
    authorization: str,
):
    """
    Get a single beneficiary profile.
    """

    url = (
        f"{ASHA_BACKEND_URL}"
        f"/api/beneficiaries/{beneficiary_id}/profile"
    )

    headers = {
        "Authorization": authorization
    }

    async with httpx.AsyncClient(timeout=10.0) as client:

        response = await client.get(
            url,
            headers=headers,
        )

        response.raise_for_status()

        return response.json()

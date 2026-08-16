import os
import httpx


ASHA_BACKEND_URL = os.getenv(
    "ASHA_BACKEND_URL",
    "http://127.0.0.1:8000"
)


class BackendError(Exception):
    pass


async def backend_request(
    method: str,
    path: str,
    authorization: str,
    *,
    params=None,
    json=None,
):
    if not authorization:
        raise BackendError("Authentication required")

    url = f"{ASHA_BACKEND_URL}{path}"

    headers = {
        "Authorization": authorization,
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=15.0) as client:

        response = await client.request(
            method,
            url,
            headers=headers,
            params=params,
            json=json,
        )

    if response.status_code == 401:
        raise BackendError("Authentication failed")

    if response.status_code >= 400:
        raise BackendError(
            f"Backend returned HTTP {response.status_code}: "
            f"{response.text}"
        )

    return response.json()

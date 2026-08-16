from app.agent.backend import backend_request


async def list_appointments(
    authorization: str,
    date=None,
):
    params = {}

    if date:
        params["date"] = date

    return await backend_request(
        "GET",
        "/api/appointments",
        authorization,
        params=params,
    )


async def create_appointment(
    authorization: str,
    payload: dict,
):
    return await backend_request(
        "POST",
        "/api/appointments",
        authorization,
        json=payload,
    )

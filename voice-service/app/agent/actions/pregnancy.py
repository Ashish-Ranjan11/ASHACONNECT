from app.agent.backend import backend_request


async def list_pregnancy_records(
    authorization: str,
):
    return await backend_request(
        "GET",
        "/api/pregnancy-records",
        authorization,
    )


async def create_pregnancy_record(
    authorization: str,
    payload: dict,
):
    return await backend_request(
        "POST",
        "/api/pregnancy-records",
        authorization,
        json=payload,
    )

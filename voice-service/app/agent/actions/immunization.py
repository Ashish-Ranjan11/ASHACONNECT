from app.agent.backend import backend_request


async def list_immunization_records(
    authorization: str,
):
    return await backend_request(
        "GET",
        "/api/immunization-records",
        authorization,
    )


async def create_immunization_record(
    authorization: str,
    payload: dict,
):
    return await backend_request(
        "POST",
        "/api/immunization-records",
        authorization,
        json=payload,
    )

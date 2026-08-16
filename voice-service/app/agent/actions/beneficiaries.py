from app.agent.backend import backend_request


async def list_beneficiaries(
    authorization: str,
):
    return await backend_request(
        "GET",
        "/api/beneficiaries",
        authorization,
    )


async def create_beneficiary(
    authorization: str,
    payload: dict,
):
    return await backend_request(
        "POST",
        "/api/beneficiaries",
        authorization,
        json=payload,
    )


async def update_beneficiary(
    authorization: str,
    beneficiary_id: int,
    payload: dict,
):
    return await backend_request(
        "PUT",
        f"/api/beneficiaries/{beneficiary_id}",
        authorization,
        json=payload,
    )


async def delete_beneficiary(
    authorization: str,
    beneficiary_id: int,
):
    return await backend_request(
        "DELETE",
        f"/api/beneficiaries/{beneficiary_id}",
        authorization,
    )


async def beneficiary_profile(
    authorization: str,
    beneficiary_id: int,
):
    return await backend_request(
        "GET",
        f"/api/beneficiaries/{beneficiary_id}/profile",
        authorization,
    )

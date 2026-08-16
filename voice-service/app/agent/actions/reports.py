from app.agent.backend import backend_request


async def list_reports(
    authorization: str,
):
    return await backend_request(
        "GET",
        "/api/care-automation/reports",
        authorization,
    )


async def generate_individual_report(
    authorization: str,
    payload: dict,
):
    return await backend_request(
        "POST",
        "/api/care-automation/reports/individual",
        authorization,
        json=payload,
    )


async def generate_family_report(
    authorization: str,
    payload: dict,
):
    return await backend_request(
        "POST",
        "/api/care-automation/reports/family",
        authorization,
        json=payload,
    )


async def generate_phc_summary(
    authorization: str,
    payload: dict,
):
    return await backend_request(
        "POST",
        "/api/care-automation/reports/all-families-phc-summary",
        authorization,
        json=payload,
    )


async def generate_report(
    authorization: str,
    payload: dict,
):
    return await backend_request(
        "POST",
        "/api/reports/generate",
        authorization,
        json=payload,
    )

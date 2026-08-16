from app.agent.backend import backend_request


async def list_messages(
    authorization: str,
):
    return await backend_request(
        "GET",
        "/api/care-automation/messages",
        authorization,
    )


async def run_reminders(
    authorization: str,
):
    return await backend_request(
        "POST",
        "/api/care-automation/reminders/run-now",
        authorization,
    )


async def auto_run_reminders(
    authorization: str,
):
    return await backend_request(
        "POST",
        "/api/care-automation/reminders/auto-run-now",
        authorization,
    )


async def mark_message_sent(
    authorization: str,
    message_id: int,
):
    return await backend_request(
        "POST",
        f"/api/care-automation/messages/{message_id}/mark-sent",
        authorization,
    )

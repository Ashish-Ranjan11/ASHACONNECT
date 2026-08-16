WRITE_INTENTS = {
    "appointments.create",
    "appointments.reschedule",
    "appointments.cancel",

    "beneficiary.create",
    "beneficiary.update",

    "reminders.send",
}


def requires_confirmation(intent: str) -> bool:
    return intent in WRITE_INTENTS


def is_confirmation(text: str) -> bool:

    normalized = text.strip().lower()

    confirmations = [
        "हाँ",
        "हां",
        "जी हाँ",
        "जी हां",
        "कर दो",
        "कर दीजिए",
        "yes",
        "confirm",
        "confirmed",
        "ok",
        "okay",
    ]

    return any(
        word in normalized
        for word in confirmations
    )


def is_rejection(text: str) -> bool:

    normalized = text.strip().lower()

    rejections = [
        "नहीं",
        "मत करो",
        "रहने दो",
        "cancel",
        "no",
    ]

    return any(
        word in normalized
        for word in rejections
    )

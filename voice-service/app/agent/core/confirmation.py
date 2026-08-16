WRITE_ACTIONS = {
    "create_appointment",
    "create_beneficiary",
    "update_beneficiary",
    "delete_beneficiary",
    "create_pregnancy_record",
    "create_immunization_record",
    "run_reminders",
    "run_auto_reminders",
    "mark_message_sent",
    "generate_individual_report",
    "generate_family_report",
    "generate_phc_summary",
    "generate_report",
}


YES_WORDS = {
    "yes",
    "yes please",
    "confirm",
    "confirmed",
    "do it",
    "go ahead",
    "proceed",
    "okay",
    "ok",
    "हाँ",
    "हां",
    "जी",
    "कर दो",
    "कर दीजिए",
    "ठीक है",
    "आगे बढ़ो",
}


NO_WORDS = {
    "no",
    "cancel",
    "stop",
    "don't",
    "do not",
    "नहीं",
    "नही",
    "रद्द करो",
    "मत करो",
    "छोड़ दो",
}


def requires_confirmation(action: str) -> bool:
    return action in WRITE_ACTIONS


def detect_confirmation(text: str):
    normalized = " ".join(
        str(text or "").strip().lower().split()
    )

    if normalized in YES_WORDS:
        return True

    if normalized in NO_WORDS:
        return False

    return None


def confirmation_message(
    action: str,
    payload: dict,
    hindi: bool = False,
):
    if action == "create_appointment":

        name = (
            payload.get("beneficiary_name")
            or payload.get("name")
            or f"beneficiary ID {payload.get('beneficiary_id')}"
        )

        date = (
            payload.get("appointment_date")
            or payload.get("date")
            or "specified date"
        )

        time = (
            payload.get("appointment_time")
            or payload.get("time")
            or "specified time"
        )

        if hindi:
            return (
                f"{name} का अपॉइंटमेंट {date} को "
                f"{time} बजे बनाना है। "
                "क्या मैं इसे सेव कर दूँ?"
            )

        return (
            f"I am ready to schedule {name} on {date} "
            f"at {time}. Should I save the appointment?"
        )

    if action == "create_beneficiary":
        name = payload.get("full_name") or payload.get("name") or "this beneficiary"

        if hindi:
            return (
                f"{name} को नया लाभार्थी जोड़ना है। "
                "क्या मैं इसे सेव कर दूँ?"
            )

        return (
            f"I am ready to add {name} as a new beneficiary. "
            "Should I save the record?"
        )

    if action == "delete_beneficiary":
        if hindi:
            return (
                "यह लाभार्थी रिकॉर्ड हटाया जाएगा। "
                "क्या आप निश्चित हैं?"
            )

        return (
            "This beneficiary record will be deleted. "
            "Are you sure you want to continue?"
        )

    if hindi:
        return (
            "यह बदलाव ASHA Connect में सेव किया जाएगा। "
            "क्या मैं आगे बढ़ूँ?"
        )

    return (
        "This action will change data in ASHA Connect. "
        "Should I proceed?"
    )

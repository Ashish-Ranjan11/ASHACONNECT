import re
from datetime import datetime, timedelta


def normalize_text(text: str) -> str:
    """
    Lightweight transcript cleanup.

    We deliberately do NOT alter the original STT model output.
    This only creates a normalized version for intent detection.
    """

    if not text:
        return ""

    text = text.strip()

    replacements = {
        "अपॉइंटमेंटटवेस्": "अपॉइंटमेंट है",
        "अपॉइंटमेंट्स": "अपॉइंटमेंट",
        "अपॉइंटमेंट": "अपॉइंटमेंट",
        "टीके": "टीका",
        "टिका": "टीका",
        "इम्यूनाइजेशन": "टीकाकरण",
        "प्रेगनेंसी": "गर्भावस्था",
        "प्रेग्नेंसी": "गर्भावस्था",
        "गर्भवती महिला": "गर्भवती",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    # Remove duplicate spaces
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def detect_date(text):
    """
    Detect relative and explicit dates from Hindi/English voice commands.

    Supported examples:
        आज
        कल
        परसों
        26 जून
        27 जून
        15 अगस्त
        26 June
        26 June 2026
        26 जून 2026
    """

    from datetime import date, timedelta

    if not text:
        return None

    text = str(text).strip().lower()

    today = date.today()

    # --------------------------------------------------
    # RELATIVE DATES
    # --------------------------------------------------

    if "परसों" in text:
        target = today + timedelta(days=2)

        return {
            "date": target.isoformat(),
            "label": "day_after_tomorrow",
        }

    if "कल" in text:
        target = today + timedelta(days=1)

        return {
            "date": target.isoformat(),
            "label": "tomorrow",
        }

    if "आज" in text:
        return {
            "date": today.isoformat(),
            "label": "today",
        }

    if "day after tomorrow" in text:
        target = today + timedelta(days=2)

        return {
            "date": target.isoformat(),
            "label": "day_after_tomorrow",
        }

    if "tomorrow" in text:
        target = today + timedelta(days=1)

        return {
            "date": target.isoformat(),
            "label": "tomorrow",
        }

    if "today" in text:
        return {
            "date": today.isoformat(),
            "label": "today",
        }

    # --------------------------------------------------
    # MONTH NAMES
    # --------------------------------------------------

    months = {
        # Hindi
        "जनवरी": 1,
        "फरवरी": 2,
        "मार्च": 3,
        "अप्रैल": 4,
        "मई": 5,
        "जून": 6,
        "जुलाई": 7,
        "अगस्त": 8,
        "सितंबर": 9,
        "सितम्बर": 9,
        "अक्टूबर": 10,
        "नवंबर": 11,
        "नवम्बर": 11,
        "दिसंबर": 12,
        "दिसम्बर": 12,

        # English
        "january": 1,
        "jan": 1,
        "february": 2,
        "feb": 2,
        "march": 3,
        "mar": 3,
        "april": 4,
        "apr": 4,
        "may": 5,
        "june": 6,
        "jun": 6,
        "july": 7,
        "jul": 7,
        "august": 8,
        "aug": 8,
        "september": 9,
        "sep": 9,
        "sept": 9,
        "october": 10,
        "oct": 10,
        "november": 11,
        "nov": 11,
        "december": 12,
        "dec": 12,
    }

    # --------------------------------------------------
    # EXPLICIT DATE
    #
    # Examples:
    # 26 जून
    # 26 जून 2026
    # 26 june
    # 26 june 2026
    # --------------------------------------------------

    month_pattern = "|".join(
        sorted(
            (re.escape(month) for month in months),
            key=len,
            reverse=True,
        )
    )

    match = re.search(
        rf"(\d{{1,2}})\s*({month_pattern})(?:\s*(20\d{{2}}))?",
        text,
    )

    if match:
        day = int(match.group(1))
        month_name = match.group(2)
        year_text = match.group(3)

        month = months[month_name]

        if year_text:
            year = int(year_text)
        else:
            # For appointment/history queries, a date without
            # an explicit year refers to the current calendar year.
            year = today.year

        try:
            target = date(year, month, day)
        except ValueError:
            return None

        return {
            "date": target.isoformat(),
            "label": target.strftime("%Y-%m-%d"),
        }

    # --------------------------------------------------
    # NUMERIC DATES
    #
    # Examples:
    # 26/06/2026
    # 26-06-2026
    # 26/06
    # --------------------------------------------------

    match = re.search(
        r"\b(\d{1,2})[/-](\d{1,2})(?:[/-](20\d{2}))?\b",
        text,
    )

    if match:
        day = int(match.group(1))
        month = int(match.group(2))
        year_text = match.group(3)

        year = int(year_text) if year_text else today.year

        try:
            target = date(year, month, day)

            if not year_text and target < today:
                target = date(year + 1, month, day)

        except ValueError:
            return None

        return {
            "date": target.isoformat(),
            "label": target.strftime("%Y-%m-%d"),
        }

    return None

def extract_person_name(text: str):
    """
    Extract a likely beneficiary name from common ASHA voice queries.

    The backend remains the source of truth for resolving
    the actual beneficiary.
    """

    if not text:
        return None

    text = text.strip()

    patterns = [
        r"(?:status|health|profile|record|details|information|about)\s+(?:of|for|on)\s+([A-Za-z]+(?:\s+[A-Za-z]+){1,3})",

        r"(?:tell me about|show me|show|give me details about|check)\s+([A-Za-z]+(?:\s+[A-Za-z]+){1,3})",

        r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})['’]s\s+(?:health|profile|status|record|details)",

        r"(?:की|के|का)\s+(?:स्वास्थ्य|हालत|स्थिति|रिकॉर्ड|जानकारी)\s+([A-Za-z]+(?:\s+[A-Za-z]+){1,3})",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)

        if match:
            name = match.group(1).strip()

            name = re.sub(
                r"[?.,!]+$",
                "",
                name,
            ).strip()

            return name

    return None

def detect_intent(text: str):

    normalized = normalize_text(text)

    date_info = detect_date(normalized)

    # --------------------------------------------------
    # APPOINTMENTS
    # --------------------------------------------------

    appointment_words = [
        "अपॉइंटमेंट",
        "मुलाकात",
        "भेंट",
        "विजिट",
        "appointment",
        "visit",
    ]

    if any(word in normalized.lower() for word in appointment_words):

        return {
            "intent": "appointments.list",
            "confidence": 0.95,
            "entities": {
                "date": date_info["date"] if date_info else None,
                "date_label": date_info["label"] if date_info else None,
                "person_name": extract_person_name(normalized),
            },
            "normalized_text": normalized,
        }

    # --------------------------------------------------
    # PREGNANCY
    # --------------------------------------------------

    pregnancy_words = [
        "गर्भवती",
        "गर्भावस्था",
        "pregnancy",
        "pregnant",
        "anc",
        "जांच बाकी",
    ]

    if any(word in normalized.lower() for word in pregnancy_words):

        return {
            "intent": "pregnancy.list",
            "confidence": 0.90,
            "entities": {
                "date": date_info["date"] if date_info else None,
                "date_label": date_info["label"] if date_info else None,
                "person_name": extract_person_name(normalized),
            },
            "normalized_text": normalized,
        }

    # --------------------------------------------------
    # IMMUNIZATION
    # --------------------------------------------------

    immunization_words = [
        "टीका",
        "टीकाकरण",
        "वैक्सीन",
        "vaccination",
        "vaccine",
        "immunization",
    ]

    if any(word in normalized.lower() for word in immunization_words):

        return {
            "intent": "immunization.list",
            "confidence": 0.90,
            "entities": {
                "date": date_info["date"] if date_info else None,
                "date_label": date_info["label"] if date_info else None,
                "person_name": extract_person_name(normalized),
            },
            "normalized_text": normalized,
        }

    # --------------------------------------------------
    # BENEFICIARY / HEALTH PROFILE
    # --------------------------------------------------

    beneficiary_words = [
        "लाभार्थी",
        "beneficiary",
        "जानकारी",
        "रिकॉर्ड",
        "परिवार",
        "family",
        "health",
        "status",
        "profile",
        "details",
        "health status",
        "स्वास्थ्य",
        "हालत",
        "स्थिति",
        "स्वास्थ्य स्थिति",
    ]

    person_name = extract_person_name(normalized)

    # Generic beneficiary lookup must take priority over
    # accidental extraction such as "the beneficiaries".
    generic_lookup_phrases = [
        "show me the beneficiaries",
        "show the beneficiaries",
        "list the beneficiaries",
        "list beneficiaries",
        "all beneficiaries",
        "show beneficiaries",
        "लाभार्थियों की सूची",
        "सभी लाभार्थी",
        "लाभार्थी दिखाओ",
    ]

    if any(
        phrase in normalized.lower()
        for phrase in generic_lookup_phrases
    ):
        return {
            "intent": "beneficiary.lookup",
            "confidence": 0.90,
            "entities": {
                "person_name": None,
            },
            "normalized_text": normalized,
        }

    # Named beneficiary health/profile request
    if person_name:

        return {
            "intent": "beneficiary.profile",
            "confidence": 0.92,
            "entities": {
                "person_name": person_name,
            },
            "normalized_text": normalized,
        }

    # Generic beneficiary lookup
    if any(
        word in normalized.lower()
        for word in beneficiary_words
    ):

        return {
            "intent": "beneficiary.lookup",
            "confidence": 0.80,
            "entities": {
                "person_name": None,
            },
            "normalized_text": normalized,
        }

    # --------------------------------------------------
    # UNKNOWN
    # --------------------------------------------------

    return {
        "intent": "unknown",
        "confidence": 0.20,
        "entities": {},
        "normalized_text": normalized,
    }

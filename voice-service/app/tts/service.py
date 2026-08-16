from pathlib import Path
import tempfile

from gtts import gTTS


def synthesize_speech(text: str, language: str = "hi") -> str:
    language_map = {
        "hi": "hi",
        "ne": "ne",
        "en": "en",
    }

    lang = language_map.get(language, "hi")

    output_dir = Path(
        tempfile.mkdtemp(prefix="asha_tts_")
    )

    output_path = output_dir / "response.mp3"

    tts = gTTS(
        text=text,
        lang=lang,
        slow=False,
    )

    tts.save(str(output_path))

    return str(output_path)

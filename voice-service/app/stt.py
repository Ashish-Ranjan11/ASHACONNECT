import os
import subprocess
import tempfile

import librosa
import torch
from transformers import AutoModel


MODEL_ID = "ai4bharat/indic-conformer-600m-multilingual"

_model = None


def load_model():
    global _model

    if _model is None:
        print("[ASHA Voice] Loading IndicConformer...")

        _model = AutoModel.from_pretrained(
            MODEL_ID,
            trust_remote_code=True
        )

        # Apple Silicon / CPU
        if torch.backends.mps.is_available():
            print("[ASHA Voice] Using Apple MPS")
            _model = _model.to("mps")
        else:
            print("[ASHA Voice] Using CPU")
            _model = _model.to("cpu")

        _model.eval()

        print("[ASHA Voice] IndicConformer ready.")

    return _model


def convert_to_wav(input_path: str) -> str:

    output_file = tempfile.NamedTemporaryFile(
        suffix=".wav",
        delete=False
    )

    output_path = output_file.name
    output_file.close()

    command = [
        "ffmpeg",
        "-y",
        "-i",
        input_path,
        "-ar",
        "16000",
        "-ac",
        "1",
        "-sample_fmt",
        "s16",
        output_path,
    ]

    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    if result.returncode != 0:

        if os.path.exists(output_path):
            os.remove(output_path)

        raise RuntimeError(
            "FFmpeg conversion failed:\n"
            + result.stderr
        )

    return output_path


def transcribe_audio(
    audio_path: str,
    language: str = "hi"
):

    model = load_model()

    wav_path = convert_to_wav(audio_path)

    try:

        audio, sample_rate = librosa.load(
            wav_path,
            sr=16000,
            mono=True
        )

        print(
            "[ASHA Voice] Audio:",
            f"{len(audio) / 16000:.2f}s",
            "sample_rate=",
            sample_rate
        )

        # IndicConformer expects a tensor shaped (1, T)
        wav = torch.tensor(
            audio,
            dtype=torch.float32
        ).unsqueeze(0)

        if torch.backends.mps.is_available():
            wav = wav.to("mps")
        else:
            wav = wav.to("cpu")

        print(
            f"[ASHA Voice] Running {language.upper()} CTC decoding..."
        )

        with torch.no_grad():

            transcription = model(
                wav,
                language,
                "ctc"
            )

        print(
            "[ASHA Voice] Transcription:",
            transcription
        )

        if isinstance(transcription, str):
            return transcription.strip()

        return str(transcription).strip()

    finally:

        if os.path.exists(wav_path):
            os.remove(wav_path)

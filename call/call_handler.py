from services.stt_service import STTService
from services.json_store import save_call_result


stt = STTService()


async def handle_audio(audio_bytes: bytes, phone_number: str = "", tts_text: str = ""):
    """Legacy handler — transcribe audio bytes and save to JSON."""
    text = stt.transcribe(audio_bytes)

    print("User said:", text)

    save_call_result(
        phone_number=phone_number,
        tts_text=tts_text,
        transcription=text,
    )

    return text

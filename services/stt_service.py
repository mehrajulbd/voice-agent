import os
import base64
import requests
from dotenv import load_dotenv

load_dotenv()

GOOGLE_STT_URL = "https://speech.googleapis.com/v1/speech:recognize"


class STTService:
    """Google Cloud Speech-to-Text using REST API with API key."""

    def __init__(self):
        self.api_key = os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY is not set in .env")

    def transcribe(self, audio_bytes: bytes, sample_rate: int = 48000) -> str:
        """
        Transcribe raw PCM audio bytes (LINEAR16) to text using Google STT REST API.
        Google STT synchronous API has a limit of ~1 minute / ~10MB.
        For longer audio we trim to ~55 seconds.
        Returns the transcription string.
        """
        # Trim audio to max ~55 seconds (16-bit mono = 2 bytes per sample)
        max_samples = 55 * sample_rate
        max_bytes = max_samples * 2  # 16-bit = 2 bytes per sample
        if len(audio_bytes) > max_bytes:
            print(f"[STTService] Trimming audio from {len(audio_bytes)} to {max_bytes} bytes (~55s)")
            audio_bytes = audio_bytes[:max_bytes]

        # Skip if audio is too short (< 0.5 seconds)
        min_bytes = int(0.5 * sample_rate * 2)
        if len(audio_bytes) < min_bytes:
            print(f"[STTService] Audio too short ({len(audio_bytes)} bytes), skipping transcription")
            return "(audio too short)"

        # Base64 encode the audio
        audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")

        payload = {
            "config": {
                "encoding": "LINEAR16",
                "sampleRateHertz": sample_rate,
                "languageCode": "en-US",
                "enableAutomaticPunctuation": True,
            },
            "audio": {
                "content": audio_b64,
            },
        }

        url = f"{GOOGLE_STT_URL}?key={self.api_key}"
        print(f"[STTService] Sending {len(audio_bytes)} bytes ({len(audio_bytes) / (sample_rate * 2):.1f}s) for transcription...")

        try:
            response = requests.post(url, json=payload, timeout=30)
        except requests.exceptions.Timeout:
            print("[STTService] Google STT API request timed out")
            return "(transcription timed out)"
        except requests.exceptions.RequestException as e:
            print(f"[STTService] Google STT API request error: {e}")
            return "(transcription error)"

        if response.status_code != 200:
            print(f"[STTService] Google STT API error {response.status_code}: {response.text}")
            return "(transcription failed)"

        result = response.json()
        transcript = ""
        for res in result.get("results", []):
            alternatives = res.get("alternatives", [])
            if alternatives:
                transcript += alternatives[0].get("transcript", "") + " "

        transcript = transcript.strip()
        if not transcript:
            transcript = "(no speech detected)"

        print(f"[STTService] Transcription: {transcript}")
        return transcript

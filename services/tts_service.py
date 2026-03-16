import os
import base64
import requests
from dotenv import load_dotenv

load_dotenv()

GOOGLE_TTS_URL = "https://texttospeech.googleapis.com/v1/text:synthesize"


class TTSService:
    """Google Cloud Text-to-Speech using REST API with API key."""

    def __init__(self):
        self.api_key = os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY is not set in .env")

    def synthesize(self, text: str) -> bytes:
        """
        Synthesize text to WAV audio bytes (LINEAR16, 48kHz, mono).
        Returns raw WAV bytes.
        """
        payload = {
            "input": {"text": text},
            "voice": {
                "languageCode": "en-US",
                "ssmlGender": "NEUTRAL",
            },
            "audioConfig": {
                "audioEncoding": "LINEAR16",
                "sampleRateHertz": 48000,
            },
        }

        url = f"{GOOGLE_TTS_URL}?key={self.api_key}"
        print(f"[TTSService] Synthesizing: '{text[:60]}...'")
        response = requests.post(url, json=payload)

        if response.status_code != 200:
            raise RuntimeError(f"Google TTS API error {response.status_code}: {response.text}")

        audio_content = base64.b64decode(response.json()["audioContent"])
        print(f"[TTSService] Synthesized {len(audio_content)} bytes of audio")
        return audio_content

    def synthesize_to_file(self, text: str, output_path: str = "output.wav") -> str:
        """Synthesize text and save to a WAV file. Returns the file path."""
        audio_content = self.synthesize(text)
        with open(output_path, "wb") as f:
            f.write(audio_content)
        print(f"[TTSService] Audio written to {output_path}")
        return output_path

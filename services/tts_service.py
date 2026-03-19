import os
import base64
import requests
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

GOOGLE_TTS_URL = "https://texttospeech.googleapis.com/v1beta1/text:synthesize"

class TTSService:
    """Google Cloud Text-to-Speech using REST API with API key."""

    def __init__(self):
        self.api_key = os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY is not set in .env")

    def synthesize(
        self, 
        text: str, 
        language_code: str = "bn-BD", 
        # Recommended Natural Female Voices:
        # bn-BD-Neural2-A (Bangladesh Female)
        # bn-IN-Neural2-A (India Female)
        # bn-IN-Wavenet-A (India Female)
        voice_name: Optional[str] = "bn-IN-Neural2-A" 
    ) -> bytes:
        
        payload = {
            "input": {"text": text},
            "voice": {
                "languageCode": language_code,  # Use bn-BD if you want the Bangladesh voice, but it may be less natural
                # "name": "bn-IN-Neural2-A",
                "ssmlGender": "FEMALE",
            },
            "audioConfig": {
                "audioEncoding": "LINEAR16",
                "sampleRateHertz": 48000,
                "speakingRate": 1.05, # Slightly faster sounds more natural
                "pitch": 0.0,         # Adjust between -20.0 and 20.0 if needed
            },
        }

        url = f"{GOOGLE_TTS_URL}?key={self.api_key}"
        print(f"[TTSService] Synthesizing with {language_code} and {voice_name}...")
        
        response = requests.post(url, json=payload)

        if response.status_code != 200:
            raise RuntimeError(f"Google TTS API error {response.status_code}: {response.text}")

        audio_content = base64.b64decode(response.json()["audioContent"])
        return audio_content

    def synthesize_to_file(self, text: str, output_path: str = "female_output.wav") -> str:
        audio_content = self.synthesize(text)
        with open(output_path, "wb") as f:
            f.write(audio_content)
        print(f"[TTSService] Natural female audio written to {output_path}")
        return output_path

# Example Usage
if __name__ == "__main__":
    tts = TTSService()
    # For Bangladesh Female Voice
    tts.synthesize_to_file("কেমন আছেন? আমি আপনার কৃত্রিম বুদ্ধিমত্তা সহকারী।", "test_bd.wav")
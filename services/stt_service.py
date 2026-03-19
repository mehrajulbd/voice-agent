import os
import base64
import requests
from dotenv import load_dotenv

load_dotenv()

# Using v1p1beta1 to access enhanced models like 'latest_long'
GOOGLE_STT_URL = "https://speech.googleapis.com/v1/speech:recognize"

class STTService:
    """Google Cloud Speech-to-Text using REST API with Enhanced Bangla Models."""

    def __init__(self):
        self.api_key = os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY is not set in .env")

    def transcribe(self, audio_bytes: bytes, sample_rate: int = 48000, language_code: str = "bn-IN") -> str:
        """
        Transcribe raw PCM audio bytes to text.
        Optimized for Bangla using 'latest_long' enhanced model.
        
        Args:
            audio_bytes: Raw PCM audio data
            sample_rate: Sample rate in Hz (default 48000)
            language_code: "bn-IN" (India) or "bn-BD" (Bangladesh)
        """
        # Trim audio to max ~55 seconds to stay within Synchronous API limits
        max_samples = 55 * sample_rate
        max_bytes = max_samples * 2  # 16-bit = 2 bytes per sample
        if len(audio_bytes) > max_bytes:
            print(f"[STTService] Trimming audio from {len(audio_bytes)} to {max_bytes} bytes")
            audio_bytes = audio_bytes[:max_bytes]

        # Skip if audio is too short (< 0.5 seconds)
        min_bytes = int(0.5 * sample_rate * 2)
        if len(audio_bytes) < min_bytes:
            return "(audio too short)"

        # Base64 encode
        audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")

        payload = {
            "config": {
                "encoding": "LINEAR16",
                "sampleRateHertz": sample_rate,
                "languageCode": language_code,  # Use "bn-BD" if targeting Bangladeshi speakers
                "enableAutomaticPunctuation": True,
                "useEnhanced": True,        # Opts into higher-quality hardware processing
                # --------------------------------------------
            },
            "audio": {
                "content": audio_b64,
            },
        }

        print(f"[STTService] Sending audio for transcription (size: {len(audio_bytes)} bytes)")
        print(f"[STTService] Payload config: {payload['config']}")

        url = f"{GOOGLE_STT_URL}?key={self.api_key}"
        
        try:
            response = requests.post(url, json=payload, timeout=30)
            if response.status_code != 200:
                print(f"[STTService] API Error Response: {response.text}")
            response.raise_for_status() # Raise error for 4xx or 5xx
        except requests.exceptions.Timeout:
            return "(transcription timed out)"
        except requests.exceptions.RequestException as e:
            print(f"[STTService] API error: {e}")
            return "(transcription error)"

        result = response.json()
        
        # Check for errors in the JSON response itself
        if "error" in result:
            print(f"[STTService] Google API Error: {result['error'].get('message')}")
            return "(transcription failed)"

        transcript_parts = []
        for res in result.get("results", []):
            alternatives = res.get("alternatives", [])
            if alternatives:
                transcript_parts.append(alternatives[0].get("transcript", ""))

        transcript = " ".join(transcript_parts).strip()
        
        if not transcript:
            return "(no speech detected)"

        print(f"[STTService] Transcription: {transcript}")
        return transcript

# Example Usage:
# if __name__ == "__main__":
#     service = STTService()
#     # with open("audio.raw", "rb") as f:
#     #     text = service.transcribe(f.read())
#     #     print(text)


import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

class GeminiService:
    """Gemini API for intelligent order confirmation analysis in Bangla."""

    def __init__(self):
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY is not set in .env")
        
        genai.configure(api_key=api_key)
        
        # This system instruction tells the AI to act as a linguistically flexible assistant
        system_instruction = (
            "You are an expert order-processing assistant for a Bangladeshi e-commerce company. "
            "Your task is to analyze user responses (transcribed from audio) to see if they want to accept or cancel their order. "
            "\n\n"
            "GUIDELINES FOR BANGLA STT ANALYSIS:\n"
            "1. EXPECT TYPOS: Transcriptions often miss characters. (e.g., 'হ' or 'হে' might mean 'হ্যাঁ'; 'টিক আছে' means 'ঠিক আছে').\n"
            "2. AFFIRMATIVE (yes): Look for words like: হ্যাঁ (yes), জি (ji), ঠিক আছে (ok), ওকে (ok), পাঠান (send it), নিব (will take), "
            "আসেন (come), দিয়ে যান (give it), হ (informal yes).\n"
            "3. NEGATIVE (no): Look for words like: না (no), লাগবে না (don't need), ক্যানসেল (cancel), ভুল করে (by mistake), "
            "পরে নিব (take later), রাখব না (won't keep).\n"
            "4. AMBIGUITY: If the user sounds confused or says they didn't order, treat it as 'no'.\n"
            "\n"
            "OUTPUT RULES:\n"
            "- Return 'yes' if they want the order.\n"
            "- Return 'no' if they don't want it or are unsure.\n"
            "- Output ONLY the word 'yes' or 'no'."
        )

        self.model = genai.GenerativeModel(
            model_name="gemini-3-flash-preview",
            system_instruction=system_instruction,
            generation_config={
                "temperature": 0.1,  # Keep it deterministic
                "max_output_tokens": 5,
            }
        )

    def analyze_confirmation(self, transcription: str) -> tuple[bool, str]:
        """
        Intelligently analyzes Bangla transcription to detect order acceptance.
        """
        if not transcription or len(transcription.strip()) < 1:
            return False, "empty_input"

        print(f"[GeminiService] Analyzing: '{transcription}'")

        try:
            # The prompt is simplified because the System Instruction handles the logic
            prompt = f"User said: {transcription}"
            response = self.model.generate_content(prompt)
            
            # Extract and clean result
            result = response.text.strip().lower()
            
            # Logic check (in case model returns a sentence, though restricted by tokens)
            is_confirmed = "yes" in result
            
            return is_confirmed, result

        except Exception as e:
            print(f"[GeminiService] SDK Error: {e}")
            return False, "error"

# --- Practical Test Cases ---
if __name__ == "__main__":
    service = GeminiService()
    
    test_cases = [
        "হ্যাঁ পাঠিয়ে দিন",         # Direct Yes
        "টিক আছে ভাই নিয়ে আসেন",    # STT Error: 'Tik' instead of 'Thik'
        "অকে দিয়ে যান",           # Phonetic 'Ok'
        "না ভাই এখন লাগবে না",      # Direct No
        "আমি তো অর্ডার করি নাই",     # Rejection via confusion
        "হ ঠিক আছে",              # Informal/Short
        "পরে ফোন দিয়েন এখন ব্যস্ত", # Soft Rejection/Delay
    ]

    for text in test_cases:
        confirmed, raw = service.analyze_confirmation(text)
        status = "✅ ACCEPTED" if confirmed else "❌ REJECTED"
        print(f"Input: {text} \nDecision: {status} ({raw})\n" + "-"*30)
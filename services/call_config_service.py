import json
import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class CallConfig:
    """Configuration for a single call."""
    company_name: str
    product_name: str
    quantity: str
    language_code: str = "bn-BD"
    voice_name: Optional[str] = None


class CallConfigService:
    """Loads call configuration from a JSON file."""

    def __init__(self, config_path: str = "config/call_config.json"):
        self.config_path = config_path
        self.config = self._load_config()

    def _load_config(self) -> CallConfig:
        """Load configuration from file, or return defaults if file not found."""
        if not os.path.exists(self.config_path):
            print(f"[CallConfigService] Config file not found: {self.config_path}")
            print("[CallConfigService] Using default configuration (English)")
            return self._default_config()

        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            config = CallConfig(
                company_name=data.get('company_name', 'Company'),
                product_name=data.get('product_name', 'Product'),
                quantity=data.get('quantity', '1'),
                language_code=data.get('language_code', 'bn-BD'),
                voice_name=data.get('voice_name')
            )
            print(f"[CallConfigService] Loaded config: {config}")
            return config

        except (json.JSONDecodeError, KeyError) as e:
            print(f"[CallConfigService] Error loading config: {e}")
            print("[CallConfigService] Using default configuration (English)")
            return self._default_config()

    def _default_config(self) -> CallConfig:
        """Return a default English configuration."""
        return CallConfig(
            company_name="Default Company",
            product_name="Product",
            quantity="1",
            language_code="en-US",
            voice_name=None
        )

    def get_config(self) -> CallConfig:
        """Get the loaded configuration."""
        return self.config

    def generate_tts_text(self) -> str:
        """
        Generate the TTS message based on configuration.
        Returns a Bangla (or configured language) message.
        """
        config = self.config

        return self._generate_tts_text_impl(
            company_name=config.company_name,
            product_name=config.product_name,
            quantity=config.quantity,
            language_code=config.language_code
        )

    def generate_tts_text_for_order(self, product_name: str, quantity: str, language_code: Optional[str] = None) -> str:
        """
        Generate a TTS message for a specific product and quantity.
        Uses the company name from config and optional language override.

        Args:
            product_name: Name of the product
            quantity: Quantity as string (e.g., "৫ কেজি" or "5 kg")
            language_code: Optional language code override (defaults to config language)

        Returns:
            TTS message string in appropriate language
        """
        config = self.config
        lang = language_code or config.language_code

        return self._generate_tts_text_impl(
            company_name=config.company_name,
            product_name=product_name,
            quantity=quantity,
            language_code=lang
        )

    def _generate_tts_text_impl(self, company_name: str, product_name: str, quantity: str, language_code: str) -> str:
        """Internal implementation for TTS text generation."""
        if language_code.startswith("bn"):
            # Bangla message
            return (
                f"আমি {company_name} থেকে বলছি।"
                f"আপনি {quantity} টি {product_name} অর্ডার করেছেন। "
                "আমি অর্ডার নিশ্চিত করতে চাই। অনুগ্রহ করে হ্যাঁ বলুন যদি আপনি অর্ডারটি চান।"
            )
        else:
            # English fallback
            return (
                f"Hello, I'm calling from {company_name}. "
                f"I want to confirm your order for {quantity} "
                f"{product_name}. Please say yes to confirm."
            )

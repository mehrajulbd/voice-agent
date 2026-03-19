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
        
        return (
            f"আমি {config.company_name} থেকে মীম বলছি।"
            f"আপনি {config.quantity} টি {config.product_name} অর্ডার করেছেন। "
            "আমি অর্ডার নিশ্চিত করতে চাই। অনুগ্রহ করে হ্যাঁ বলুন যদি আপনি অর্ডারটি চান।"
        )
        # return (
        # f"Hello, I'm calling from {config.company_name}. "
        # f"I want to confirm your order for {config.quantity} "
        # f"{config.product_name}. Please say yes to confirm."
        # )

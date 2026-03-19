import asyncio
import os
from typing import Dict, Any, Optional
from dotenv import load_dotenv

from call.make_call import make_call
from services.call_handler import CallHandler
from services.call_config_service import CallConfigService
from services.product_service import ProductService

load_dotenv()


async def place_call(
    phone_number: str,
    product_id: str,
    quantity: int,
    language_code: Optional[str] = None,
    custom_tts: Optional[str] = None
) -> Dict[str, Any]:
    """
    High-level function to place an automated call for a product order.

    Args:
        phone_number: Target phone number in E.164 format
        product_id: ID of the product from the catalog
        quantity: Quantity to order
        language_code: Optional language override (e.g., "bn-BD", "en-US")
        custom_tts: Optional custom TTS message (overrides generated message)

    Returns:
        Dictionary with call results:
        {
            "success": bool,
            "phone_number": str,
            "product_id": str,
            "product_name": str,
            "quantity": int,
            "transcription": str,
            "confirmation_detected": bool,
            "gemini_analysis": str,
            "result_file": str,
            "error": str (if failed)
        }
    """
    results = {
        "phone_number": phone_number,
        "product_id": product_id,
        "product_name": "",
        "quantity": quantity,
        "transcription": "",
        "confirmation_detected": False,
        "gemini_analysis": "",
        "result_file": "",
        "success": False,
        "error": None
    }

    try:
        # Validate environment variables
        missing = []
        for var in ["LIVEKIT_URL", "LIVEKIT_API_KEY", "LIVEKIT_API_SECRET", "SIP_TRUNK_ID", "GOOGLE_API_KEY", "FROM_PHONE_NUMBER"]:
            if not os.getenv(var):
                missing.append(var)
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

        # Load product catalog
        product_service = ProductService()
        product = product_service.get_product(product_id)
        if not product:
            raise ValueError(f"Product not found: {product_id}")

        results["product_name"] = product.name

        # Map language code to Google STT supported codes
        config_service = CallConfigService()
        effective_lang = language_code or config_service.get_config().language_code
        # if effective_lang == "bn-BD":
        #     effective_lang = "bn-IN"  # Google STT only supports bn-IN for Bengali

        # Generate TTS message
        if custom_tts:
            tts_text = custom_tts
        else:
            # Convert quantity to string (e.g., "5 kg" or keep Bangla format)
            quantity_str = f"{quantity} {product.unit}"
            tts_text = config_service.generate_tts_text_for_order(
                product_name=product.name,
                quantity=quantity_str,
                language_code=effective_lang
            )

        print(f"[call_runner] Placing call to {phone_number}")
        print(f"[call_runner] Product: {product.name} (x{quantity})")
        print(f"[call_runner] Language: {effective_lang}")
        print(f"[call_runner] TTS: {tts_text}")

        # Step 1: Initiate the SIP call
        print("[call_runner] Initiating SIP call...")
        room_name = await make_call(phone_number)
        print(f"[call_runner] Call initiated. Room: {room_name}")

        # Step 2: Connect and handle call
        print("[call_runner] Connecting to room and handling call...")
        handler = CallHandler(
            room_name=room_name,
            tts_text=tts_text,
            phone_number=phone_number,
            language_code=effective_lang,
            voice_name=config_service.get_config().voice_name
        )
        await handler.run()

        # Extract results from handler (we need to modify CallHandler to store these)
        # For now, we'll rely on the fact that handler.run() saves JSON and prints
        # We could enhance CallHandler to return data, but for now we'll read from
        # the latest results file or have handler store state.
        # SIMPLER: modify CallHandler to store these in instance attributes
        results["transcription"] = getattr(handler, '_last_transcription', "")
        results["confirmation_detected"] = getattr(handler, '_last_confirmation_detected', False)
        results["gemini_analysis"] = getattr(handler, '_last_gemini_analysis', "")
        results["result_file"] = getattr(handler, '_last_result_file', "")
        results["success"] = True

        print(f"[call_runner] Call completed successfully")

    except Exception as e:
        print(f"[call_runner] Error: {e}")
        results["error"] = str(e)
        results["success"] = False

    return results


def place_call_sync(
    phone_number: str,
    product_id: str,
    quantity: int,
    language_code: Optional[str] = None,
    custom_tts: Optional[str] = None
) -> Dict[str, Any]:
    """
    Synchronous wrapper for place_call.
    """
    return asyncio.run(place_call(
        phone_number=phone_number,
        product_id=product_id,
        quantity=quantity,
        language_code=language_code,
        custom_tts=custom_tts
    ))


if __name__ == "__main__":
    # Simple test
    import sys
    if len(sys.argv) < 4:
        print("Usage: python call_runner.py <phone_number> <product_id> <quantity> [language_code]")
        print("Example: python call_runner.py +8801327403936 rice_5kg 2 bn-BD")
        sys.exit(1)

    phone = sys.argv[1]
    prod_id = sys.argv[2]
    qty = int(sys.argv[3])
    lang = sys.argv[4] if len(sys.argv) > 4 else None

    result = place_call_sync(phone, prod_id, qty, lang)
    print("\n=== CALL RESULT ===")
    for key, value in result.items():
        print(f"{key}: {value}")

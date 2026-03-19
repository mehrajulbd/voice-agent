import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

from call.make_call import make_call
from services.call_handler import CallHandler
from services.call_config_service import CallConfigService


async def main():
    phone_number = os.getenv("TARGET_PHONE_NUMBER", "+8801327403936")

    # Load call configuration
    config_service = CallConfigService()
    config = config_service.get_config()

    # Generate TTS message based on configuration
    tts_text = config_service.generate_tts_text()

    print("=" * 60)
    print("  LiveKit + Twilio SIP Automated Call System")
    print("=" * 60)
    print(f"  Target Phone : {phone_number}")
    print(f"  Company      : {config.company_name}")
    print(f"  Product      : {config.product_name}")
    print(f"  Quantity     : {config.quantity}")
    print(f"  Language     : {config.language_code}")
    if config.voice_name:
        print(f"  Voice        : {config.voice_name}")
    print(f"  TTS Message  : {tts_text}")
    print(f"  From Number  : {os.getenv('FROM_PHONE_NUMBER', 'NOT SET')}")
    print(f"  LiveKit URL  : {os.getenv('LIVEKIT_URL', 'NOT SET')}")
    print(f"  SIP Trunk    : {os.getenv('SIP_TRUNK_ID', 'NOT SET')}")
    print(f"  Google API   : {'SET' if os.getenv('GOOGLE_API_KEY') else 'NOT SET'}")
    print("=" * 60)

    # Validate env
    missing = []
    for var in ["LIVEKIT_URL", "LIVEKIT_API_KEY", "LIVEKIT_API_SECRET", "SIP_TRUNK_ID", "GOOGLE_API_KEY", "FROM_PHONE_NUMBER"]:
        if not os.getenv(var):
            missing.append(var)
    if missing:
        print(f"\nERROR: Missing required environment variables: {', '.join(missing)}")
        print("Please set them in your .env file.")
        return

    # Step 1: Initiate the SIP call via LiveKit
    print("\n[main] Step 1: Initiating SIP outbound call...")
    try:
        room_name = await make_call(phone_number)
    except Exception as e:
        print(f"[main] Failed to initiate call: {e}")
        return

    print(f"[main] Call initiated. Room: {room_name}")

    # Step 2: Connect to the room, play TTS, record response, transcribe, save
    print("\n[main] Step 2: Connecting to room and handling call...")
    handler = CallHandler(
        room_name=room_name,
        tts_text=tts_text,
        phone_number=phone_number,
        language_code=config.language_code,
        voice_name=config.voice_name
    )
    await handler.run()

    print("\n[main] Done! Check the results/ directory for JSON output.")


if __name__ == "__main__":
    asyncio.run(main())

import os
import asyncio
from dotenv import load_dotenv
from livekit import api
from livekit.protocol.sip import CreateSIPParticipantRequest

load_dotenv()


async def make_call(target_phone: str = None):
    """
    Create a LiveKit SIP outbound call to the target phone number.
    LiveKit is already configured with Twilio SIP trunk — no Twilio SDK needed.
    """
    phone_number = target_phone or os.getenv("TARGET_PHONE_NUMBER")
    from_number = os.getenv("FROM_PHONE_NUMBER")
    sip_trunk_id = os.getenv("SIP_TRUNK_ID")
    livekit_url = os.getenv("LIVEKIT_URL")
    api_key = os.getenv("LIVEKIT_API_KEY")
    api_secret = os.getenv("LIVEKIT_API_SECRET")

    if not phone_number:
        raise ValueError("TARGET_PHONE_NUMBER is not set in .env")
    if not from_number:
        raise ValueError("FROM_PHONE_NUMBER is not set in .env")
    if not sip_trunk_id:
        raise ValueError("SIP_TRUNK_ID is not set in .env")
    if not livekit_url:
        raise ValueError("LIVEKIT_URL is not set in .env")
    if not api_key or not api_secret:
        raise ValueError("LIVEKIT_API_KEY / LIVEKIT_API_SECRET not set in .env")

    print(f"[make_call] LiveKit URL: {livekit_url}")
    print(f"[make_call] SIP Trunk ID: {sip_trunk_id}")
    print(f"[make_call] From: {from_number}")
    print(f"[make_call] Dialing: {phone_number}")

    # Create a LiveKit API client
    lk_api = api.LiveKitAPI(
        url=livekit_url,
        api_key=api_key,
        api_secret=api_secret,
    )

    # The room name where the call participant will join
    room_name = "call-room"

    # Debug: print all available fields in the protobuf
    print("[make_call] Available fields in CreateSIPParticipantRequest:")
    for field in CreateSIPParticipantRequest.DESCRIPTOR.fields:
        print(f"  - {field.name}")

    # Build the request using the protobuf message directly
    # sip_number = the FROM/caller-ID number (your Twilio number)
    request = CreateSIPParticipantRequest(
        sip_trunk_id=sip_trunk_id,
        sip_call_to=phone_number,
        room_name=room_name,
        participant_identity=f"phone-{phone_number}",
        participant_name="Customer",
    )

    # Try to set sip_number / number field for the FROM caller ID
    # Different livekit-api versions may use different field names
    try:
        request.sip_number = from_number
        print(f"[make_call] Set sip_number = {from_number}")
    except (AttributeError, ValueError) as e:
        print(f"[make_call] Could not set sip_number: {e}")
        try:
            request.number = from_number
            print(f"[make_call] Set number = {from_number}")
        except (AttributeError, ValueError) as e2:
            print(f"[make_call] Could not set number either: {e2}")

    # Print the full request for debugging
    print(f"[make_call] Full request:\n{request}")

    try:
        sip_participant = await lk_api.sip.create_sip_participant(request)
        print(f"[make_call] SIP participant response: {sip_participant}")

        # Check if the participant has an ID
        participant_id = getattr(sip_participant, 'participant_id', None) or getattr(sip_participant, 'sip_participant_id', None)
        print(f"[make_call] Participant ID: {participant_id}")

        return room_name
    except Exception as e:
        print(f"[make_call] Error creating SIP participant: {type(e).__name__}: {e}")
        # Print full error details
        import traceback
        traceback.print_exc()
        raise
    finally:
        await lk_api.aclose()


if __name__ == "__main__":
    target_number = input("Enter the target phone number: ")
    asyncio.run(make_call(target_number))

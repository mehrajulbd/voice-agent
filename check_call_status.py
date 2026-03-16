# filepath: /media/Main Files/tenbytes/livekit-call/check_call_status.py
"""
Monitor a SIP call's actual status in the LiveKit room.
This helps diagnose why calls disconnect immediately.
Run: python check_call_status.py
"""
import asyncio
import os
import time
from dotenv import load_dotenv
from livekit import rtc, api
from livekit.protocol.sip import CreateSIPParticipantRequest

load_dotenv()


async def main():
    livekit_url = os.getenv("LIVEKIT_URL")
    api_key = os.getenv("LIVEKIT_API_KEY")
    api_secret = os.getenv("LIVEKIT_API_SECRET")
    sip_trunk_id = os.getenv("SIP_TRUNK_ID")
    from_number = os.getenv("FROM_PHONE_NUMBER")
    target = os.getenv("TARGET_PHONE_NUMBER", "+8801327403936")

    print("=" * 60)
    print("  SIP Call Status Monitor")
    print("=" * 60)

    # Step 1: Create the room first so we can monitor it
    room_name = "test-call-room"

    # Generate token for bot
    token = (
        api.AccessToken(api_key, api_secret)
        .with_identity("monitor-bot")
        .with_name("Monitor Bot")
        .with_grants(api.VideoGrants(room_join=True, room=room_name))
    )
    jwt_token = token.to_jwt()

    # Connect to room
    room = rtc.Room()

    events = []

    def on_participant_connected(participant: rtc.RemoteParticipant):
        ts = time.strftime("%H:%M:%S")
        msg = f"[{ts}] PARTICIPANT_CONNECTED: {participant.identity}"
        print(msg)
        events.append(msg)
        # Print participant metadata/attributes
        print(f"  metadata: {participant.metadata}")
        print(f"  attributes: {participant.attributes}")

    def on_participant_disconnected(participant: rtc.RemoteParticipant):
        ts = time.strftime("%H:%M:%S")
        msg = f"[{ts}] PARTICIPANT_DISCONNECTED: {participant.identity}"
        print(msg)
        events.append(msg)

    def on_track_subscribed(track, publication, participant):
        ts = time.strftime("%H:%M:%S")
        msg = f"[{ts}] TRACK_SUBSCRIBED: kind={track.kind} from {participant.identity}"
        print(msg)
        events.append(msg)

    def on_track_unsubscribed(track, publication, participant):
        ts = time.strftime("%H:%M:%S")
        msg = f"[{ts}] TRACK_UNSUBSCRIBED: kind={track.kind} from {participant.identity}"
        print(msg)
        events.append(msg)

    def on_participant_attrs_changed(changed_attrs, participant):
        ts = time.strftime("%H:%M:%S")
        msg = f"[{ts}] ATTRIBUTES_CHANGED: {participant.identity} -> {changed_attrs}"
        print(msg)
        print(f"  all attributes: {participant.attributes}")
        events.append(msg)

    def on_participant_metadata_changed(old_metadata, participant):
        ts = time.strftime("%H:%M:%S")
        msg = f"[{ts}] METADATA_CHANGED: {participant.identity} -> {participant.metadata}"
        print(msg)
        events.append(msg)

    room.on("participant_connected", on_participant_connected)
    room.on("participant_disconnected", on_participant_disconnected)
    room.on("track_subscribed", on_track_subscribed)
    room.on("track_unsubscribed", on_track_unsubscribed)
    room.on("participant_attributes_changed", on_participant_attrs_changed)
    room.on("participant_metadata_changed", on_participant_metadata_changed)

    print(f"\n[1] Connecting to room '{room_name}'...")
    await room.connect(livekit_url, jwt_token)
    print(f"[1] Connected.\n")

    # Step 2: Create the SIP call
    print(f"[2] Creating SIP call to {target} from {from_number}...")
    lk_api = api.LiveKitAPI(url=livekit_url, api_key=api_key, api_secret=api_secret)

    request = CreateSIPParticipantRequest(
        sip_trunk_id=sip_trunk_id,
        sip_call_to=target,
        room_name=room_name,
        participant_identity=f"phone-{target}",
        participant_name="Customer",
    )
    # Set FROM number
    try:
        request.sip_number = from_number
    except Exception:
        pass

    print(f"[2] Request:\n{request}\n")

    try:
        resp = await lk_api.sip.create_sip_participant(request)
        print(f"[2] Response:\n{resp}\n")
    except Exception as e:
        print(f"[2] ERROR: {e}")
        await room.disconnect()
        await lk_api.aclose()
        return

    await lk_api.aclose()

    # Step 3: Monitor for 30 seconds
    print("[3] Monitoring room events for 30 seconds...")
    print("    (If your phone rings, ANSWER it!)\n")

    for i in range(30):
        await asyncio.sleep(1)
        # Check participant status
        for pid, p in room.remote_participants.items():
            if i % 5 == 0:  # Print every 5 seconds
                print(f"  [{i}s] Participant: {p.identity}, tracks: {len(p.track_publications)}, metadata: {p.metadata}, attrs: {p.attributes}")

    print("\n--- Summary ---")
    print(f"Events captured: {len(events)}")
    for e in events:
        print(f"  {e}")

    if not events:
        print("  No events at all — SIP participant never appeared in room.")
        print("  This means the SIP call failed before even entering the room.")

    participant_connected = any("PARTICIPANT_CONNECTED" in e for e in events)
    participant_disconnected = any("PARTICIPANT_DISCONNECTED" in e for e in events)

    if participant_connected and participant_disconnected:
        # Check how fast disconnect happened
        print("\n  *** SIP participant connected then quickly disconnected ***")
        print("  This means the outbound SIP call FAILED at the Twilio level.")
        print("  Possible causes:")
        print("    1. Twilio Geo Permissions: Bangladesh (+880) may not be enabled")
        print("       → Go to: https://console.twilio.com/us1/develop/voice/settings/geo-permissions")
        print("       → Enable 'Bangladesh' under Low-Risk or allow it")
        print("    2. Twilio Termination URI may be incorrect")
        print(f"       → Current: nafiterminate.pstn.twilio.com")
        print("       → Should match your Elastic SIP Trunk termination URI in Twilio")
        print("    3. Twilio account balance may be insufficient")
        print("    4. SIP trunk auth credentials may be wrong")

    await room.disconnect()
    print("\nDone.")


if __name__ == "__main__":
    asyncio.run(main())

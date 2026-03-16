# filepath: /media/Main Files/tenbytes/livekit-call/test_call.py
"""
Minimal test: make a SIP call and watch the sip.callStatus attribute
to diagnose exactly where the call fails.
Run: python test_call.py
"""
import asyncio
import os
import time
from datetime import timedelta
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
    target = os.getenv("TARGET_PHONE_NUMBER")

    room_name = "debug-call-room"

    # Step 1: Connect bot to room FIRST
    token = (
        api.AccessToken(api_key, api_secret)
        .with_identity("debug-bot")
        .with_name("Debug Bot")
        .with_grants(api.VideoGrants(room_join=True, room=room_name))
    )

    room = rtc.Room()
    call_status_log = []
    disconnect_event = asyncio.Event()

    def on_participant_connected(p: rtc.RemoteParticipant):
        ts = time.strftime("%H:%M:%S")
        status = p.attributes.get("sip.callStatus", "unknown")
        print(f"  [{ts}] CONNECTED: {p.identity} | callStatus={status}")
        print(f"          attributes: {dict(p.attributes)}")
        call_status_log.append(("connected", status, ts))

    def on_participant_disconnected(p: rtc.RemoteParticipant):
        ts = time.strftime("%H:%M:%S")
        status = p.attributes.get("sip.callStatus", "unknown")
        print(f"  [{ts}] DISCONNECTED: {p.identity} | callStatus={status}")
        call_status_log.append(("disconnected", status, ts))
        disconnect_event.set()

    def on_attrs_changed(changed, p: rtc.RemoteParticipant):
        ts = time.strftime("%H:%M:%S")
        status = p.attributes.get("sip.callStatus", "unknown")
        print(f"  [{ts}] ATTR_CHANGED: {p.identity} | callStatus={status} | changed={dict(changed)}")
        call_status_log.append(("attr_changed", status, ts))

    def on_track_subscribed(track, pub, p):
        ts = time.strftime("%H:%M:%S")
        print(f"  [{ts}] TRACK: kind={track.kind} from {p.identity}")

    room.on("participant_connected", on_participant_connected)
    room.on("participant_disconnected", on_participant_disconnected)
    room.on("participant_attributes_changed", on_attrs_changed)
    room.on("track_subscribed", on_track_subscribed)

    print(f"[1] Connecting bot to room '{room_name}'...")
    await room.connect(livekit_url, token.to_jwt())
    print(f"[1] Connected.\n")

    # Step 2: Make the SIP call
    print(f"[2] Dialing {target} from {from_number}...")
    lk_api = api.LiveKitAPI(url=livekit_url, api_key=api_key, api_secret=api_secret)

    request = CreateSIPParticipantRequest(
        sip_trunk_id=sip_trunk_id,
        sip_call_to=target,
        sip_number=from_number,
        room_name=room_name,
        participant_identity=f"phone-{target}",
        participant_name="Customer",
        play_dialtone=True,
        ringing_timeout=timedelta(seconds=45),
        max_call_duration=timedelta(seconds=120),
    )

    print(f"[2] Request:\n{request}")

    try:
        resp = await lk_api.sip.create_sip_participant(request)
        print(f"\n[2] Response: participant_id={resp.participant_id} sip_call_id={resp.sip_call_id}\n")
    except Exception as e:
        print(f"\n[2] ERROR: {type(e).__name__}: {e}\n")
        await room.disconnect()
        await lk_api.aclose()
        return

    await lk_api.aclose()

    # Step 3: Monitor for 60 seconds
    print("[3] Monitoring call status for 60 seconds (pick up the phone!)...\n")

    try:
        await asyncio.wait_for(disconnect_event.wait(), timeout=60)
    except asyncio.TimeoutError:
        print("  (60 second timeout)")

    # Also check if participant is still there
    for pid, p in room.remote_participants.items():
        print(f"  Still in room: {p.identity} | attrs={dict(p.attributes)}")

    print(f"\n--- Call Status Timeline ---")
    for event_type, status, ts in call_status_log:
        print(f"  {ts} | {event_type:20s} | sip.callStatus = {status}")

    if call_status_log:
        last_status = call_status_log[-1][1]
        print(f"\n--- Diagnosis ---")
        if last_status == "dialing":
            print("  Call FAILED during dialing phase.")
            print("  The SIP INVITE was rejected by Twilio.")
            print("  Check in Twilio Console:")
            print("    → Elastic SIP Trunking → your trunk → check for error logs")
            print("    → Monitor → Logs → look for SIP errors")
            print("    → Ensure Credential List auth matches: username='nafiullah'")
        elif last_status == "ringing":
            print("  Call reached the phone but was not answered.")
        elif last_status == "active":
            print("  Call was answered successfully!")
        else:
            print(f"  Final status: {last_status}")

    await room.disconnect()
    print("\nDone.")


if __name__ == "__main__":
    asyncio.run(main())

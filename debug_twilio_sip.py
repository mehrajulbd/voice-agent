"""
Debug script: Verify Twilio SIP trunk configuration by checking:
1. LiveKit outbound trunk details (address, auth, numbers)
2. Try a SIP call with wait_until_answered=True to get the actual error
3. Check if the termination URI resolves via DNS

Run: python debug_twilio_sip.py
"""
import asyncio
import os
import socket
from dotenv import load_dotenv
from livekit import api
from livekit.protocol.sip import (
    CreateSIPParticipantRequest,
    ListSIPOutboundTrunkRequest,
)
from datetime import timedelta

load_dotenv()


async def main():
    livekit_url = os.getenv("LIVEKIT_URL")
    api_key = os.getenv("LIVEKIT_API_KEY")
    api_secret = os.getenv("LIVEKIT_API_SECRET")
    sip_trunk_id = os.getenv("SIP_TRUNK_ID")
    from_number = os.getenv("FROM_PHONE_NUMBER")
    target = os.getenv("TARGET_PHONE_NUMBER")

    print("=" * 60)
    print("  Twilio SIP Trunk Debug")
    print("=" * 60)

    # ── Step 1: Check trunk config ──
    print("\n[1] Checking outbound SIP trunk configuration...")
    lk_api = api.LiveKitAPI(url=livekit_url, api_key=api_key, api_secret=api_secret)

    try:
        resp = await lk_api.sip.list_sip_outbound_trunk(ListSIPOutboundTrunkRequest())
        trunks = list(resp.items)
        if not trunks:
            print("  ❌ No outbound SIP trunks found!")
            print("  You need to create one in LiveKit Cloud dashboard.")
            await lk_api.aclose()
            return

        our_trunk = None
        for t in trunks:
            if t.sip_trunk_id == sip_trunk_id:
                our_trunk = t
                break

        if not our_trunk:
            print(f"  ❌ Trunk {sip_trunk_id} not found!")
            print(f"  Available trunks: {[t.sip_trunk_id for t in trunks]}")
            await lk_api.aclose()
            return

        print(f"  Trunk ID     : {our_trunk.sip_trunk_id}")
        print(f"  Name         : {our_trunk.name}")
        print(f"  Address      : {our_trunk.address}")
        print(f"  Transport    : {our_trunk.transport}")
        print(f"  Numbers      : {list(our_trunk.numbers)}")
        print(f"  Auth Username: {our_trunk.auth_username}")
        print(f"  Auth Password: {'***' + our_trunk.auth_password[-3:] if our_trunk.auth_password else '(empty)'}")

        address = our_trunk.address

    except Exception as e:
        print(f"  Error listing trunks: {e}")
        import traceback
        traceback.print_exc()
        await lk_api.aclose()
        return

    # ── Step 2: DNS resolution check ──
    print(f"\n[2] Checking DNS resolution for: {address}")
    try:
        hostname = address.split(":")[0]  # remove port if any
        ips = socket.getaddrinfo(hostname, 5061, socket.AF_INET, socket.SOCK_STREAM)
        print(f"  ✅ Resolves to: {set(ip[4][0] for ip in ips)}")
    except socket.gaierror as e:
        print(f"  ❌ DNS resolution FAILED: {e}")
        print(f"  The termination URI '{address}' does not exist!")
        print(f"  Go to Twilio Console → Elastic SIP Trunking → your trunk → Termination")
        print(f"  and verify the Termination SIP URI.")

    # ── Step 3: Try calling with different configurations ──
    print(f"\n[3] Attempting call to {target} ...")
    print(f"    (Using trunk: {sip_trunk_id}, from: {from_number})")

    room_name = "sip-debug-room"

    # Try with hide_phone_number=False explicitly
    request = CreateSIPParticipantRequest(
        sip_trunk_id=sip_trunk_id,
        sip_call_to=target,
        sip_number=from_number,
        room_name=room_name,
        participant_identity=f"sip-debug-{target}",
        participant_name="Debug Call",
        play_dialtone=False,
        hide_phone_number=False,
        ringing_timeout=timedelta(seconds=30),
        max_call_duration=timedelta(seconds=60),
    )

    print(f"\n    Full request:\n{request}")

    try:
        resp = await lk_api.sip.create_sip_participant(request)
        print(f"\n  ✅ SIP participant created: {resp.participant_id}")
        print(f"     sip_call_id: {resp.sip_call_id}")

        # Now wait and check the room for the participant status
        print(f"\n[4] Checking participant status in room '{room_name}'...")
        await asyncio.sleep(5)  # Wait for call to attempt

        from livekit.protocol.room import ListRoomsRequest, ListParticipantsRequest
        rooms_resp = await lk_api.room.list_rooms(ListRoomsRequest(names=[room_name]))
        rooms = list(rooms_resp.rooms)
        if rooms:
            participants_resp = await lk_api.room.list_participants(
                ListParticipantsRequest(room=room_name)
            )
            participants = list(participants_resp.participants)
            if participants:
                for p in participants:
                    print(f"  Participant: {p.identity}")
                    print(f"    State: {p.state}")
                    print(f"    Attributes: {dict(p.attributes)}")
                    sip_status = p.attributes.get("sip.callStatus", "unknown")
                    print(f"    SIP Call Status: {sip_status}")

                    if sip_status == "dialing":
                        print("\n  ⏳ Still dialing... waiting 10 more seconds")
                        await asyncio.sleep(10)
                        # Re-check
                        participants_resp2 = await lk_api.room.list_participants(
                            ListParticipantsRequest(room=room_name)
                        )
                        p2_list = list(participants_resp2.participants)
                        if p2_list:
                            for p2 in p2_list:
                                print(f"  Updated status: {p2.attributes.get('sip.callStatus', 'unknown')}")
                        else:
                            print("  ❌ Participant left room — call FAILED")
                            print("\n  This confirms Twilio REJECTED the call.")
                            print("  The issue is in your Twilio SIP trunk configuration.")
                    elif sip_status == "ringing":
                        print("  📞 Phone is RINGING!")
                    elif sip_status == "active":
                        print("  ✅ Call is ACTIVE!")
            else:
                print("  ❌ No participants in room — call already failed")
                print("\n  The SIP participant was created but immediately disconnected.")
                print("  This means Twilio REJECTED the SIP INVITE.")
        else:
            print("  ❌ Room doesn't exist — call failed before room was created")

    except Exception as e:
        print(f"\n  ❌ API Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

    await lk_api.aclose()

    print("\n" + "=" * 60)
    print("  TROUBLESHOOTING CHECKLIST")
    print("=" * 60)
    print("""
  The SIP call FAILS during the 'dialing' phase (within 2-3 seconds).
  This means Twilio receives the SIP INVITE but REJECTS it.

  ✅ MUST CHECK in Twilio Console:

  1. CALL LOGS — see the exact error
     → https://console.twilio.com/us1/monitor/logs/debugger
     → Look for the most recent error with your trunk name
     → The error code will tell you exactly what's wrong

  2. ELASTIC SIP TRUNKING → Trunks → 'nafitrunk' → Termination:
     → Is Termination URI: nafiterminate.pstn.twilio.com ?
     → Is the URI ENABLED (not disabled)?
     → Authentication: Credential List with username 'nafiullah'
       and the CORRECT password?

  3. ELASTIC SIP TRUNKING → Trunks → 'nafitrunk' → General:
     → Is the trunk status ACTIVE?

  4. GEO PERMISSIONS for Bangladesh:
     → https://console.twilio.com/us1/develop/voice/settings/geo-permissions
     → Bangladesh must be checked/enabled

  5. ACCOUNT BALANCE:
     → International calls cost money. Check your Twilio balance.
     → Bangladesh mobile calls cost ~$0.04/min

  6. TRY A US NUMBER FIRST:
     → Change TARGET_PHONE_NUMBER to a US number you own
     → If US number works, the issue is specifically Bangladesh routing
""")


if __name__ == "__main__":
    asyncio.run(main())

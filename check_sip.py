# filepath: /media/Main Files/tenbytes/livekit-call/check_sip.py
"""
Diagnostic script to check LiveKit SIP trunk configuration.
Run: python check_sip.py
"""
import asyncio
import os
from dotenv import load_dotenv
from livekit import api

load_dotenv()


async def main():
    livekit_url = os.getenv("LIVEKIT_URL")
    api_key = os.getenv("LIVEKIT_API_KEY")
    api_secret = os.getenv("LIVEKIT_API_SECRET")
    sip_trunk_id = os.getenv("SIP_TRUNK_ID")

    print("=" * 60)
    print("  LiveKit SIP Trunk Diagnostic")
    print("=" * 60)
    print(f"  LIVEKIT_URL      : {livekit_url}")
    print(f"  LIVEKIT_API_KEY  : {api_key}")
    print(f"  SIP_TRUNK_ID     : {sip_trunk_id}")
    print(f"  FROM_PHONE_NUMBER: {os.getenv('FROM_PHONE_NUMBER')}")
    print(f"  TARGET_PHONE     : {os.getenv('TARGET_PHONE_NUMBER')}")
    print("=" * 60)

    lk_api = api.LiveKitAPI(
        url=livekit_url,
        api_key=api_key,
        api_secret=api_secret,
    )

    # 1. List all SIP trunks
    print("\n--- Listing SIP Outbound Trunks ---")
    try:
        from livekit.protocol.sip import ListSIPOutboundTrunkRequest
        trunks_resp = await lk_api.sip.list_sip_outbound_trunk(ListSIPOutboundTrunkRequest())
        trunks = trunks_resp.items if hasattr(trunks_resp, 'items') else trunks_resp
        print(f"Found {len(list(trunks)) if hasattr(trunks, '__len__') else '?'} outbound trunk(s):")
        for trunk in trunks:
            print(f"  Trunk: {trunk}")
    except Exception as e:
        print(f"  Error listing outbound trunks: {type(e).__name__}: {e}")

    print("\n--- Listing SIP Inbound Trunks ---")
    try:
        from livekit.protocol.sip import ListSIPInboundTrunkRequest
        trunks_resp = await lk_api.sip.list_sip_inbound_trunk(ListSIPInboundTrunkRequest())
        trunks = trunks_resp.items if hasattr(trunks_resp, 'items') else trunks_resp
        print(f"Found trunk(s):")
        for trunk in trunks:
            print(f"  Trunk: {trunk}")
    except Exception as e:
        print(f"  Error listing inbound trunks: {type(e).__name__}: {e}")

    # 2. List rooms
    print("\n--- Listing Active Rooms ---")
    try:
        rooms_resp = await lk_api.room.list_rooms(api.ListRoomsRequest())
        rooms = rooms_resp.rooms
        if rooms:
            for room in rooms:
                print(f"  Room: {room.name} (participants: {room.num_participants})")
        else:
            print("  No active rooms.")
    except Exception as e:
        print(f"  Error listing rooms: {type(e).__name__}: {e}")

    # 3. List SIP dispatch rules
    print("\n--- Listing SIP Dispatch Rules ---")
    try:
        from livekit.protocol.sip import ListSIPDispatchRuleRequest
        rules_resp = await lk_api.sip.list_sip_dispatch_rule(ListSIPDispatchRuleRequest())
        rules = rules_resp.items if hasattr(rules_resp, 'items') else rules_resp
        print(f"Found rule(s):")
        for rule in rules:
            print(f"  Rule: {rule}")
    except Exception as e:
        print(f"  Error listing dispatch rules: {type(e).__name__}: {e}")

    await lk_api.aclose()
    print("\n--- Done ---")


if __name__ == "__main__":
    asyncio.run(main())

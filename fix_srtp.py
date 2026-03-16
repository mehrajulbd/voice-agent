"""
Fix the SIP trunk to use SRTP (encrypted media) so Twilio accepts the call.
Twilio Error 32208: "SIP trunk or domain is required to use secure media (SRTP)"
"""
import asyncio
import os
from dotenv import load_dotenv
from livekit import api
from livekit.protocol import sip as sip_proto

load_dotenv()


async def main():
    livekit_url = os.getenv("LIVEKIT_URL")
    api_key = os.getenv("LIVEKIT_API_KEY")
    api_secret = os.getenv("LIVEKIT_API_SECRET")
    sip_trunk_id = os.getenv("SIP_TRUNK_ID")
    from_number = os.getenv("FROM_PHONE_NUMBER")
    target = os.getenv("TARGET_PHONE_NUMBER")

    lk_api = api.LiveKitAPI(url=livekit_url, api_key=api_key, api_secret=api_secret)

    # Step 1: Show current trunk config
    print("[1] Current trunk config...")
    resp = await lk_api.sip.list_sip_outbound_trunk(sip_proto.ListSIPOutboundTrunkRequest())
    current_trunk = None
    for t in resp.items:
        if t.sip_trunk_id == sip_trunk_id:
            current_trunk = t
            print(f"    media_encryption = {t.media_encryption} (0=DISABLE, 1=ALLOW, 2=REQUIRE)")
            break

    if not current_trunk:
        print(f"    Trunk {sip_trunk_id} not found!")
        await lk_api.aclose()
        return

    # Step 2: Update trunk to require SRTP
    print("\n[2] Updating trunk to require SRTP (media_encryption=REQUIRE)...")

    # Build replacement trunk with SRTP enabled
    replacement = sip_proto.SIPOutboundTrunkInfo(
        name=current_trunk.name,
        address=current_trunk.address,
        transport=current_trunk.transport,
        numbers=list(current_trunk.numbers),
        auth_username=current_trunk.auth_username,
        auth_password=current_trunk.auth_password,
        media_encryption=sip_proto.SIP_MEDIA_ENCRYPT_REQUIRE,  # <-- THE FIX
    )

    try:
        # API: update_outbound_trunk(trunk_id: str, trunk: SIPOutboundTrunkInfo)
        update_resp = await lk_api.sip.update_outbound_trunk(sip_trunk_id, replacement)
        print(f"    ✅ Trunk updated!")
        print(f"    New media_encryption = {update_resp.media_encryption}")
    except Exception as e:
        print(f"    ❌ Update failed: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

    # Step 3: Verify the update
    print("\n[3] Verifying trunk config after update...")
    resp2 = await lk_api.sip.list_sip_outbound_trunk(sip_proto.ListSIPOutboundTrunkRequest())
    for t in resp2.items:
        if t.sip_trunk_id == sip_trunk_id:
            print(f"    media_encryption = {t.media_encryption}")
            if t.media_encryption == 2:
                print("    ✅ SRTP is now REQUIRED — Twilio should accept calls!")
            elif t.media_encryption == 1:
                print("    ⚠️  SRTP is ALLOWED (may work)")
            else:
                print("    ❌ SRTP is still DISABLED — fix didn't apply!")
            break

    await lk_api.aclose()
    print("\nDone. Now run: python test_call.py")


if __name__ == "__main__":
    asyncio.run(main())

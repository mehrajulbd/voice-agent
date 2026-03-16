from livekit import rtc
from config.settings import LIVEKIT_URL

async def connect():

    room = rtc.Room()

    await room.connect(
        LIVEKIT_URL,
        auto_subscribe=True
    )

    return room

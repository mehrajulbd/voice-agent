import wave
import asyncio

async def stream_audio(track, audio_path):

    wf = wave.open(audio_path, 'rb')

    while True:
        data = wf.readframes(960)

        if len(data) == 0:
            break

        await track.write(data)
        await asyncio.sleep(0.02)

    wf.close()

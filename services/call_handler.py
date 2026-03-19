# filepath: /media/Main Files/tenbytes/livekit-call/services/call_handler.py
import os
import asyncio
import struct
import wave
import io
from typing import Optional
from dotenv import load_dotenv

from livekit import rtc, api

from services.tts_service import TTSService
from services.stt_service import STTService
from services.json_store import save_call_result, append_to_call_log
from services.gemini_service import GeminiService

load_dotenv()

# Constants for audio
SAMPLE_RATE = 48000
NUM_CHANNELS = 1
SAMPLES_PER_CHANNEL = 480  # 10ms frames at 48kHz


class CallHandler:
    """
    Handles a LiveKit room session:
    - Pre-synthesizes TTS audio before connecting
    - Connects to the room
    - Waits for the customer's AUDIO TRACK (not just participant presence)
    - Publishes TTS audio to the room
    - Records customer audio AFTER TTS finishes
    - Transcribes the customer audio and saves to JSON
    """

    def __init__(self, room_name: str, tts_text: str, phone_number: str,
                 language_code: str = "bn-BD", voice_name: Optional[str] = None):
        self.room_name = room_name
        self.tts_text = tts_text
        self.phone_number = phone_number
        self.language_code = language_code
        self.voice_name = voice_name
        self.tts_service = TTSService()
        self.stt_service = STTService()
        self.gemini_service = GeminiService()
        self.room = rtc.Room()
        self.recorded_audio: bytearray = bytearray()
        self._customer_audio_track_ready = asyncio.Event()
        self._recording_done = asyncio.Event()
        self._customer_disconnected = asyncio.Event()
        self._tts_finished = asyncio.Event()
        self._phone_participant: Optional[rtc.RemoteParticipant] = None
        self._record_duration = 15  # seconds to record customer response
        self._pcm_data: bytes = b""  # Pre-synthesized TTS PCM data
        self._customer_audio_stream = None

    async def run(self):
        """Main entry point: pre-synth TTS, connect, play, record, transcribe, save."""
        livekit_url = os.getenv("LIVEKIT_URL")
        api_key = os.getenv("LIVEKIT_API_KEY")
        api_secret = os.getenv("LIVEKIT_API_SECRET")

        # Step A: Pre-synthesize TTS audio BEFORE connecting
        print("[CallHandler] Pre-synthesizing TTS audio...")
        wav_bytes = self.tts_service.synthesize(
            self.tts_text,
            language_code=self.language_code,
            voice_name=self.voice_name
        )
        self._pcm_data = self._extract_pcm_from_wav(wav_bytes)
        tts_duration = len(self._pcm_data) / (SAMPLE_RATE * NUM_CHANNELS * 2)
        print(f"[CallHandler] TTS ready: {len(self._pcm_data)} bytes ({tts_duration:.1f}s)")

        # Step B: Generate access token
        token = (
            api.AccessToken(api_key, api_secret)
            .with_identity("bot-agent")
            .with_name("Bot Agent")
            .with_grants(api.VideoGrants(
                room_join=True,
                room=self.room_name,
            ))
        )
        jwt_token = token.to_jwt()

        # Step C: Set up event handlers
        self.room.on("track_subscribed", self._on_track_subscribed)
        self.room.on("participant_connected", self._on_participant_connected)
        self.room.on("participant_disconnected", self._on_participant_disconnected)

        # Step D: Connect to room
        print(f"[CallHandler] Connecting to room '{self.room_name}'...")
        await self.room.connect(livekit_url, jwt_token)
        print(f"[CallHandler] Connected to room as 'bot-agent'")

        # List existing participants for debugging
        print(f"[CallHandler] Remote participants in room: {list(self.room.remote_participants.keys())}")
        for pid, p in self.room.remote_participants.items():
            print(f"  - {p.identity} (tracks: {len(p.track_publications)})")
            for tp_sid, tp in p.track_publications.items():
                print(f"    track: {tp_sid} kind={tp.kind} subscribed={tp.subscribed}")

        # Step E: Wait for the customer's AUDIO TRACK to appear
        # This means the phone was actually answered and audio is flowing
        print("[CallHandler] Waiting for customer to ANSWER the call (audio track)...")
        print("[CallHandler] (The phone should be ringing now...)")
        try:
            await asyncio.wait_for(self._customer_audio_track_ready.wait(), timeout=90)
        except asyncio.TimeoutError:
            print("[CallHandler] Timeout — customer never answered. Aborting.")
            await self.room.disconnect()
            return

        print("[CallHandler] Customer answered! Audio track is active.")

        # Now verify the SIP call status is ACTIVE to ensure it's not early media
        print("[CallHandler] Verifying SIP call status is ACTIVE...")
        try:
            await self._wait_for_sip_active(timeout=30)
            print("[CallHandler] SIP call status is ACTIVE.")
        except asyncio.TimeoutError:
            print("[CallHandler] *** CALL FAILED *** SIP status never became ACTIVE.")
            print("[CallHandler] This usually indicates early media or a transient connection.")
            await self.room.disconnect()
            return

        # IMPORTANT: Wait a few seconds to confirm the call is stable
        # If the SIP call fails, the participant will disconnect within 1-2 seconds
        print("[CallHandler] Verifying call is stable (0.5s)...")
        await asyncio.sleep(0.5)
        if self._customer_disconnected.is_set():
            print("[CallHandler] *** CALL FAILED *** Customer disconnected immediately.")
            print("[CallHandler] This usually means:")
            print("  1. Twilio doesn't have international calling enabled for this destination")
            print("  2. The FROM number is not set correctly on the SIP trunk")
            print("  3. The SIP trunk configuration is incorrect")
            print("  4. Insufficient Twilio account balance")
            print("[CallHandler] Check your Twilio console for call logs/errors.")
            await self.room.disconnect()
            return

        # Small delay for audio to stabilize
        await asyncio.sleep(0.2)

        # Step F: Publish and play TTS audio
        print("[CallHandler] Playing TTS message to customer...")
        await self._publish_tts_audio()
        self._tts_finished.set()

        # Check if customer already disconnected during TTS
        if self._customer_disconnected.is_set():
            print("[CallHandler] Customer hung up during TTS playback.")
        else:
            # Step G: Record customer response
            print(f"[CallHandler] TTS done. Recording customer response for {self._record_duration}s...")

            # Wait for recording to complete or customer to disconnect
            try:
                await asyncio.wait_for(self._recording_done.wait(), timeout=self._record_duration + 5)
            except asyncio.TimeoutError:
                print("[CallHandler] Recording timeout reached.")

        # Step H: Transcribe
        transcription = ""
        if len(self.recorded_audio) > 0:
            audio_duration = len(self.recorded_audio) / (SAMPLE_RATE * NUM_CHANNELS * 2)
            print(f"[CallHandler] Recorded {len(self.recorded_audio)} bytes ({audio_duration:.1f}s) of audio")
            transcription = self.stt_service.transcribe(
                bytes(self.recorded_audio),
                sample_rate=SAMPLE_RATE,
                language_code=self.language_code
            )
        else:
            print("[CallHandler] No audio recorded from customer.")
            transcription = "(no audio received)"

        # Step I: Analyze with Gemini (dummy for now)
        confirmation_detected = False
        gemini_analysis = ""
        if transcription and transcription not in ["(no audio received)", "(audio too short)"]:
            try:
                confirmation_detected, gemini_analysis = self.gemini_service.analyze_confirmation(transcription)
            except Exception as e:
                print(f"[CallHandler] Gemini analysis failed: {e}")
                confirmation_detected = False
                gemini_analysis = "(error)"

        if confirmation_detected:
            print("[CallHandler] User confirmed! Would trigger external API here.")
            # TODO: Call external API with order confirmation data
        else:
            print("[CallHandler] User did not confirm (or analysis failed).")

        # Step J: Save to JSON with extra data
        extra = {
            "confirmation_detected": confirmation_detected,
            "gemini_analysis": gemini_analysis,
            "language": self.language_code
        }
        result_file = save_call_result(
            phone_number=self.phone_number,
            tts_text=self.tts_text,
            transcription=transcription,
            extra=extra
        )
        append_to_call_log({
            "phone_number": self.phone_number,
            "tts_text": self.tts_text,
            "customer_response": transcription,
            "result_file": result_file,
        })

        print(f"\n{'='*60}")
        print(f"  CALL RESULT")
        print(f"  Customer said: {transcription}")
        print(f"  Saved to: {result_file}")
        print(f"{'='*60}")

        # Disconnect
        await self.room.disconnect()
        print("[CallHandler] Disconnected from room.")

    async def _publish_tts_audio(self):
        """Publish pre-synthesized TTS audio frames to the room."""
        pcm_data = self._pcm_data

        # Create an audio source and track
        source = rtc.AudioSource(SAMPLE_RATE, NUM_CHANNELS)
        track = rtc.LocalAudioTrack.create_audio_track("tts-audio", source)

        # Publish the track
        options = rtc.TrackPublishOptions()
        options.source = rtc.TrackSource.SOURCE_MICROPHONE
        publication = await self.room.local_participant.publish_track(track, options)
        print(f"[CallHandler] Published TTS audio track: {publication.sid}")

        # Small delay so the track is fully negotiated
        await asyncio.sleep(0.5)

        # Send audio frames (10ms chunks)
        bytes_per_frame = SAMPLES_PER_CHANNEL * NUM_CHANNELS * 2
        offset = 0
        frame_count = 0

        while offset < len(pcm_data):
            if self._customer_disconnected.is_set():
                print("[CallHandler] Customer disconnected, stopping TTS.")
                break

            chunk = pcm_data[offset: offset + bytes_per_frame]
            if len(chunk) < bytes_per_frame:
                chunk = chunk + b'\x00' * (bytes_per_frame - len(chunk))

            frame = rtc.AudioFrame(
                data=chunk,
                sample_rate=SAMPLE_RATE,
                num_channels=NUM_CHANNELS,
                samples_per_channel=SAMPLES_PER_CHANNEL,
            )
            await source.capture_frame(frame)
            offset += bytes_per_frame
            frame_count += 1

            await asyncio.sleep(0.01)  # 10ms per frame

        # Trailing silence (500ms)
        silence = b'\x00' * bytes_per_frame
        for _ in range(50):
            frame = rtc.AudioFrame(
                data=silence,
                sample_rate=SAMPLE_RATE,
                num_channels=NUM_CHANNELS,
                samples_per_channel=SAMPLES_PER_CHANNEL,
            )
            await source.capture_frame(frame)
            await asyncio.sleep(0.01)

        await self.room.local_participant.unpublish_track(publication.sid)
        print(f"[CallHandler] TTS playback finished ({frame_count} frames).")

    def _extract_pcm_from_wav(self, wav_bytes: bytes) -> bytes:
        """Extract raw PCM data from WAV bytes."""
        with io.BytesIO(wav_bytes) as wav_io:
            with wave.open(wav_io, 'rb') as wav_file:
                pcm_data = wav_file.readframes(wav_file.getnframes())
        return pcm_data

    def _on_participant_connected(self, participant: rtc.RemoteParticipant):
        print(f"[CallHandler] Participant connected: {participant.identity}")
        if participant.identity.startswith("phone-"):
            self._phone_participant = participant
            print(f"[CallHandler] Phone participant object stored for status checking")

    def _on_participant_disconnected(self, participant: rtc.RemoteParticipant):
        print(f"[CallHandler] Participant disconnected: {participant.identity}")
        if participant.identity.startswith("phone-"):
            self._customer_disconnected.set()
            self._recording_done.set()

    def _on_track_subscribed(
        self,
        track: rtc.Track,
        publication: rtc.RemoteTrackPublication,
        participant: rtc.RemoteParticipant,
    ):
        print(f"[CallHandler] Track subscribed: kind={track.kind} from {participant.identity} (sid={track.sid})")
        if track.kind == rtc.TrackKind.KIND_AUDIO and participant.identity.startswith("phone-"):
            print(f"[CallHandler] *** Customer audio track active — call is answered! ***")
            self._customer_audio_track_ready.set()
            audio_stream = rtc.AudioStream(track)
            asyncio.ensure_future(self._record_audio_stream(audio_stream))

    async def _record_audio_stream(self, stream: rtc.AudioStream):
        """Record audio from the customer's audio stream (only after TTS finishes)."""
        print("[CallHandler] Audio stream started, waiting for TTS to finish before saving...")

        # Wait for TTS to finish before we start saving audio
        await self._tts_finished.wait()
        print("[CallHandler] Now recording customer audio...")

        start_time = asyncio.get_event_loop().time()

        async for event in stream:
            if self._customer_disconnected.is_set():
                break

            frame = event.frame
            self.recorded_audio.extend(frame.data)

            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed >= self._record_duration:
                print(f"[CallHandler] Recording duration reached ({self._record_duration}s)")
                self._recording_done.set()
                break

        print(f"[CallHandler] Finished recording. Total bytes: {len(self.recorded_audio)}")
        self._recording_done.set()

    async def _wait_for_sip_active(self, timeout: float = 30):
        """Wait until the phone participant's SIP call status becomes ACTIVE."""
        deadline = asyncio.get_event_loop().time() + timeout
        while True:
            # Try to find the phone participant
            participant = self._phone_participant
            if not participant:
                # Fallback: look up by identity
                expected_identity = f"phone-{self.phone_number}"
                for p in self.room.remote_participants.values():
                    if p.identity == expected_identity:
                        participant = p
                        self._phone_participant = p
                        break

            if participant:
                # Check SIP status via participant attributes (sip.callStatus)
                sip_status = participant.attributes.get("sip.callStatus", "unknown")
                if sip_status == "active":
                    return
                print(f"[CallHandler] SIP call status: {sip_status}; waiting for active...")
            remaining = deadline - asyncio.get_event_loop().time()
            if remaining <= 0:
                raise asyncio.TimeoutError()
            await asyncio.sleep(0.5)

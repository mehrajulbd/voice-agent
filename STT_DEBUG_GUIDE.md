# STT Debugging Guide

## Problem: "no voice detected"

If you're seeing `(no speech detected)` as the transcription, follow these steps to diagnose.

---

## Step 1: Enable Audio Debugging

Add to your `.env` file:

```bash
DEBUG_AUDIO=true
```

This will save the recorded audio from each call as a WAV file in `debug_audio/` directory.

---

## Step 2: Run a Test Call

Use the UI to place an order:

```bash
streamlit run ui/app.py
```

Make a call, answer the phone, and speak clearly (e.g., say "হ্যাঁ" or "yes").

---

## Step 3: Check the Saved Audio

After the call completes, look in the `debug_audio/` folder. You'll find a file like:

```
debug_audio/call_8801327403936_20250319_064730.wav
```

### Play it back:

**On Mac:**
```bash
afplay debug_audio/call_*.wav
```

**On Linux:**
```bash
aplay debug_audio/call_*.wav
```

**On Windows:** Open in any media player.

---

## Step 4: Analyze the Audio

Check the logs for these messages:

```
[CallHandler] Track info: sample_rate=48000, num_channels=1
[CallHandler] Finished recording. Total bytes: 1440000
[CallHandler] DEBUG: Audio all zeros: False
[CallHandler] Saved debug audio to: debug_audio/call_...
```

### Scenarios:

**A. Audio file contains clear speech**
- This means the recording is working.
- The issue is likely **sample rate mismatch**. Check the logged `sample_rate`. If it's NOT 48000, the STT request may be using the wrong rate.
- Fix: The code now uses the actual track's sample rate automatically. If you still see issues, verify the logged sample rate matches what you send to STT.

**B. Audio file is all silence (static or quiet)**
- Means the customer's audio track isn't sending data (maybe silent in the stream).
- Check the call: Is the customer actually speaking? Is the microphone working?
- Also check if the track's sample rate looks correct (should be 48000 or 16000, etc.)

**C. Audio file sounds like noise/static**
- Could be wrong sample format. LiveKit should deliver 16-bit PCM, but if it's actually float32, the WAV will be corrupted.
- In that case, we need to convert the audio format before sending to STT.

---

## Step 5: Check Language Code

The STT API requires **bn-IN** for Bengali, not **bn-BD**.

The UI now uses `bn-IN` in the language dropdown. If you previously had `bn-BD` in your `.env` or call_config.json, it has been mapped to `bn-IN` in `call_runner.py`.

Make sure you're using a supported language:
- `bn-IN` - Bengali (India)
- `en-US` - English (US)

---

## Step 6: Verify STT API Works

Test the STT service directly with a known WAV file:

```python
from services.stt_service import STTService
with open("test.wav", "rb") as f:
    # You need to extract PCM from WAV (skip header)
    import wave
    with wave.open("test.wav", 'rb') as wav:
        pcm = wav.readframes(wav.getnframes())
        sr = wav.getframerate()
        svc = STTService()
        text = svc.transcribe(pcm, sample_rate=sr, language_code="bn-IN")
        print(text)
```

If this works, the STT service is fine.

---

## Common Fixes Already Applied

1. ✅ Language code mapping: `bn-BD` → `bn-IN`
2. ✅ Using actual track sample rate instead of hardcoded 48000
3. ✅ Debug audio dumping
4. ✅ Zero-silence detection in logs

---

## Still Not Working?

If you've gone through the steps and the audio file has clear speech but STT still says "no speech detected", gather these logs:

```
[CallHandler] Track info: sample_rate=..., num_channels=...
[CallHandler] Finished recording. Total bytes: ...
[CallHandler] DEBUG: Audio all zeros: ...
[STTService] Transcription: (no speech detected)
```

And open an issue with those details.

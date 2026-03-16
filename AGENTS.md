# Agent Guidelines for LiveKit Call System

## Build/Lint/Test Commands

### Running the Application
```bash
# Main application - automated call flow with TTS and transcription
python main.py

# Simple test to check SIP call connectivity and monitor status
python test_call.py

# Monitor call status events (diagnostic tool)
python check_call_status.py

# Debug Twilio SIP configuration
python debug_twilio_sip.py

# Make a simple SIP call without TTS/STT
python call/make_call.py
```

### Running Single Tests
The codebase uses standalone diagnostic scripts rather than a formal test framework:
- `test_call.py` - Minimal test to diagnose SIP call failures
- `check_call_status.py` - Monitors room events to see exact call flow
- `check_sip.py` - Validates SIP trunk configuration

### Environment Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your actual credentials
```

### Linting/Formatting
This project follows PEP 8 standards:
- Use `black` for formatting (if needed: `pip install black && black .`)
- Use `flake8` for linting (if needed: `pip install flake8 && flake8`)
- Maximum line length: 88 characters (black default)

---

## Code Style Guidelines

### General Principles
1. Use type hints for all function parameters and return values
2. Write docstrings for all classes and public methods (Google style)
3. Prefer async/await for I/O operations (this is an async codebase)
4. Handle exceptions explicitly with try/except blocks
5. Log errors with print statements for now (structured logging could be added)

### Imports
```python
# Standard library imports first
import asyncio
import os
import json
from datetime import datetime

# Third-party imports second
from livekit import rtc, api
from dotenv import load_dotenv

# Local imports last, organized by module
from services.tts_service import TTSService
from services.stt_service import STTService
from config.settings import LIVEKIT_URL
```

### Formatting
- Indentation: 4 spaces (no tabs)
- Blank lines: 2 between top-level functions/classes, 1 between methods
- Trailing commas in multi-line collections
- Parentheses: use implicit line continuation inside parentheses
- Follow PEP 8 for naming and structure

### Naming Conventions
- Files: `snake_case.py` (e.g., `call_handler.py`, `tts_service.py`)
- Classes: `PascalCase` (e.g., `CallHandler`, `TTSService`)
- Functions: `snake_case` (e.g., `make_call()`, `transcribe()`)
- Variables: `snake_case` (e.g., `room_name`, `audio_bytes`)
- Constants: `UPPER_SNAKE_CASE` (e.g., `SAMPLE_RATE`, `NUM_CHANNELS`)
- Private methods/attributes: prefix with `_` (e.g., `_publish_tts_audio`)

### Types
- Use type hints everywhere: `def func(param: str) -> bytes:`
- Common types in this codebase:
  - `bytes` for audio data
  - `str` for text
  - `int`/`float` for numeric values
  - `asyncio.Event` for synchronization
  - `rtc.Room`, `rtc.RemoteParticipant` from LiveKit SDK

### Error Handling
- Use specific exception types, not bare `except:`
- Log exceptions with context: `print(f"[module] Error: {e}")`
- Re-raise when appropriate: `raise ValueError("message") from e`
- Validate inputs early (fail fast)
- Check environment variables at startup

### Async Patterns
- Always `await` async calls
- Use `asyncio.Event()` for cross-coroutine signaling
- Use `asyncio.wait_for()` with timeouts to prevent hangs
- Use `asyncio.create_task()` or `asyncio.ensure_future()` for background tasks
- Avoid blocking calls in async functions (no `time.sleep()`, use `await asyncio.sleep()`)

### Project Structure
```
livekit-call/
├── main.py                    # Entry point with full TTS+STT flow
├── test_call.py              # Minimal diagnostic test
├── check_call_status.py      # Event monitoring tool
├── config/
│   └── settings.py          # Centralized configuration (env vars)
├── call/
│   ├── make_call.py         # SIP call initiation
│   ├── call_handler.py      # Legacy handler (transcribe only)
│   └── livekit_client.py    # Room connection helper
├── services/
│   ├── tts_service.py       # Google TTS integration
│   ├── stt_service.py       # Google STT integration
│   ├── json_store.py        # Result persistence
│   └── call_handler.py      # Main call orchestration
├── audio/
│   └── audio_utils.py       # Audio streaming utilities
├── results/                 # Output JSON files (created at runtime)
└── .env                     # Environment configuration
```

### LiveKit-Specific Guidelines
- Room connections: use `await room.connect(url, token)`
- Track subscriptions: check `track.kind == rtc.TrackKind.KIND_AUDIO`
- Audio frames: 10ms chunks at 48kHz = 960 samples per frame
- Participant identity: phone numbers prefixed with "phone-" (e.g., "phone-+15551234567")
- Always disconnect rooms with `await room.disconnect()`

### Google API Guidelines
- TTS/STT use REST API with API key (not service account)
- Audio encoding: LINEAR16, 48kHz, mono
- STT maximum: ~55 seconds to stay within API limits
- Base64 encode audio bytes before sending to API
- Handle API errors gracefully and return fallback messages

### Environment Variables
All required in `.env`:
- `LIVEKIT_URL` - LiveKit server URL
- `LIVEKIT_API_KEY` - LiveKit API key
- `LIVEKIT_API_SECRET` - LiveKit API secret
- `SIP_TRUNK_ID` - LiveKit SIP trunk ID (from Twilio)
- `FROM_PHONE_NUMBER` - Your Twilio phone number (E.164 format)
- `GOOGLE_API_KEY` - Google Cloud API key with TTS and STT enabled
- `TARGET_PHONE_NUMBER` - Default phone to call (optional)

---

## Common Pitfalls

1. **Twilio International Calling**: Bangladesh (+880) blocked by default. Enable in Twilio Geo Permissions.
2. **SIP Trunk Auth**: Ensure credential list username matches `sip_number` field.
3. **Call Status**: True "answered" state requires AUDIO track, not just participant presence.
4. **Audio Timing**: Record customer AFTER TTS finishes; use `_tts_finished` event.
5. **Sample Rate**: Keep consistent 48kHz throughout (LiveKit standard).
6. **API Keys**: Use API key for Google APIs, not OAuth tokens.
7. **Room Cleanup**: Always disconnect rooms to avoid resource leaks.

---

## Agent Instructions

When modifying this codebase:
- Preserve async patterns and proper error handling
- Keep type hints complete and accurate
- Follow existing file organization (services, call, config)
- Add print statements for key state changes (existing pattern)
- Validate environment variables before use
- Test with `test_call.py` or `check_call_status.py` after changes
- Do not remove or alter existing diagnostic output without discussion

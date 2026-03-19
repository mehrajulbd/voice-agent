# LiveKit Automated Call System

An automated telephone calling system that uses LiveKit's SIP integration with Twilio to place outbound calls, deliver a pre-recorded message using Google Text-to-Speech (TTS), and transcribe the recipient's response using Google Speech-to-Text (STT).

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your actual credentials
```

Required environment variables:
- `LIVEKIT_URL` - LiveKit server URL
- `LIVEKIT_API_KEY` - LiveKit API key
- `LIVEKIT_API_SECRET` - LiveKit API secret
- `SIP_TRUNK_ID` - LiveKit SIP trunk ID (from Twilio)
- `FROM_PHONE_NUMBER` - Your Twilio number (E.164 format)
- `GOOGLE_API_KEY` - Google Cloud API key with TTS and STT enabled

### 3. Run the Web UI (Recommended)

```bash
streamlit run ui/app.py
```

Open http://localhost:8501 in your browser and start ordering!

---

## Architecture Overview

### System Flow

1. **Call Initiation**: `main.py` → `call/make_call.py` creates a SIP participant via LiveKit API
2. **Room Connection**: `services/call_handler.py` connects a bot agent to the room
3. **Call Answer Detection**: Wait for customer's audio track to appear (confirms call answered)
4. **TTS Playback**: Pre-synthesized message is published as an audio track
5. **Response Recording**: Customer audio is captured after TTS finishes
6. **Transcription**: Recorded audio sent to Google STT API
7. **Persistence**: Results saved as JSON files in `results/` directory

### Key Components

#### Core Modules

- **`main.py`** - Entry point that orchestrates the full call flow
  - Validates environment configuration
  - Initiates SIP call via `make_call()`
  - Creates `CallHandler` and runs the call session
  - Prints status updates and final results

- **`call/make_call.py`** - SIP call creation
  - Builds `CreateSIPParticipantRequest` protobuf
  - Sets caller ID (`sip_number`) and destination (`sip_call_to`)
  - Returns room name for the call
  - Handles API errors and connection cleanup

- **`services/call_handler.py`** - Main call orchestration (NEW)
  - Pre-synthesizes TTS audio before connecting (reduces latency)
  - Connects to LiveKit room as bot agent
  - Waits for customer audio track (real call answer detection)
  - Publishes TTS audio track with 10ms frames
  - Records customer response after TTS completes
  - Transcribes via STTService and saves results
  - Uses asyncio events for coordination (`_customer_audio_track_ready`, `_tts_finished`, `_recording_done`)

- **`services/call_handler.py`** - Legacy simple handler (kept for reference)
  - Simple `handle_audio()` function for transcribing raw bytes
  - Minimal implementation for simpler use cases

#### Service Layer

- **`services/tts_service.py`** - Google Text-to-Speech
  - Uses Google Cloud TTS REST API with API key
  - Synthesizes text to LINEAR16, 48kHz, mono WAV
  - Returns raw WAV bytes
  - `synthesize_to_file()` utility for debugging

- **`services/stt_service.py`** - Google Speech-to-Text
  - Uses Google Cloud STT REST API with API key
  - Accepts raw PCM bytes (LINEAR16)
  - Auto-trims to ~55 seconds (API limit)
  - Skips audio < 0.5 seconds
  - Returns transcript string with automatic punctuation

- **`services/json_store.py`** - Result persistence
  - `save_call_result()` - Saves individual call as timestamped JSON
  - `append_to_call_log()` - Maintains cumulative `call_log.json`
  - Files stored in `results/` directory

#### Configuration

- **`config/settings.py`** - Centralized environment variables
  - Loads `.env` via `python-dotenv`
  - Exports constants: LIVEKIT_URL, LIVEKIT_API_KEY, etc.
  - NOTE: Some fields like `LIVEKIT_TRUNK_ID` have mismatch with actual usage (`SIP_TRUNK_ID`)

- **`config/call_config.json`** - Legacy call configuration (optional)
  - Contains default company_name, product_name, quantity, language_code, voice_name
  - Used by `main.py` for backward compatibility
  - New UI uses `products.json` instead

- **`config/products.json`** - Product catalog for web UI
  - Contains company_name and array of products
  - Each product has: id, name, name_en, unit, default_quantity, price_per_unit, currency
  - This is the source for the product selection UI

#### Utilities

- **`audio/audio_utils.py`** - Async audio streaming helper
  - `stream_audio()` - Streams WAV file to LiveKit audio track
  - Used by older code; new code uses pre-synthesized PCM frames

- **`call/livekit_client.py`** - Simple room connection helper
  - Basic `connect()` function for quick room joins

#### New Features (2025)

- **`services/product_service.py`** - Product catalog management
  - Loads products from `config/products.json`
  - Provides `Product` dataclass with name, price, unit
  - Used by the web UI to display catalog

- **`call_runner.py`** - High-level call orchestration
  - `place_call()` function - single entry point for making calls
  - Accepts product_id, quantity, phone, language parameters
  - Returns structured results with transcription and confirmation status
  - Used by both CLI and web UI

- **`ui/app.py`** - Streamlit web interface
  - Product catalog browser with 3-column responsive grid
  - Checkout form with quantity and phone input
  - Real-time call progress display with spinners
  - Results page with transcription and analysis
  - Session state management for multi-page flow

---

#### Diagnostic Tools

- **`test_call.py`** - Minimal call test with detailed status logging
  - Monitors `sip.callStatus` attribute changes
  - Provides Twilio-specific failure diagnosis
  - Shows timeline of call events

- **`check_call_status.py`** - Comprehensive room event monitor
  - Tracks participant connections, disconnections, track subscriptions
  - Useful for debugging SIP trunk configuration issues
  - Provides Twilio geo-permission guidance

- **`debug_twilio_sip.py`** - Advanced Twilio SIP debugging
  - Tests different `sip_number` and `number` field placements
  - Experiments with `play_dialtone`, `ringing_timeout`, etc.

- **`check_sip.py`** - Validates SIP trunk exists in LiveKit
- **`fix_srtp.py`** - SRTP encryption troubleshooting
- **`debug_proto.py`** - Protobuf field inspection

### Data Flow

```
┌─────────────┐
│   main.py   │
└──────┬──────┘
       │ 1. Initiate call
       ▼
┌─────────────────────┐
│  call/make_call.py  │
│  (CreateSIPParticipantRequest) │
└──────┬──────────────┘
       │ 2. Room name returned
       ▼
┌────────────────────────┐
│ services/call_handler.py │
│  - Connect to room     │
│  - Wait for audio      │
│  - Play TTS            │
│  - Record              │
│  - Transcribe          │
└──────┬─────────────────┘
       │ 3. Transcription result
       ▼
┌────────────────────┐
│ services/json_store│
│  → results/*.json  │
└────────────────────┘
```

### Audio Pipeline

1. **TTS**: Text → Google TTS → WAV bytes → Extract PCM → `bytearray` buffer
2. **Publishing**: PCM → 10ms frames → `rtc.AudioFrame` → `source.capture_frame()`
3. **Recording**: Customer audio → `rtc.AudioStream` → accumulate bytes
4. **STT**: Raw PCM bytes (48kHz, LINEAR16) → Google STT → transcript

### Technology Stack

- **Language**: Python 3.8+ with asyncio
- **LiveKit SDK**: `livekit` package (real-time audio/video)
- **Google Cloud**: Text-to-Speech & Speech-to-Text REST APIs
- **Twilio**: Elastic SIP Trunking (configured in LiveKit, not directly called)
- **Configuration**: `python-dotenv` for environment variables

---

## Setup Instructions

### Prerequisites

1. LiveKit Cloud account (self-hosted also works)
2. Twilio account with Elastic SIP Trunk configured
3. Google Cloud project with TTS and STT APIs enabled
4. Python 3.8+

### Installation

```bash
# Clone and enter directory
cd livekit-call

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your credentials
```

### Required Services

#### LiveKit
- Create a SIP trunk linked to your Twilio account
- Note the SIP Trunk ID
- Ensure LiveKit URL, API key, and API secret are available

#### Twilio
- Purchase a phone number
- Configure Elastic SIP Trunking
- Set up Credential List (username/password) for authentication
- **Important**: Enable destination country in Geo Permissions (e.g., Bangladesh)
- Termination URI should match LiveKit's expectation: typically `.pstn.twilio.com`

#### Google Cloud
- Enable Text-to-Speech API
- Enable Speech-to-Text API
- Create API key (not OAuth)
- Ensure API key has permissions for both services

### Environment Variables

| Variable | Required | Purpose |
|----------|----------|---------|
| `LIVEKIT_URL` | Yes | WebSocket URL of LiveKit server |
| `LIVEKIT_API_KEY` | Yes | LiveKit API key |
| `LIVEKIT_API_SECRET` | Yes | LiveKit API secret |
| `SIP_TRUNK_ID` | Yes | LiveKit SIP trunk identifier |
| `FROM_PHONE_NUMBER` | Yes | Twilio number (E.164 format: `+15551234567`) |
| `GOOGLE_API_KEY` | Yes | Google Cloud API key |
| `TARGET_PHONE_NUMBER` | No | Default number to call |

---

## Running the System

### Basic Usage

```bash
# Quick test with default number in .env
python main.py

# Or change TARGET_PHONE_NUMBER in .env first
```

### Web UI (Recommended)

The system now includes a beautiful Streamlit web interface for ordering:

```bash
# Run the web UI
streamlit run ui/app.py

# Access at http://localhost:8501
```

The web UI provides:
- **Product Catalog**: Browse available products with prices
- **Checkout Form**: Select quantity and enter phone number
- **Call Progress**: Real-time status updates during the call
- **Results Page**: View transcription and confirmation status

---

### Diagnostic Workflow

If calls fail immediately:

1. **Check SIP trunk validity**:
   ```bash
   python check_sip.py
   ```

2. **Monitor call status**:
   ```bash
   python test_call.py
   ```
   - Look for `sip.callStatus` changes: `dialing`, `ringing`, `active`, `failed`
   - If `dialing` → Twilio rejected (check geo permissions, balance)
   - If `ringing` but never `active` → phone not answered

3. **Detailed event monitoring**:
   ```bash
   python check_call_status.py
   ```
   - Answer the phone when it rings
   - Watch for participant connect/disconnect timing
   - Immediate disconnect = SIP failure at Twilio level

4. **Twilio debugging**:
   ```bash
   python debug_twilio_sip.py
   ```

### Expected Output

```
============================================================
  LiveKit + Twilio SIP Automated Call System
============================================================
  Target Phone : +8801327403936
  TTS Message  : Hello. This is an automated call...
  From Number  : +16562554399
  LiveKit URL  : wss://your-project.livekit.cloud
  SIP Trunk    : your_sip_trunk_id
  Google API   : SET
============================================================

[main] Step 1: Initiating SIP outbound call...
[make_call] LiveKit URL: wss://...
...
[CallHandler] Customer answered! Audio track is active.
[CallHandler] Playing TTS message to customer...
[CallHandler] TTS playback finished (X frames).
[CallHandler] Recording customer response for 15s...
[CallHandler] Recorded X bytes (Y.s) of audio
[STTService] Transcription: "Hello, yes I am here"

============================================================
  CALL RESULT
  Customer said: Hello, yes I am here
  Saved to: results/call_20260317_023456.json
============================================================
```

---

## Troubleshooting

### Call Fails Immediately (No Ring)

- **Check**: Twilio Geo Permissions for destination country
- **Check**: Twilio account balance
- **Check**: SIP trunk termination URI matches Twilio config
- **Check**: `FROM_PHONE_NUMBER` is correct Twilio number
- **Check**: LiveKit logs for SIP errors

### Call Rings but Never Answers

- Verify phone number is correct
- Check if phone is accessible
- `test_call.py` will show `ringing` but not `active`

### No Audio Recorded

- Customer may have hung up before recording started
- Check `_customer_audio_track_ready` event timing
- Ensure LiveKit room has proper audio subscription

### Transcription Fails

- Verify `GOOGLE_API_KEY` is valid and STT API enabled
- Check audio duration < 55 seconds
- Audio must be LINEAR16, 48kHz mono (this code ensures that)
- STT returns `(transcription failed)` on HTTP errors

### TTS Fails

- Verify TTS API enabled in Google Cloud
- Check API key permissions
- Text length reasonable (< 5KB typical)

---

## File Structure

```
livekit-call/
├── AGENTS.md              # This file's agent guidelines (see separate doc)
├── README.md              # This documentation
├── main.py                # Main entry point
├── test_call.py           # Minimal diagnostic test
├── check_call_status.py   # Event monitoring tool
├── check_sip.py           # SIP trunk validator
├── debug_*.py             # Various debugging utilities
├── requirements.txt       # Python dependencies
├── .env.example           # Environment template
├── .env                   # Local configuration (gitignored)
├── config/
│   └── settings.py       # Environment variable loading
├── call/
│   ├── __init__.py
│   ├── make_call.py      # SIP call creation
│   ├── call_handler.py   # Legacy simple handler
│   └── livekit_client.py # Room connection helper
├── services/
│   ├── __init__.py
│   ├── tts_service.py    # Google TTS
│   ├── stt_service.py    # Google STT
│   ├── json_store.py     # JSON persistence
│   └── call_handler.py   # Main orchestration
├── audio/
│   └── audio_utils.py    # Audio streaming utilities
└── results/              # Generated JSON files
    ├── call_*.json       # Individual call results
    └── call_log.json     # Cumulative log
```

---

## Development Notes

### Async Architecture

This codebase uses Python's `asyncio` throughout. Key patterns:

- **Events**: `asyncio.Event()` for cross-coroutine synchronization
  - `_customer_audio_track_ready` - set when audio track appears
  - `_tts_finished` - set when TTS playback completes
  - `_recording_done` - set when recording duration reached

- **Timeouts**: Always use `asyncio.wait_for()` to prevent indefinite hangs
  - Example: `await asyncio.wait_for(event.wait(), timeout=90)`

- **Room Events**: LiveKit uses event callbacks; handlers must be synchronous wrappers that schedule async work

### Audio Timing

- LiveKit standard: 48kHz, 16-bit, mono
- Frame size: 10ms → 480 samples per frame → 960 bytes per frame
- Publishing: `source.capture_frame(rtc.AudioFrame(...))`
- TTS frames sent every 0.01s (10ms)

### SIP Call States

Understanding `sip.callStatus` attribute on participant:
- `dialing` - Outbound call initiated, not yet answered
- `ringing` - Destination phone ringing
- `active` - Call answered and audio flowing
- `completed` - Call ended normally
- `failed` - Call failed (busy, rejected, network error)

---

## Contributing

When making changes:

1. Run diagnostic tests to verify behavior
2. Add print statements for important state changes (existing pattern)
3. Preserve async/await structure
4. Maintain type hints
5. Keep environment variable validation
6. Update this README if architecture changes

---

## License

[Add license information here]

---

## Support

For issues:
1. Run `test_call.py` and capture output
2. Check LiveKit room logs for participant events
3. Verify Twilio console for call logs
4. Google Cloud console for API errors
5. Open issue with diagnostic logs

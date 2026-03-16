# filepath: /media/Main Files/tenbytes/livekit-call/services/json_store.py
import os
import json
from datetime import datetime


RESULTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results")


def ensure_results_dir():
    os.makedirs(RESULTS_DIR, exist_ok=True)


def save_call_result(phone_number: str, tts_text: str, transcription: str, extra: dict = None):
    """
    Save a call result to a JSON file in the results/ directory.
    Each call gets its own timestamped JSON file.
    """
    ensure_results_dir()

    timestamp = datetime.now().isoformat()
    filename = f"call_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    filepath = os.path.join(RESULTS_DIR, filename)

    data = {
        "timestamp": timestamp,
        "phone_number": phone_number,
        "tts_text_sent": tts_text,
        "customer_response": transcription,
    }
    if extra:
        data.update(extra)

    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)

    print(f"[json_store] Call result saved to {filepath}")
    return filepath


def append_to_call_log(entry: dict):
    """Append an entry to a cumulative call_log.json file."""
    ensure_results_dir()
    log_path = os.path.join(RESULTS_DIR, "call_log.json")

    if os.path.exists(log_path):
        with open(log_path, "r") as f:
            log = json.load(f)
    else:
        log = []

    log.append(entry)

    with open(log_path, "w") as f:
        json.dump(log, f, indent=2)

    print(f"[json_store] Entry appended to {log_path}")
    return log_path

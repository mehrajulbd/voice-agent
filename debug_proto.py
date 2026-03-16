# filepath: /media/Main Files/tenbytes/livekit-call/debug_proto.py
"""Debug script to check CreateSIPParticipantRequest fields."""
from livekit.protocol.sip import CreateSIPParticipantRequest

# Print all fields in the protobuf message
print("Fields in CreateSIPParticipantRequest:")
for field in CreateSIPParticipantRequest.DESCRIPTOR.fields:
    print(f"  {field.name} (type={field.type}, number={field.number})")

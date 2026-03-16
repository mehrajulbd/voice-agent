#!/bin/bash
find /media/Main\ Files/tenbytes/livekit-call -type f -not -path '*/venv/*' -not -path '*/__pycache__/*' -not -path '*/.git/*' -not -name '*.pyc' | sort


import sys
import unittest
from unittest.mock import patch

# Mock ffprobe BEFORE importing main
# 741 seconds = 12 mins 21 seconds
with patch('src.audio_engine.AudioAligner.get_audio_duration', return_value=741.0):
    import main
    
    # Modify sys.argv to inject arguments
    sys.argv = [
        "main.py",
        "--run_id", "CANON_RUN",
        "--version", "7",
        "--stage", "planning",
        "--mode", "simulation"
    ]
    
    print(">>> RUNNING CANON VERIFICATION (Mocked Duration=741.0s) <<<")
    try:
        main.main()
    except Exception as e:
        print(f"CRASHED: {e}")
        import traceback
        traceback.print_exc()

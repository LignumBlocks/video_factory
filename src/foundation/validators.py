import os
from mutagen.mp3 import MP3
from mutagen import MutagenError

def validate_input_files(script_path: str, audio_path: str, style_bible_path: str) -> dict:
    """
    Validates existence, extensions, and content of inputs.
    Returns: Preflight Report Dictionary
    """
    checks = []
    overall_passed = True

    # 1. Script Validation
    check_script = {"name": "script_valid", "passed": False, "detail": ""}
    if not os.path.exists(script_path):
        check_script["detail"] = "File not found"
    elif not (script_path.lower().endswith('.txt') or script_path.lower().endswith('.md')):
        check_script["detail"] = "Invalid extension"
    elif os.path.getsize(script_path) == 0:
        check_script["detail"] = "File is empty"
    else:
        check_script["passed"] = True
        check_script["detail"] = f"size={os.path.getsize(script_path)} bytes"
    
    if not check_script["passed"]: overall_passed = False
    checks.append(check_script)

    # 2. Audio Validation
    check_audio = {"name": "voiceover_valid", "passed": False, "detail": ""}
    if not os.path.exists(audio_path):
        check_audio["detail"] = "File not found"
    elif not (audio_path.lower().endswith('.mp3') or audio_path.lower().endswith('.wav')):
        check_audio["detail"] = "Invalid extension"
    else:
        try:
            audio = MP3(audio_path)
            if audio.info.length > 0:
                check_audio["passed"] = True
                check_audio["detail"] = f"duration_s={audio.info.length:.2f}"
            else:
                 check_audio["detail"] = "Audio duration is 0"
        except MutagenError:
            check_audio["detail"] = "Invalid or Corrupted MP3 file"
        except Exception as e:
            check_audio["detail"] = f"Error reading audio: {str(e)}"
    
    if not check_audio["passed"]: overall_passed = False
    checks.append(check_audio)

    # 3. Style Bible Validation
    check_bible = {"name": "bible_locked", "passed": False, "detail": ""}
    if not os.path.exists(style_bible_path):
        check_bible["detail"] = "File not found"
    elif not (style_bible_path.lower().endswith('.md') or style_bible_path.lower().endswith('.txt')):
        check_bible["detail"] = "Invalid extension"
    elif os.path.getsize(style_bible_path) == 0:
        check_bible["detail"] = "File is empty"
    else:
        try:
            with open(style_bible_path, 'r', encoding='utf-8') as f:
                content = f.read(4096) 
                if "LOCKED" in content:
                    check_bible["passed"] = True
                    check_bible["detail"] = "Found LOCKED marker"
                else:
                    check_bible["detail"] = "Missing 'LOCKED' marker"
        except Exception as e:
             check_bible["detail"] = f"Error reading file: {str(e)}"

    if not check_bible["passed"]: overall_passed = False
    checks.append(check_bible)

    return {
        "passed": overall_passed,
        "checks": checks
    }

import os

def validate_input_files(script_path: str, audio_path: str, style_bible_path: str):
    """
    Validates existence, extensions, and basic content validity of inputs.
    Raises FileNotFoundError or ValueError on failure.
    """
    # 1. Check existence
    if not os.path.exists(script_path):
        raise FileNotFoundError(f"Script file not found: {script_path}")
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Audio file not found: {audio_path}")
    if not os.path.exists(style_bible_path):
        raise FileNotFoundError(f"Style Bible file not found: {style_bible_path}")

    # 2. Check extensions (Case insensitive)
    if not script_path.lower().endswith('.txt'):
        raise ValueError(f"Script must be a .txt file: {script_path}")
    if not audio_path.lower().endswith('.mp3'):
        raise ValueError(f"Voiceover must be a .mp3 file: {audio_path}")
    if not (style_bible_path.lower().endswith('.md') or style_bible_path.lower().endswith('.txt')):
        raise ValueError(f"Style Bible must be .md or .txt: {style_bible_path}")

    # 3. Check emptiness
    if os.path.getsize(script_path) == 0:
        raise ValueError(f"Script file is empty: {script_path}")
    if os.path.getsize(audio_path) == 0:
        raise ValueError(f"Audio file is empty: {audio_path}")
    if os.path.getsize(style_bible_path) == 0:
        raise ValueError(f"Style Bible file is empty: {style_bible_path}")

    # 4. Check Bible "LOCKED" status (Architecture Constraint)
    # The architecture doc says: "STYLE_BIBLE_LOCKED.md (Clean Score Jump)"
    # We essentially scan the first few lines for "LOCKED" keyword to ensure it's a ready document.
    with open(style_bible_path, 'r', encoding='utf-8') as f:
        head = f.read(1024)
        if "LOCKED" not in head:
             # Warning only? Or strict? The Architecture says "Locked: Clean Score Jump".
             # Let's be strict for T-0.2
             raise ValueError(f"Style Bible does not match 'LOCKED' criteria in header: {style_bible_path}")

    return True

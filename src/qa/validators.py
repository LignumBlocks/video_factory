import os
from .engine import QAStatus, QAResult

def validate_image_file(path: str) -> QAResult:
    """
    Checks if image file exists and is a valid format.
    """
    if not os.path.exists(path):
        return QAResult(QAStatus.FAIL, f"Image file not found: {path}", retry_suggested=True)
    
    if os.path.getsize(path) == 0:
        return QAResult(QAStatus.FAIL, "Image file is empty", retry_suggested=True)
        
    lower_path = path.lower()
    if not (lower_path.endswith('.png') or lower_path.endswith('.jpg')):
         return QAResult(QAStatus.WARNING, "Image format not PNG/JPG")

    return QAResult(QAStatus.PASS, "File check passed")

def validate_clip_duration(path: str) -> QAResult:
    """
    Checks if clip exists and has acceptable duration (approx 8s).
    NOTE: Requires ffprobe or moviepy. For MVP we check file existence/extension only
    mocking the duration check to avoid heavy dependencies on this iteration.
    """
    if not os.path.exists(path):
        return QAResult(QAStatus.FAIL, f"Clip file not found: {path}", retry_suggested=True)

    if not path.endswith('.mp4'):
        return QAResult(QAStatus.FAIL, "Clip must be MP4", retry_suggested=True)
        
    # TODO: Implement actual `ffprobe` duration check here.
    # For now, we assume if it exists and is > 100KB, it's likely okay.
    if os.path.getsize(path) < 100 * 1024: # < 100KB
        return QAResult(QAStatus.FAIL, "Clip file too small (<100KB)", retry_suggested=True)

    return QAResult(QAStatus.PASS, "Clip check passed (Mock Duration)")

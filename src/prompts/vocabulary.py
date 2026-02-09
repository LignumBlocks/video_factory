# Strict Vocabulary Enforcement

FORBIDDEN_TERMS = [
    # System terms (LOCKED)
    "blueprint", "noir",
    "ui", "hud",
    "trace", "unlock", "verified",
    "route", "overlay",
    "label", "text", "markings",
    "signage", "caption", "subtitle", "watermark", "logo",
    "username", "copyright", "signature",
    
    # Content restrictions
    "fleshy", "skin", "naked", "nude", "nsfw",
    "glitch", "distorted", "morbid", "mutilated",
    "blur", "haze", "noise",
    
    # Closed System Violations
    "spill", "pour", "leak", "puddle", "splash"
]

NEGATIVE_PROMPT_DEFAULT = (
    "no humans, no text, no markings, no labels, no symbols, "
    "blur, distortion, glitch, low quality, "
    "watermark, user interface, hud"
)

# Strict Hard Lock Injection (Always Appended)
# Focus: Safety & Contract Compliance only. No style/quality heuristics.
HARD_LOCK_INJECTION = "clean surfaces, closed system, no humans"

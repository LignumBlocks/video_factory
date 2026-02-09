from enum import Enum

class BeatVerb(str, Enum):
    EXPECTATION = "EXPECTATION"
    TRACE = "TRACE"
    UNLOCK = "UNLOCK"

class BeatState(str, Enum):
    LOCKED = "LOCKED"
    NOISY = "NOISY"
    CLEAN = "CLEAN"
    VERIFIED = "VERIFIED"
    UNLOCKED = "UNLOCKED"

class BeatLayer(str, Enum):
    BLUEPRINT = "Blueprint"
    EVIDENCE = "Evidence"
    MICRO = "Micro"

class BeatIntensity(str, Enum):
    L1 = "L1"
    L2 = "L2"
    L3 = "L3"

class ClipActionCategory(str, Enum):
    GATE_CLICK = "GATE_CLICK"
    FILTER_WASH = "FILTER_WASH"
    LEDGER_IMPRINT = "LEDGER_IMPRINT"
    SNAPSHOT = "SNAPSHOT"
    STAIR_STEP = "STAIR_STEP"
    THROTTLE = "THROTTLE"
    BREATH = "BREATH"
    # Fallback/Default
    GENERIC = "GENERIC"

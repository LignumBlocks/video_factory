from .enums import ClipActionCategory

ACTION_LIBRARY = {
    ClipActionCategory.SNAPSHOT: {
        "REST": "Inner assembly settles into a stable resting state",
        "PRESS_DEEP": "Core plate presses one notch deeper",
        "PRESS_LIGHT": "Core plate presses one notch lighter"
    },

    ClipActionCategory.LEDGER_IMPRINT: {
        "STAMP": "Ledger plate stamps one notch deeper",
        "INDEX": "Mechanism indexes forward one unit",
        "ALIGN": "Recording head aligns with next segment",
        "ROTATE": "Data cylinder rotates to new position",
        "CYCLE": "Imprint arm cycles to active state",
        "SHIFT": "Surface geometry shifts incrementally"
    },

    ClipActionCategory.GATE_CLICK:
        "Gate ring clicks from idle to engaged",

    # Defaults for other categories if needed, using generic safe actions
    ClipActionCategory.FILTER_WASH:
        "Light passes through the filtration mesh",
    
    ClipActionCategory.STAIR_STEP:
        "Mechanism advances one step upward",
        
    ClipActionCategory.THROTTLE:
        "Valve mechanism adjusts flow rate",
        
    ClipActionCategory.BREATH:
        "Structure expands and contracts rhythmically",
        
    ClipActionCategory.GENERIC:
        "Component executes standard operation cycle"
}

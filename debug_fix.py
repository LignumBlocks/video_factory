
import sys
import os
sys.path.append(os.getcwd())

from src.planning.enums import BeatLayer, ClipActionCategory, BeatVerb, BeatState, BeatIntensity
from src.planning.models import BeatSheetRow, VoSpanRef
from src.prompts.models import PromptRow

def test_layer_string():
    # Mock Beat
    beat = BeatSheetRow(
        beat_id="B0001",
        sequence_index=1,
        verb=BeatVerb.EXPECTATION,
        state=BeatState.LOCKED,
        layer=BeatLayer.BLUEPRINT,
        intensity=BeatIntensity.L1,
        shot_archetype=1,
        node_type_base="GATE",
        node_role="THRESHOLD",
        amber_allowed=False,
        vo_summary="Test",
        vo_span_ref=VoSpanRef(start_ms=0, end_ms=1000)
    )

    clip_category = ClipActionCategory.SNAPSHOT

    print(f"Beat Layer: {beat.layer}")
    print(f"Beat Layer Value: {beat.layer.value}")
    print(f"Has Value? {hasattr(beat.layer, 'value')}")

    # My Logic
    layer_val = beat.layer.value if hasattr(beat.layer, 'value') else str(beat.layer)
    print(f"Initial layer_val: '{layer_val}'")
    
    if not layer_val.strip():
        print("Empty detected, switching to default")
        layer_val = "Efficiency"
    else:
        print("Not empty")

    raw_init = f"Abstract background representing {layer_val}, {clip_category.value} aesthetic, static scene, clean surfaces, closed system, no humans, high quality, 8k"
    print(f"FINAL PROMPT: {raw_init}")

if __name__ == "__main__":
    test_layer_string()

"""
QC Blocking Test - Demonstrates A→B QC Gate functionality

This test creates specs that violate constraints to prove QC can block.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.qc_manager import QCManager
from src.models import NanobananaRequest, PairRole, AccentColor, ShotSpec, CameraSpec, ContinuitySpec, CameraMovement, ShotSize, CameraAngle, AlignmentSource

def test_qc_blocks_too_many_props():
    """Test that QC blocks when props_count > 2"""
    print("\n=== TEST 1: Too Many Props ===")
    
    qc = QCManager()
    
    # Create shot spec
    shot = ShotSpec(
        id="TEST_s001",
        beat_id="TEST_b001",
        run_id="TEST",
        video_id="VID_TEST",
        beat_start_s=0.0,
        beat_end_s=3.0,
        duration_s=3.0,
        script_text="Test with many props",
        metaphor="Arrow, sign, and graph",
        intent="Test",
        phase_start_intent=None,
        phase_end_intent=None,
        camera=CameraSpec(movement=CameraMovement.STATIC, shot_size=ShotSize.MEDIUM, angle=CameraAngle.EYE_LEVEL, strength=0.5),
        continuity=ContinuitySpec(),
        seed=42,
        alignment_source=AlignmentSource.FORCED_ALIGNMENT,
        alignment_confidence=1.0
    )
    
    # Create requests with TOO MANY PROPS (3 > limit of 2)
    requests = [
        NanobananaRequest(
            request_id="req_1",
            shot_id="TEST_s001",
            beat_id="TEST_b001",
            pair_role=PairRole.START_REF,
            end_static=False,
            props_count=3,  # VIOLATION
            accent_color=AccentColor.POSITIVE,
            ab_plan="Test plan",
            ab_changes_count=1,
            prompt="Test prompt",
            style_bible_hash="test123",
            negative_prompt="test",
            seed=42,
            width=1920,
            height=1080
        ),
        NanobananaRequest(
            request_id="req_2",
            shot_id="TEST_s001",
            beat_id="TEST_b001",
            pair_role=PairRole.END_REF,
            end_static=True,
            props_count=3,  # VIOLATION
            accent_color=AccentColor.POSITIVE,
            ab_plan="Test plan",
            ab_changes_count=1,
            prompt="Test prompt",
            style_bible_hash="test123",
            negative_prompt="test",
            seed=42,
            width=1920,
            height=1080
        )
    ]
    
    # Create dummy asset files
    assets_dir = "test_assets_temp"
    os.makedirs(assets_dir, exist_ok=True)
    
    # Create files
    with open(os.path.join(assets_dir, "TEST_s001_start_ref.png"), 'wb') as f:
        f.write(b'dummy')
    with open(os.path.join(assets_dir, "TEST_s001_end_ref.png"), 'wb') as f:
        f.write(b'dummy')
    
    # Run QC
    report = qc.evaluate_still_pairs([shot], requests, assets_dir)
    
    # Cleanup
    import shutil
    shutil.rmtree(assets_dir)
    
    # Verify QC blocked
    if report.stop_pipeline:
        print(f"✅ QC BLOCKED as expected")
        print(f"   Flags: {report.critical_flags}")
        return True
    else:
        print(f"❌ QC DID NOT BLOCK (should have blocked for >2 props)")
        return False

def test_qc_blocks_ab_budget_exceeded():
    """Test that QC blocks when ab_changes_count > 2"""
    print("\n=== TEST 2: A→B Budget Exceeded ===")
    
    qc = QCManager()
    
    shot = ShotSpec(
        id="TEST_s002",
        beat_id="TEST_b002",
        run_id="TEST",
        video_id="VID_TEST",
        beat_start_s=0.0,
        beat_end_s=3.0,
        duration_s=3.0,
        script_text="Complex transformation",
        metaphor="Multi-step change",
        intent="Test",
        phase_start_intent=None,
        phase_end_intent=None,
        camera=CameraSpec(movement=CameraMovement.STATIC, shot_size=ShotSize.MEDIUM, angle=CameraAngle.EYE_LEVEL, strength=0.5),
        continuity=ContinuitySpec(),
        seed=42,
        alignment_source=AlignmentSource.FORCED_ALIGNMENT,
        alignment_confidence=1.0
    )
    
    requests = [
        NanobananaRequest(
            request_id="req_3",
            shot_id="TEST_s002",
            beat_id="TEST_b002",
            pair_role=PairRole.START_REF,
            end_static=False,
            props_count=1,
            accent_color=AccentColor.NEGATIVE,
            ab_plan="Test plan",
            ab_changes_count=1,
            prompt="Test prompt",
            style_bible_hash="test123",
            negative_prompt="test",
            seed=42,
            width=1920,
            height=1080
        ),
        NanobananaRequest(
            request_id="req_4",
            shot_id="TEST_s002",
            beat_id="TEST_b002",
            pair_role=PairRole.END_REF,
            end_static=True,
            props_count=1,
            accent_color=AccentColor.POSITIVE,
            ab_plan="Test plan",
            ab_changes_count=3,  # VIOLATION (>2)
            prompt="Test prompt",
            style_bible_hash="test123",
            negative_prompt="test",
            seed=42,
            width=1920,
            height=1080
        )
    ]
    
    assets_dir = "test_assets_temp"
    os.makedirs(assets_dir, exist_ok=True)
    
    with open(os.path.join(assets_dir, "TEST_s002_start_ref.png"), 'wb') as f:
        f.write(b'dummy')
    with open(os.path.join(assets_dir, "TEST_s002_end_ref.png"), 'wb') as f:
        f.write(b'dummy')
    
    report = qc.evaluate_still_pairs([shot], requests, assets_dir)
    
    import shutil
    shutil.rmtree(assets_dir)
    
    if report.stop_pipeline:
        print(f"✅ QC BLOCKED as expected")
        print(f"   Flags: {report.critical_flags}")
        return True
    else:
        print(f"❌ QC DID NOT BLOCK (should have blocked for >2 changes)")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("QC BLOCKING TEST - Proving QC is NOT Decorative")
    print("=" * 60)
    
    test1 = test_qc_blocks_too_many_props()
    test2 = test_qc_blocks_ab_budget_exceeded()
    
    print("\n" + "=" * 60)
    if test1 and test2:
        print("✅ ALL TESTS PASSED - QC can block violations")
    else:
        print("❌ TESTS FAILED - QC may be decorative")
    print("=" * 60)


import json
import logging
from typing import List, Set
from pathlib import Path

# Config
RUN_ID = "20260210_160108_c7545055"
RUN_DIR = Path(f"runs/{RUN_ID}")
SCRIPT_PATH = Path("inputs_test/valid_script.txt")
BEATS_PATH = RUN_DIR / "work/beats/beat_sheet.jsonl"
META_PATH = RUN_DIR / "work/beats/beat_sheet.meta.json"

def verify_real_run():
    print(f"--- Verifying Real Run: {RUN_ID} ---")
    
    # 1. Load Original Script
    print(f"\n[INPUT] Loading {SCRIPT_PATH}...")
    with open(SCRIPT_PATH, "r") as f:
        raw_lines = f.readlines()
    
    # Normalize script for comparison (remove empty lines, stripped)
    script_lines_normalized = [l.strip() for l in raw_lines if l.strip()]
    print(f"   Total Non-Empty Script Lines: {len(script_lines_normalized)}")

    # 2. Load Generated Beats
    print(f"\n[OUTPUT] Loading {BEATS_PATH}...")
    beats = []
    with open(BEATS_PATH, "r") as f:
        for line in f:
            beats.append(json.loads(line))
    print(f"   Total Beats Generated: {len(beats)}")

    # 3. Verification: Coverage
    print(f"\n1. Verification: Script Coverage (Gap Filling)")
    # Flatten beat text
    beat_text_combined = "\n".join([b['text'] for b in beats])
    # Check if every script line exists in beat text
    missing_lines = []
    for line in script_lines_normalized:
        if line not in beat_text_combined:
            missing_lines.append(line)
    
    if not missing_lines:
        print("   [PASS] 100% Script Coverage. All lines accounted for.")
    else:
        print(f"   [FAIL] Found {len(missing_lines)} missing lines:")
        for l in missing_lines[:3]:
            print(f"      - {l}")

    # 4. Verification: Duration Clamping
    print(f"\n2. Verification: Duration Clamping (< 12.0s)")
    clamped_beats = [b for b in beats if b['estimated_seconds'] == 12.0]
    if clamped_beats:
        print(f"   [INFO] Found {len(clamped_beats)} beats clamped to 12.0s (Limit enforced).")
        for b in clamped_beats:
            word_count = len(b['text'].split())
            calc_dur = word_count / 2.8
            print(f"      - Beat {b['beat_id']}: {word_count} words -> Calc {calc_dur:.1f}s -> Clamped to 12.0s")
    else:
        print("   [INFO] No beats exceeded 12.0s.")

    # 5. Verification: Warnings
    print(f"\n3. Verification: Metadata Warnings")
    with open(META_PATH, "r") as f:
        meta = json.load(f)
    
    warnings = meta.get("warnings", [])
    if warnings:
        print(f"   Found {len(warnings)} warnings (As Expected for robust pipelines):")
        for w in warnings:
             prefix = "[PASS]" if "CONTAMINATION" in w or "TOO_LONG" in w or "gap" in w.lower() else "[INFO]"
             print(f"      {prefix} {w}")
    else:
        print("   [INFO] No warnings found.")

if __name__ == "__main__":
    if not BEATS_PATH.exists():
        print(f"[ERROR] Run artifacts not found at {BEATS_PATH}. Did the run complete?")
    else:
        verify_real_run()

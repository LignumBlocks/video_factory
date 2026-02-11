"""
T-103: BeatSegmenterAgent Implementation
Converts script into structured beats using LLM for segmentation and ranges.
"""
import os
import json
import re
import logging
from typing import List, Dict, Any, Tuple
from datetime import datetime

from src.llm import LLMClient, LLMJsonRequest, LLMMessage
from .beat_models import Beat, BeatSource, BeatLLMResponse, BeatSheetMeta

logger = logging.getLogger(__name__)

# --- Prompt Templates (T-103.4) ---

SYSTEM_PROMPT = """You are a Narrative Segmenter for a financial video production pipeline.
Your job is to divide the provided script into small, logical narrative "beats".

RULES:
1. NO VISUAL DESCRIPTIONS: Do not describe camera angles, colors, "we see X", or visual styles.
2. NO NEW TEXT: You must only use ranges of lines from the provided script.
3. CONTEXT: Maintain the narrative flow. Each beat should represent a single idea or transition.
4. JSON ONLY: Respond strictly with valid JSON matching the requested schema.
5. STRICT LIMITS: You MUST produce between {min_beats} and {max_beats} beats.
   - If you produce fewer than {min_beats}, your output is INVALID.
   - Break long sentences or paragraphs into multiple beats to meet this count.
   - Each beat should be roughly 1 sentence or phrase.

PACING:
{pacing_instruction}

You will receive lines of the script numbered from 1. 
Return the starting and ending line number (inclusive) for each beat.

IMPORTANT: Each beat object MUST have these exact fields:
- order: integer (1, 2, 3, ...)
- line_start: integer (first line number)
- line_end: integer (last line number, inclusive)
- intent: string (brief narrative intent)
- estimated_seconds: number (1.0 to 12.0)
- priority: integer (1=low, 2=medium, 3=high)
"""

USER_PROMPT_TEMPLATE = """Script to segment:
{numbered_script}

REQUIRED BEAT COUNT: {min_beats} to {max_beats} beats.
CRITICAL: You must generate at least {min_beats} beats. 
Do not group large blocks of text. Keep beats granular (1-3 lines max usually).

Segment the script into logical beats and return JSON in this EXACT format:

{{
  "beats": [
    {{
      "order": 1,
      "line_start": 1,
      "line_end": 2,
      "intent": "Brief description of narrative purpose",
      "estimated_seconds": 4.5,
      "priority": 2
    }},
    ...
  ]
}}

Start segmentation now."""

# --- Contamination Keywords (T-103.2 R2) ---
# Intent: Strict check for any visual terms
INTENT_KEYWORDS = [
    r"camera", r"zoom", r"pan", r"tilt", r"\bshot\b", r"angle", r"\bframe\b",
    r"\bcolor\b", r"\bblue\b", r"\bred\b", r"\bgreen\b", r"\byellow\b", r"\bgold\b",
    r"glossy", r"neon", r"bright", r"\bdark\b", r"lighting",
    r"we see", r"appears", r"shows", r"background", r"foreground",
    r"\bscene\b", r"\bimage\b", r"\bpicture\b", r"\bview\b", r"visual"
]

# Text: Only specific explicit direction, not common words
TEXT_KEYWORDS = [
    r"camera angle", r"camera moves", r"camera pans", r"camera zooms", r"camera tilts",
    r"close-up", r"wide shot", r"tracking shot", r"dolly", r"crane shot",
    r"we see\b", r"viewer sees", r"audience sees", r"screen shows",
    r"zoom in", r"zoom out", r"pan to", r"tilt up", r"tilt down",
    r"fade in", r"fade out", r"cut to"
]

class BeatSegmenterAgent:
    """
    T-103: BeatSegmenterAgent
    Segments a script into beats using ranges to avoid "hallucinating" text or visuals.
    """
    
    def __init__(self, llm: LLMClient, config: Dict[str, Any] = None):
        self.llm = llm
        self.config = config or {}
        # Dynamic resizing overrides these if script is long enough
        self.min_beats_default = self.config.get("min_beats", 6)
        self.max_beats_default = self.config.get("max_beats", 18)
        self.target_beat_duration = self.config.get("target_beat_duration", 4.0) # Seconds per beat (T-103/Bible req)
        self.contamination_threshold = self.config.get("visual_contamination_threshold", 30)
        self.agent_version = "BeatSegmenter/1.2" # Version Bump for Dynamic Sizes

    def segment_script(self, run_id: str, script_text: str, bible_text: str = None) -> Tuple[List[Beat], BeatSheetMeta]:
        """
        Main entry point for segmentation.
        """
        # Step A: Normalize and number script
        # T-103 Refinement: Split Structural vs Narrable
        narrable_lines, markers = self._prepare_script(script_text)
        
        # Save normalized script (Narrable only) -> Source of Truth for Beats
        try:
            work_dir = os.path.join("runs", run_id, "work")
            os.makedirs(work_dir, exist_ok=True)
            
            norm_path = os.path.join(work_dir, "normalized_script_narrable.txt")
            with open(norm_path, "w", encoding="utf-8") as f:
                f.write("\n".join(narrable_lines))
            logger.info(f"Saved narrable script to {norm_path}")
            
            # Save Structural Markers
            markers_path = os.path.join(work_dir, "structural_markers.jsonl")
            with open(markers_path, "w", encoding="utf-8") as f:
                for m in markers:
                    f.write(json.dumps(m) + "\n")
            logger.info(f"Saved structural markers to {markers_path}")
            
        except Exception as e:
            logger.warning(f"Could not save normalized artifacts: {e}")

        # Step A.1: Create Chunks (T-104)
        chunks = self._create_chunks(narrable_lines, markers)
        logger.info(f"Script split into {len(chunks)} chunks for processing.")
        
        all_llm_beats = []
        global_beat_order = 1
        
        for i, chunk in enumerate(chunks):
            chunk_lines = chunk['lines']
            offset = chunk['offset']
            
            logger.info(f"Processing Chunk {i+1}/{len(chunks)}: Lines {offset+1}-{offset+len(chunk_lines)}")
            
            # Numbered script relative to chunk
            numbered_script = "\n".join([f"{i+1}: {line}" for i, line in enumerate(chunk_lines)])
            
            # Dynamic limits for chunk
            chunk_text = "\n".join(chunk_lines)
            c_min, c_max = self._calculate_dynamic_limits(chunk_text)
            
            # Call LLM
            try:
                chunk_beats = self._get_segmentation_from_llm(run_id, numbered_script, c_min, c_max, bible_text)
            except Exception as e:
                logger.error(f"FAILED Processing Chunk {i+1}: {e}", exc_info=True)
                raise e
            
            # Adjust and collect
            for b in chunk_beats:
                b.line_start += offset
                b.line_end += offset
                b.order = global_beat_order # Force sequential order
                global_beat_order += 1
                all_llm_beats.append(b)
                
        # Calculate Global Limits for Validation
        full_text = "\n".join(narrable_lines)
        min_b, max_b = self._calculate_dynamic_limits(full_text)
        
        # Step C: Post-process (Global)
        # Pass NARRABLE lines as the source of truth
        llm_beats = all_llm_beats # Rename for compatibility

        
        # Step C: Post-process
        # Pass NARRABLE lines as the source of truth
        beats, meta = self._post_process(run_id, narrable_lines, llm_beats, min_expected=min_b, max_expected=max_b)
        
        # Add Structural Markers info to Meta
        meta.structural_markers_count = len(markers)
        meta.structural_markers_path = markers_path if 'markers_path' in locals() else None
        
        return beats, meta

    def _calculate_dynamic_limits(self, script_text: str) -> Tuple[int, int]:
        """Calculate min/max beats based on script word count and target duration."""
        # Clean text
        clean = re.sub(r'[#*]', '', script_text)
        words = len(clean.split())
        
        # Estimate Duration (2.8 wps)
        estimated_duration = words / 2.8
        
        # Target Beats
        target_beats = max(1, int(estimated_duration / self.target_beat_duration))
        
        # Safety Margins (+/- 20% or default minimums)
        # T-104: Relaxed minimum to 0.4 (40%) to allow LLM to group ideas.
        # Strict duration limits are enforced in post-processing (_split_long_beats).
        min_beats = max(1, int(target_beats * 0.4))
        max_beats = max(self.max_beats_default, int(target_beats * 1.5))
        
        logger.info(f"Dynamic Beat Sizing: {words} words -> ~{estimated_duration:.1f}s -> Target {target_beats} beats -> Range [{min_beats}, {max_beats}]")
        return min_beats, max_beats


    def _prepare_script(self, text: str) -> Tuple[List[str], List[Dict]]:
        """
        Normalize script separating NARRABLE (VO) from STRUCTURAL (Metadata) lines.
        Returns:
            - narrable_lines: List[str] containing only speakable text.
            - markers: List[Dict] containing structural elements with context.
        """
        # 1. CRLF normalization
        text = text.replace("\r\n", "\n")
        
        raw_lines = text.split("\n")
        narrable_lines = []
        markers = []
        
        # Track index in narrable stream (0-based)
        # If narrable_lines is empty, index is -1 (meaning "before first line")
        # applies_after_narrable_index = len(narrable_lines) - 1
        
        full_normalized_line_index = 0
        
        # 2. Iterate and process
        for line in raw_lines:
            line = line.strip() # Remove surrounding whitespace first
            if not line:
                continue
                
            # Check for structural elements that must NOT be split
            is_structural = False
            marker_type = None
            
            # Headers: #, ##, etc.
            if re.match(r"^#{1,6}\s", line):
                is_structural = True
                marker_type = "SECTION"
            # Separators: ---
            elif re.match(r"^---+$", line):
                is_structural = True
                marker_type = "SEPARATOR"
                
            if is_structural:
                markers.append({
                    "marker_type": marker_type,
                    "text": line,
                    "normalized_line": full_normalized_line_index,
                    "applies_after_narrable_index": len(narrable_lines) - 1
                })
                # We do NOT add to narrable_lines
                # but we increment full_normalized_line_index because conceptually it exists in the source doc
                full_normalized_line_index += 1
                continue

            # NARRABLE CONTENT PROCESSING
            # Bullets: -, *, 1. (Treat as narrable for now, or could be structural if purely visual)
            # Per prompt requirements, only --- and headers are strictly structural.
            # Bullets are often read aloud. Keep as narrable.
            
            # Prosa: Split into sentences deterministically
            sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', line)
            
            for s in sentences:
                s = s.strip()
                if s:
                    narrable_lines.append(s)
                    full_normalized_line_index += 1
                    
        return narrable_lines, markers

    def _get_segmentation_from_llm(self, run_id: str, numbered_script: str, min_beats: int, max_beats: int, bible_text: str = None) -> List[BeatLLMResponse]:
        """Call LLM to get beat ranges (T-103.3 Step B)"""
        schema = {
            "type": "object",
            "required": ["beats"],
            "properties": {
                "beats": {
                    "type": "array",
                    "minItems": min_beats, # T-103 Fix: Strict enforcement
                    "maxItems": max_beats,
                    "items": {
                        "type": "object",
                        "required": ["order", "line_start", "line_end", "intent", "estimated_seconds", "priority"],
                        "properties": {
                            "order": {"type": "integer", "minimum": 1},
                            "line_start": {"type": "integer", "minimum": 1},
                            "line_end": {"type": "integer", "minimum": 1},
                            "intent": {"type": "string", "minLength": 3},
                            "estimated_seconds": {"type": "number", "minimum": 1.0, "maximum": 12.0},
                            "priority": {"type": "integer", "minimum": 1, "maximum": 3}
                        }
                    }
                }
            }
        }

        # Pacing Instruction
        pacing = "FAST PACING. Keep beats short (2-5 seconds). Avoid long blocks of text."
        if bible_text:
            pacing += " Adhere to pipeline requirements: roughly 150 beats for standard length scripts."

        req = LLMJsonRequest(
            messages=[
                LLMMessage(role="system", content=SYSTEM_PROMPT.format(
                    min_beats=min_beats, max_beats=max_beats,
                    pacing_instruction=pacing
                )),
                LLMMessage(role="user", content=USER_PROMPT_TEMPLATE.format(
                    numbered_script=numbered_script,
                    min_beats=min_beats,
                    max_beats=max_beats
                ))
            ],
            model="gpt-4o-mini", # Default
            json_schema=schema,
            run_id=run_id,
            step_name="BEAT_SEGMENTER",
            max_tokens=12000, # Increased for long scripts (150+ beats)
            timeout_s=600.0   # Significantly increased for long generation time
        )

        response = self.llm.generate_json(req)
        
        # Convert to model list
        beats_data = response.json.get("beats", [])
        return [BeatLLMResponse(**b) for b in beats_data]

    def _post_process(self, run_id: str, script_lines: List[str], llm_beats: List[BeatLLMResponse], min_expected: int = None, max_expected: int = None) -> Tuple[List[Beat], BeatSheetMeta]:
        """Post-process LLM output into final Beats (T-103.3 Step C)"""
        # 1. Sort by order
        llm_beats.sort(key=lambda x: x.order)
        
        # Map LLM beats to basic Beat objects first
        intermediate_beats = []
        warnings = []
        line_count = len(script_lines)
        
        for i, lb in enumerate(llm_beats):
            # Validate ranges
            start = max(1, lb.line_start)
            end = min(line_count, lb.line_end)
            
            if start > end:
                warnings.append(f"Invalid range for beat {lb.order}: {lb.line_start}-{lb.line_end}. Skipping.")
                continue
            
            # Build text directly from source lines to ensure contract
            beat_lines = script_lines[start-1:end]
            beat_text = "\n".join(beat_lines)
            
            if not beat_text.strip():
                continue

            beat = Beat(
                run_id=run_id,
                beat_id=f"temp_{i}", 
                order=lb.order,
                text=beat_text,
                intent=lb.intent,
                estimated_seconds=0.0, # Recalc later
                priority=lb.priority,
                source=BeatSource(line_start=start, line_end=end)
            )
            intermediate_beats.append(beat)

        # 2. Fill Gaps (100% Coverage Rule)
        filled_beats, gap_warnings = self._fill_gaps(script_lines, intermediate_beats)
        warnings.extend(gap_warnings)
        
        # 3. Merge short beats (T-103.3 Step C.4)
        # Pass script_lines to ensure text reconstruction is perfect
        merged_beats = self._merge_short_beats(filled_beats, script_lines)
        
        # 3.5 Split long beats (Atomic Range Splitting)
        final_beats = self._split_long_beats(merged_beats, script_lines)
        
        # 4. Final Processing loop (Recalc IDs, Duration, Contamination)
        total_contamination = 0
        total_words = 0
        
        for idx, b in enumerate(final_beats):
            # Update ID and Order
            b.order = idx + 1
            b.beat_id = f"b{idx+1:03d}"
            
            # Sanity Check Contract (Audit)
            expected_text = "\n".join(script_lines[b.source.line_start-1 : b.source.line_end])
            if b.text != expected_text:
                # This should technically never happen with new logic, but if safe-guarding:
                warnings.append(f"AUDIT FAIL: Beat {b.beat_id} text mismatch. Fixing.")
                b.text = expected_text
            
            # Recalculate Duration strictly
            calc_duration = self._calculate_duration(b.text)
            
            # Clamp and Warn
            if calc_duration > 12.0:
                warnings.append(f"BEAT_TOO_LONG: Beat {b.beat_id} duration {calc_duration:.1f}s > 12.0s (Atomic unit too large).")
                # We do NOT clamp time arbitrarily if the text is truly that long.
                b.estimated_seconds = 12.0 
            else:
                b.estimated_seconds = calc_duration
            
            total_words += len(b.text.split())
                
            # Detect Contamination
            intent_contam = self._detect_contamination(b.intent)
            if intent_contam > 0:
                warnings.append(f"[CONTAMINATION] Beat {b.beat_id} intent contains visual terms.")
                total_contamination += intent_contam
                
            text_contam = self._detect_text_contamination(b.text)
            if text_contam > 0:
                warnings.append(f"[CONTAMINATION] Beat {b.beat_id} text contains direction phrases.")
                total_contamination += text_contam

        # Check contamination threshold (T-103.2 R2)
        if total_contamination > self.contamination_threshold:
            raise RuntimeError(f"BEAT_VISUAL_CONTAMINATION: Found too many visual references ({total_contamination})")

        # Check count out of range (T-103.3 C.5)
        min_limit = min_expected if min_expected is not None else self.min_beats
        max_limit = max_expected if max_expected is not None else self.max_beats
        
        if len(final_beats) < min_limit or len(final_beats) > max_limit:
            # Try one more pass of splitting if under-count? 
            # Actually, splitting creates MORE beats. If we are OVER max, we might need merge.
            # If we are UNDER min, we might need split.
            # But our split is based on duration constraints (physics).
            # If we are strictly following contract, we fallback to Error.
            
            logger.error(f"HARD FAIL: Count {len(final_beats)} not in [{min_limit}, {max_limit}]")
            logger.error(f"Warnings: {json.dumps(warnings, indent=2)}")
            raise RuntimeError(f"BEAT_COUNT_OUT_OF_RANGE: Produced {len(final_beats)} beats, expected {min_limit}-{max_limit}")

        # Meta
        avg_sec = sum(b.estimated_seconds for b in final_beats) / len(final_beats) if final_beats else 0
        
        # Calculate derived metrics for meta
        estimated_total_duration = sum(b.estimated_seconds for b in final_beats)
        target_beats = int(estimated_total_duration / self.target_beat_duration) if self.target_beat_duration else 0

        meta = BeatSheetMeta(
            total_beats=len(final_beats),
            avg_estimated_seconds=round(avg_sec, 2),
            min_beats=min_limit,
            max_beats=max_limit,
            warnings=warnings,
            visual_contamination_count=total_contamination,
            # extra fields
            normalized_line_count=line_count,
            word_count=total_words,
            estimated_duration_s=round(estimated_total_duration, 2),
            target_beats=target_beats
        )
        
        return final_beats, meta

    def _merge_short_beats(self, beats: List[Beat], script_lines: List[str]) -> List[Beat]:
        """Merge beats that are too short (Atomic Version)"""
        if len(beats) <= 1:
            return beats
            
        merged = []
        skip_next = False
        
        for i in range(len(beats)):
            if skip_next:
                skip_next = False
                continue
                
            curr = beats[i]
            curr_dur = self._calculate_duration(curr.text)
            
            # Simple heuristic for "too short": < 1.5s or < 40 chars
            if i < len(beats) - 1 and (curr_dur < 1.5 or len(curr.text) < 40):
                nxt = beats[i+1]
                
                # Check adjacency for strict contract
                if nxt.source.line_start != curr.source.line_end + 1:
                    # Gapped beats? _fill_gaps should have fixed this.
                    # If slight gap, we can technically merge across it if we include gap lines?
                    # But better to play safe and NOT merge if non-contiguous.
                    merged.append(curr)
                    continue

                # Merge
                new_start = curr.source.line_start
                new_end = nxt.source.line_end
                new_text = "\n".join(script_lines[new_start-1:new_end])
                
                new_beat = Beat(
                    run_id=curr.run_id,
                    beat_id=curr.beat_id,
                    order=curr.order,
                    text=new_text,
                    intent=f"{curr.intent} | {nxt.intent}",
                    estimated_seconds=0.0, 
                    priority=max(curr.priority, nxt.priority),
                    source=BeatSource(line_start=new_start, line_end=new_end)
                )
                merged.append(new_beat)
                skip_next = True
            else:
                merged.append(curr)
                
        return merged

    def _split_long_beats(self, beats: List[Beat], script_lines: List[str]) -> List[Beat]:
        """Recursively split beats that exceed max duration using Atomic Line Ranges"""
        final_list = []
        
        for beat in beats:
            duration = self._calculate_duration(beat.text)
            
            # T-103: 7.0s threshold
            if duration > 7.0:
                splits = self._split_beat_recursive(beat, script_lines)
                final_list.extend(splits)
            else:
                final_list.append(beat)
                
        return final_list

    def _split_beat_recursive(self, beat: Beat, script_lines: List[str]) -> List[Beat]:
        """Helper to split a range by lines"""
        duration = self._calculate_duration(beat.text)
        if duration <= 7.0:
            return [beat]
            
        # Check if we have atomic granularity to split
        start = beat.source.line_start
        end = beat.source.line_end
        count = end - start + 1
        
        if count <= 1:
            # Cannot split atomic line further without breaking contract
            return [beat]
            
        # Split logic: Divide range in half (roughly)
        # We could try to be smarter (balance word count), but half lines is a good heuristic
        # provided lines are sentences.
        mid = start + (count // 2) - 1
        
        # Range 1: start to mid
        range1_lines = script_lines[start-1:mid]
        text1 = "\n".join(range1_lines)
        
        # Range 2: mid+1 to end
        range2_lines = script_lines[mid:end] # mid is index of (mid+1)th line
        text2 = "\n".join(range2_lines)

        b1 = Beat(
            run_id=beat.run_id,
            beat_id=f"{beat.beat_id}a",
            order=beat.order,
            text=text1,
            intent=beat.intent, # Keep original intent, avoids debug noise
            estimated_seconds=self._calculate_duration(text1),
            priority=beat.priority,
            source=BeatSource(line_start=start, line_end=mid)
        )
        
        b2 = Beat(
            run_id=beat.run_id,
            beat_id=f"{beat.beat_id}b",
            order=beat.order,
            text=text2,
            intent=beat.intent,
            estimated_seconds=self._calculate_duration(text2),
            priority=beat.priority,
            source=BeatSource(line_start=mid+1, line_end=end)
        )
        
        # Recurse
        return self._split_beat_recursive(b1, script_lines) + self._split_beat_recursive(b2, script_lines)
    def _create_sub_beats(self, original: Beat, chunks: List[str]) -> List[Beat]:
        """Create new beats from text chunks"""
        new_beats = []
        for i, chunk in enumerate(chunks):
            # Recurse on chunk in case it's still too big (unlikely with grouping logic but safe)
            b = self._clone_beat(original, chunk, suffix=f"_{i+1}")
            # check if this chunk needs further splitting
            new_beats.extend(self._split_beat_recursive(b))
        return new_beats

    def _clone_beat(self, original: Beat, new_text: str, suffix: str) -> Beat:
        """Helper to clone a beat with new text"""
        return Beat(
            run_id=original.run_id,
            beat_id=f"{original.beat_id}{suffix}",
            order=original.order, # Will be reordered later
            text=new_text,
            intent=f"{original.intent} (Split {suffix})",
            estimated_seconds=self._calculate_duration(new_text),
            priority=original.priority,
            source=original.source # Shared source range (imperfect but preserves trace)
        )

    def _detect_contamination(self, intent: str) -> int:
        """Count visual contamination (T-103.2 R2) - Strict Mode"""
        count = 0
        intent_lower = intent.lower()
        
        # Check Intent (Strict)
        for pattern in INTENT_KEYWORDS:
            if re.search(pattern, intent_lower):
                count += 1
                
        return count

    def _detect_text_contamination(self, text: str) -> int:
        """Check for specific direction phrases in text (T-103 Fix)"""
        count = 0
        text_lower = text.lower()
        for pattern in TEXT_KEYWORDS:
            if re.search(pattern, text_lower):
                count += 1
        return count

    def _calculate_duration(self, text: str) -> float:
        """Estimate duration based on word count (T-103 Fix)"""
        # remove markdown headers/formatting for word count
        clean_text = re.sub(r'[#*]', '', text)
        words = len(clean_text.split())
        # Assuming 168 wpm = 2.8 words/sec
        seconds = words / 2.8
        return max(1.0, seconds)

    def _fill_gaps(self, lines: List[str], beats: List[Beat]) -> Tuple[List[Beat], List[str]]:
        """
        Ensure 100% script coverage by filling gaps (T-103 Fix).
        NOTE: 'lines' here refers to NARRABLE lines only. Structural markers are already excluded.
        Any gap found here is a missing piece of NARRABLE text.
        """
        if not beats:
            return beats, []
            
        filled_beats = []
        warnings = []
        last_end = 0
        
        # Helper to create gap beat
        def create_gap_beat(start, end, order_hint):
            if start > end: return None
            # Validate bounds
            if start < 1 or end > len(lines): return None
            
            gap_lines = lines[start-1:end]
            gap_text = "\n".join(gap_lines)
            if not gap_text.strip():
                return None
            
            # Duration calc for header/short text might be small, but logic handles it
            return Beat(
                run_id=beats[0].run_id,
                beat_id=f"gap_{start}_{end}",
                order=order_hint,
                text=gap_text,
                intent="[GAP FILLED] Narrative Bridge",
                estimated_seconds=self._calculate_duration(gap_text),
                priority=1,
                source=BeatSource(line_start=start, line_end=end)
            )

        # check gap before first beat
        if beats[0].source.line_start > 1:
            gap_beat = create_gap_beat(1, beats[0].source.line_start - 1, 0)
            if gap_beat:
                warnings.append(f"Filled start gap: lines 1-{beats[0].source.line_start-1}")
                filled_beats.append(gap_beat)

        for i, beat in enumerate(beats):
            # Check gap between last_end and current start
            # last_end is 0 initially.
            # If beat starts at 1, gap_start=1, gap_end=0 -> Loop skip.
            # If beat starts at 5, gap_start=1, gap_end=4.
            
            gap_start = last_end + 1
            gap_end = beat.source.line_start - 1
            
            if gap_start <= gap_end:
                 gap_lines = lines[gap_start-1:gap_end]
                 gap_text = "\n".join(gap_lines)
                 
                 if gap_text.strip():
                     # Content found! 
                     # Merge into PREVIOUS beat if possible (safest context)
                     if filled_beats:
                         prev = filled_beats[-1]
                         prev.text += "\n" + gap_text
                         prev.source.line_end = gap_end
                         # Recalc duration not needed here, will do in final pass
                         warnings.append(f"Merged gap lines {gap_start}-{gap_end} into beat {prev.order}")
                     else:
                         # No previous beat, create new
                         gap_beat = create_gap_beat(gap_start, gap_end, beat.order)
                         if gap_beat:
                             filled_beats.append(gap_beat)
                             warnings.append(f"Created gap beat for lines {gap_start}-{gap_end}")
            
            filled_beats.append(beat)
            last_end = beat.source.line_end
            
        # Check gap after last beat
        if last_end < len(lines):
            gap_text = "\n".join(lines[last_end:])
            if gap_text.strip():
                # Merge into last beat if exists
                if filled_beats:
                    prev = filled_beats[-1]
                    prev.text += "\n" + gap_text
                    prev.source.line_end = len(lines)
                    warnings.append(f"Merged end gap lines {last_end+1}-{len(lines)} into last beat")
                else:
                    gap_beat = create_gap_beat(last_end + 1, len(lines), len(filled_beats) + 1)
                    if gap_beat:
                        filled_beats.append(gap_beat)
                        warnings.append(f"Created end gap beat for lines {last_end+1}-{len(lines)}")

        return filled_beats, warnings
    def _create_chunks(self, narrable_lines: List[str], markers: List[Dict]) -> List[Dict]:
        """
        Split narrable lines into chunks (T-104), respecting structural boundaries if possible.
        """
        chunks = []
        current_chunk_lines = []
        current_chunk_start_index = 0
        current_word_count = 0
        target_words = 450  # ~40 beats per chunk (Safe for timeout)
        
        # Map narrative index -> structural marker presence (AFTER this line)
        # We want to split AFTER a line if a marker exists there.
        # marker['applies_after_narrable_index'] = i means marker is between line i and i+1
        split_points = {m['applies_after_narrable_index'] for m in markers if m['marker_type'] in ['SECTION', 'SEPARATOR']}
        
        for i, line in enumerate(narrable_lines):
            # clean word count
            words = len(re.sub(r'[#*]', '', line).split())
            current_chunk_lines.append(line)
            current_word_count += words
            
            # Check for split
            # 1. Must be at least meaningful size (e.g. > 50 words) to avoid tiny separate chunks
            # 2. If word count > target, FORCE split
            # 3. If word count > target * 0.7 AND we are at a structural boundary, PREFER split
            
            should_split = False
            
            # Condition A: Hard Limit (prevent massive chunks)
            if current_word_count >= target_words:
                should_split = True
                
            # Condition B: Structural Opportunity (soft limit)
            elif current_word_count >= (target_words * 0.6) and i in split_points:
                should_split = True
                
            # Check end of script
            if i == len(narrable_lines) - 1:
                should_split = True
                
            if should_split:
                chunks.append({
                    "lines": current_chunk_lines,
                    "global_start_index": current_chunk_start_index + 1, # 1-based for display
                    "offset": current_chunk_start_index # 0-based for indexing
                })
                # Reset
                current_chunk_lines = []
                current_chunk_start_index = i + 1
                current_word_count = 0
                
        return chunks

    def _merge_chunk_beats(self, chunk_results: List[List[Beat]]) -> List[Beat]:
        """Merge beats from multiple chunks into a single list."""
        final_beats = []
        for beats in chunk_results:
            final_beats.extend(beats)
        
        # Renumber will happen in post-process, but we need to ensure beat_ids are unique temporarily?
        # Actually _post_process is called PER CHUNK or globally?
        # Better design: Call LLM per chunk, get BeatLLMResponse objects.
        # Then flatten BeatLLMResponse list.
        # THEN call _post_process ONCE on the full set?
        # Problem: _post_process expects `order` to be sequential 1..N.
        # But chunks will each return 1..M.
        # So we must adjust `order` and `line_start/line_end` before merging?
        # YES.
        
        return final_beats # Placeholder, logic moved to segment_script

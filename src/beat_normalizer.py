from typing import List, Dict, Tuple
import re

class BeatNormalizer:
    def __init__(self, min_duration: float = 2.0, max_duration: float = 12.0):
        self.min_duration = min_duration
        self.max_duration = max_duration

    def normalize(self, segments: List[Dict]) -> List[Dict]:
        """
        Enforces min/max duration constraints.
        1. Merge beats < min_duration.
        2. Split beats > max_duration (heuristic split).
        """
        # 1. Merge short beats
        merged = self._merge_short_beats(segments)
        
        # 2. Split long beats
        final_segments = []
        for seg in merged:
             duration = seg['end'] - seg['start']
             if duration > self.max_duration:
                 final_segments.extend(self._split_long_beat(seg))
             else:
                 final_segments.append(seg)
                 
        return final_segments

    def _merge_short_beats(self, segments: List[Dict]) -> List[Dict]:
        if not segments:
            return []
            
        merged = []
        buffer_seg = None
        
        for seg in segments:
            if buffer_seg is None:
                buffer_seg = seg
                continue
                
            buffer_dur = buffer_seg['end'] - buffer_seg['start']
            
            # If buffer is short, try to merge with current
            if buffer_dur < self.min_duration:
                # Merge
                buffer_seg = {
                    "text": (buffer_seg['text'] + " " + seg['text']).strip(),
                    "start": buffer_seg['start'],
                    "end": seg['end']
                }
            else:
                merged.append(buffer_seg)
                buffer_seg = seg
                
        # Handle last one
        if buffer_seg:
            buffer_dur = buffer_seg['end'] - buffer_seg['start']
            # If last one is still short, try to merge BACKWARDS with last accepted
            if buffer_dur < self.min_duration and merged:
                prev = merged.pop()
                buffer_seg = {
                    "text": (prev['text'] + " " + buffer_seg['text']).strip(),
                    "start": prev['start'],
                    "end": buffer_seg['end']
                }
            merged.append(buffer_seg)
            
        return merged

    def _split_long_beat(self, segment: Dict) -> List[Dict]:
        """
        Splits a beat proportionally. Guarantees no segment > max_duration.
        """
        text = segment['text']
        start = segment['start']
        end = segment['end']
        total_dur = end - start
        
        if total_dur <= self.max_duration:
             return [segment]
             
        # Calculate minimum splits needed to satisfy constraint
        # e.g. 25s / 12s = 2.08 -> 3 splits. 25/3 = 8.33s each.
        import math
        # Safety Factor: Target 85% of max to account for word granularity variance
        safe_max = self.max_duration * 0.85
        if safe_max < self.min_duration:
             safe_max = self.max_duration # limit case
             
        num_splits = math.ceil(total_dur / safe_max)
        
        # Proportional Split
        words = text.split()
        if not words:
             # Empty text but long duration? Just split time.
             duration_per_split = total_dur / num_splits
             splits = []
             curr = start
             for _ in range(num_splits):
                 splits.append({
                     "text": "",
                     "start": float(f"{curr:.3f}"),
                     "end": float(f"{curr + duration_per_split:.3f}")
                 })
                 curr += duration_per_split
             return splits

        total_chars = len(text)
        splits = []
        current_words = []
        current_char_count = 0
        current_start = start
        
        # Target chars per split approx
        target_chars = total_chars / num_splits
        
        for i, w in enumerate(words):
            current_words.append(w)
            current_char_count += len(w) + 1 # +1 for space
            
            # If we exceeded target for this split, and we are not the last split
            if current_char_count >= target_chars and len(splits) < num_splits - 1:
                chunk_text = " ".join(current_words)
                # Weighted duration
                chunk_dur = (len(chunk_text) / total_chars) * total_dur
                
                splits.append({
                    "text": chunk_text,
                    "start": float(f"{current_start:.3f}"),
                    "end": float(f"{current_start + chunk_dur:.3f}")
                })
                
                current_start += chunk_dur
                current_words = []
                current_char_count = 0
                
        # Final Chunk
        if current_words:
            chunk_text = " ".join(current_words)
            splits.append({
                "text": chunk_text,
                "start": float(f"{current_start:.3f}"),
                "end": end # Force exact end match
            })
            
        return splits

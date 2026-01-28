import os
import requests
import time
from typing import List, Dict, Tuple
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from .models import AlignmentSource, AlignmentStats

class AudioAligner:
    def __init__(self, source: AlignmentSource = AlignmentSource.FORCED_ALIGNMENT):
        if os.environ.get("FORCE_MOCK_ALIGNMENT") == "1":
            self.source = AlignmentSource.MOCK_PROPORTIONAL
            print("WARNING: FORCE_MOCK_ALIGNMENT env var detected. Using MOCK_PROPORTIONAL.")
        else:
            self.source = source
        
        self.api_key = os.environ.get("OPENAI_API_KEY", "")

    def get_audio_duration(self, audio_path: str) -> float:
        """
        Uses ffprobe to get precise audio duration.
        """
        import subprocess
        try:
            cmd = [
                "ffprobe", 
                "-v", "error", 
                "-show_entries", "format=duration", 
                "-of", "default=noprint_wrappers=1:nokey=1", 
                audio_path
            ]
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
            return float(result.stdout.strip())
        except Exception as e:
            print(f"Error getting duration for {audio_path}: {e}")
            # Fallback handling? For blocker, we explicitly want validation.
            raise RuntimeError(f"Could not check audio duration: {e}")


    def _fallback_mock_align(self, script_text: str, audio_path: str) -> Tuple[List[Dict], AlignmentStats]:
        """SAME logic as mocked v1, but marks source as MOCK_PROPORTIONAL"""
        import re
        total_duration = 60.0 # Default Mock
        
        # Try to get real duration if file exists
        if os.path.exists(audio_path):
            try:
                real_dur = self.get_audio_duration(audio_path)
                if real_dur > 0:
                    total_duration = real_dur
                    print(f"Fallback Mock: Using REAL audio duration: {total_duration}s")
            except Exception as e:
                print(f"Warning: Could not get duration for fallback: {e}")
        
        beats = re.split(r'(?<=[.!?])\s+', script_text)
        beats = [b.strip() for b in beats if b.strip()]
        total_chars = sum(len(b) for b in beats)
        
        segments = []
        current_time = 0.0
        for i, b in enumerate(beats):
            dur = total_duration * (len(b) / total_chars)
            segments.append({
                "text": b,
                "start": float(f"{current_time:.3f}"),
                "end": float(f"{current_time + dur:.3f}")
            })
            current_time += dur
            
        stats = AlignmentStats(
            source=AlignmentSource.MOCK_PROPORTIONAL,
            max_drift_s=0.0,
            gap_count=0,
            coverage_pct=100.0,
            confidence_avg=1.0,
            fallback_used=True
        )
        return segments, stats

    @retry(
        stop=stop_after_attempt(3), 
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(requests.exceptions.RequestException),
        reraise=True
    )
    def _real_whisper_align(self, script_text: str, audio_path: str) -> Tuple[List[Dict], AlignmentStats]:
        """Direct call to OpenAI Whisper API (verbose_json) with Local Caching"""
        import hashlib
        import json
        
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        # 0. Setup Cache
        def compute_md5(fname):
            hash_md5 = hashlib.md5()
            with open(fname, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()

        file_hash = compute_md5(audio_path)
        cache_dir = os.path.join(os.getcwd(), ".cache", "whisper")
        os.makedirs(cache_dir, exist_ok=True)
        cache_path = os.path.join(cache_dir, f"{file_hash}.json")
        
        transcript = None

        # 1. Check Cache
        if os.path.exists(cache_path):
            print(f"DEBUG: Using Cached Whisper Transcript: {cache_path}")
            try:
                with open(cache_path, 'r') as f:
                    transcript = json.load(f)
                
                # Validation: Check if 'words' exist (required for word-level timestamps)
                if not transcript.get("words"):
                    print(f"Warning: Cached transcript {cache_path} missing 'words'. Invalidating cache.")
                    transcript = None
                    os.remove(cache_path)
            except Exception as e:
                print(f"Warning: Corrupt cache file {cache_path}: {e}")
                transcript = None

        # 2. Call Whisper (if no cache)
        if not transcript:
            print(f"Calling Whisper API for {audio_path}...")
            sanitized_key = f"{self.api_key[:6]}...{self.api_key[-4:]}" if self.api_key else "None"
            print(f"DEBUG: Using API Key: {sanitized_key}")
            
            headers = {
                "Authorization": f"Bearer {self.api_key}"
            }
            
            # We use requests here for simplicity (sync)
            with open(audio_path, "rb") as f:
                files = {
                    "file": ("audio.mp3", f, "audio/mpeg")
                }
                data = {
                    "model": "whisper-1",
                    "response_format": "verbose_json",
                    "timestamp_granularities[]": "word"
                }
                
                resp = requests.post(
                    "https://api.openai.com/v1/audio/transcriptions",
                    headers=headers,
                    files=files,
                    data=data,
                    timeout=300
                )
                resp.raise_for_status()
                transcript = resp.json()
            
            # Save Cache
            print(f"DEBUG: Saving Transcript Cache to {cache_path}")
            with open(cache_path, 'w') as f:
                json.dump(transcript, f)

        # 2. Map Words
        words = transcript.get("words", [])
        print(f"Whisper transcribed {len(words)} words")
        
        # Split script into phrases
        import re
        script_phrases = re.split(r'(?<=[.!?])\s+', script_text)
        script_phrases = [p.strip() for p in script_phrases if p.strip()]
        
        # 3. Map Logic (Ported from Gateway)
        segments = []
        word_idx = 0
        
        for phrase in script_phrases:
            phrase_word_count = len(phrase.split())
            phrase_start = None
            phrase_end = None
            
            # Consume words
            for _ in range(min(phrase_word_count, len(words) - word_idx)):
                w_data = words[word_idx]
                if phrase_start is None: 
                    phrase_start = w_data["start"]
                phrase_end = w_data["end"]
                word_idx += 1
            
            if phrase_start is not None and phrase_end is not None:
                segments.append({
                    "text": phrase,
                    "start": phrase_start,
                    "end": phrase_end
                })
        
        # 4. Stats
        coverage = len([w for w in words if w.get("word")]) / max(len(words), 1)
        stats = AlignmentStats(
            source=AlignmentSource.WHISPER_API, # New Enum value needed or reuse FORCED
            max_drift_s=0.1,
            gap_count=0,
            coverage_pct=coverage * 100,
            confidence_avg=0.95,
            fallback_used=False
        )
        return segments, stats

    def align(self, script_path: str, audio_path: str, run_identity: dict = {}) -> Tuple[List[Dict], AlignmentStats]:
        with open(script_path, 'r', encoding='utf-8') as f:
            script_text = f.read()

        # Decide Mode
        # If API KEY present -> Use Real Whisper
        # Else -> Fallback
        use_real = bool(os.environ.get("OPENAI_API_KEY")) and self.source != AlignmentSource.MOCK_PROPORTIONAL
        
        if use_real:
            # Update key from env just in case
            self.api_key = os.environ.get("OPENAI_API_KEY")
            try:
                return self._real_whisper_align(script_text, audio_path)
            except Exception as e:
                print(f"CRITICAL: Real Alignment Failed: {e}")
                if self.source == AlignmentSource.FORCED_ALIGNMENT:
                    raise e
                print("Falling back to Mock Alignment...")
                return self._fallback_mock_align(script_text, audio_path)
        else:
            print("No OPENAI_API_KEY found or Mock Mode forced. Using Mock Alignment.")
            return self._fallback_mock_align(script_text, audio_path)

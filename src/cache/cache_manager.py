import hashlib
import json
from typing import Any, Dict, Optional

class CacheManager:
    """
    Manages computation of consistency hashes (cache keys) for assets.
    Does NOT handle DB storage directly (managed by DatabaseManager),
    but provides the logic to generate determining keys.
    """
    
    @staticmethod
    def compute_key(data: Dict[str, Any], prefix: str = "") -> str:
        """
        Generates a deterministic SHA256 hash from a dictionary of inputs.
        
        Args:
            data: Dictionary of input parameters (e.g., {"prompt": "...", "seed": 123}).
            prefix: Optional prefix for the key (e.g., "IMG", "VID").
            
        Returns:
            SHA256 hex string.
        """
        # Sort keys to ensure determinism
        canonical_json = json.dumps(data, sort_keys=True, separators=(',', ':'))
        hash_digest = hashlib.sha256(canonical_json.encode('utf-8')).hexdigest()
        
        if prefix:
            return f"{prefix}_{hash_digest}"
        return hash_digest

    @staticmethod
    def compute_image_key(prompt: str, negative_prompt: str, model_config: Dict[str, Any]) -> str:
        """
        Helper for Image Generation keys.
        """
        payload = {
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "config": model_config
        }
        return CacheManager.compute_key(payload, prefix="IMG")

    @staticmethod
    def compute_video_key(image_asset_id: str, prompt: str, model_config: Dict[str, Any]) -> str:
        """
        Helper for Video Generation keys (depends on source image).
        """
        payload = {
            "source_image_id": image_asset_id, # If source image changes, video must change
            "prompt": prompt,
            "config": model_config
        }
        return CacheManager.compute_key(payload, prefix="VID")

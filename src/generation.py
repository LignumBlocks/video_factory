import os
import shutil
import time
import json
from typing import List, Dict, Optional, Tuple
from .models import NanobananaRequest, ImageRole, GenerationMode, VeoRequest, PairRole
from .clients.nanobanana import NanobananaClient
from .clients.veo import VeoClient

class ImageGenerator:
    def __init__(self, output_dir: str):
        self.output_dir = output_dir
        self.assets_dir = os.path.join(output_dir, "assets")
        os.makedirs(self.assets_dir, exist_ok=True)
        self.client = NanobananaClient()

    def generate_images(self, requests: List[NanobananaRequest], mode: GenerationMode) -> List[str]:
        """
        Executes generation for a batch of image requests.
        Enforces A->B Img2Img binding if ALIGNMENT_MODE == CLEAN_SCORE.
        Returns: List of new file paths.
        """
        if mode == GenerationMode.SIMULATION:
            return self._generate_placeholders(requests)
        elif mode != GenerationMode.REAL:
            raise ValueError(f"Unsupported generation mode: {mode}")

        # --- REAL GENERATION ---
        new_files = []
        
        # Group by Shot ID to handle Pairs
        from collections import defaultdict
        shot_map = defaultdict(dict)
        for req in requests:
            role = req.pair_role or PairRole.START_REF
            shot_map[req.shot_id][role] = req
            
        print(f"Generating Images for {len(shot_map)} shots [Mode: {mode.value}]...")
        
        sorted_shots = sorted(shot_map.keys())
        
        url_map_path = os.path.join(self.output_dir, "image_urls.json")
        url_map = {}
        if os.path.exists(url_map_path):
             with open(url_map_path, 'r') as f:
                 url_map = json.load(f)

        for shot_id in sorted_shots:
            roles = shot_map[shot_id]
            start_req = roles.get(PairRole.START_REF) # Correct enum usage
            end_req = roles.get(PairRole.END_REF)
            
            # 1. Generate START (A)
            start_path = None
            start_url = None
            if start_req:
                start_path, start_url = self._generate_single(self.client, start_req)
                if start_path:
                     new_files.append(start_path)
                     start_filename = os.path.basename(start_path)
                     if start_url:
                         url_map[start_filename] = start_url

            # 2. Generate END (B)
            if end_req:
                # BINDING LOGIC (Clean Score Jump)
                # Puede deshabilitarse con DISABLE_IMG2IMG=1 para pruebas comparativas
                disable_binding = os.environ.get("DISABLE_IMG2IMG") == "1"
                
                if os.environ.get("ALIGNMENT_MODE") == "CLEAN_SCORE" and start_url and not disable_binding:
                     print(f"Binding A->B for {shot_id}: Using URL {start_url} as init_image")
                     end_req.image_input_path = start_url
                     # Potentially adjust strength if needed, or stick to model default
                elif disable_binding:
                     print(f"⚠️  BINDING DISABLED for {shot_id} (DISABLE_IMG2IMG=1)")
                
                # Check if we have end_url in map (if skipped)
                # But here we are generating...
                end_path, end_url = self._generate_single(self.client, end_req)
                if end_path:
                     new_files.append(end_path)
                     if end_url:
                          url_map[os.path.basename(end_path)] = end_url

        # Save URL Map
        with open(url_map_path, 'w') as f:
            json.dump(url_map, f, indent=2)

        return new_files

    def _generate_single(self, client: NanobananaClient, req: NanobananaRequest) -> Tuple[Optional[str], Optional[str]]:
        role_suffix = req.pair_role.value if req.pair_role else "ref"
        filename = f"{req.shot_id}_{role_suffix}.png"
        out_path = os.path.join(self.assets_dir, filename)
        
        if os.path.exists(out_path):
            print(f"Skipping {filename} (Exists)")
            return out_path, None
            
        print(f"Generating {filename}...")
        try:
            # Call Client
            img_bytes, img_url = client.generate_image(req)
            
            with open(out_path, "wb") as f:
                f.write(img_bytes)
            
            return out_path, img_url
        except Exception as e:
            print(f"FAILED to generate {filename}: {e}")
            raise e
        return None, None

class ClipGenerator:
    def __init__(self, output_dir: str):
        self.output_dir = output_dir
        self.assets_dir = os.path.join(output_dir, "assets")
        os.makedirs(self.assets_dir, exist_ok=True)
        self.client = VeoClient()

    def generate_clips(self, requests: List[VeoRequest], mode: GenerationMode) -> List[str]:
        if mode == GenerationMode.SIMULATION:
            return self._generate_placeholders(requests)
        elif mode == GenerationMode.REAL:
            return self._generate_real(requests)
        else:
            raise ValueError(f"Unsupported generation mode: {mode}")

    def _generate_real(self, requests: List[VeoRequest]) -> List[str]:
        generated_files = []
        print(f"Starting REAL CLIP generation for {len(requests)} shots...")
        
        url_map_path = os.path.join(self.output_dir, "image_urls.json")
        url_map = {}
        if os.path.exists(url_map_path):
             with open(url_map_path, 'r') as f:
                 url_map = json.load(f)

        for req in requests:
            filename = f"{req.shot_id}.mp4"
            filepath = os.path.join(self.assets_dir, filename)

            # Resolve Image Paths/URLs to pass to Client
            start_filename = f"{req.shot_id}_start_ref.png"
            end_filename = f"{req.shot_id}_end_ref.png"
            
            if start_filename in url_map:
                req.image_ref_start = url_map[start_filename]
                print(f"Attached Start Image (URL): {req.image_ref_start}")
            
            if end_filename in url_map:
                req.image_ref_end = url_map[end_filename]
                print(f"Attached End Image (URL): {req.image_ref_end}")
            
            if not req.image_ref_start and not req.image_ref_end:
                print(f"WARNING: No image URLs found for {req.shot_id}. Video will be text-only.")
            
            try:
                print(f"Generating Real Clip: {filename}")
                # Tuple return: (video_bytes, video_url)
                video_bytes, video_url = self.client.generate_clip(req)
                
                with open(filepath, 'wb') as f:
                    f.write(video_bytes)

                generated_files.append(filename)

                if video_url:
                     url_map[filename] = video_url
                     print(f"Captured Video URL: {video_url}")
                
                time.sleep(2.0) 
                
            except Exception as e:
                print(f"FAILED to generate clip {req.shot_id}: {e}")
                raise e
        
        # Save updated URL Map (Critical for Airtable Sync)
        with open(url_map_path, 'w') as f:
            json.dump(url_map, f, indent=2)

        return generated_files

    def _generate_placeholders(self, requests: List[VeoRequest]) -> List[str]:
        generated_files = []
        print(f"Generating {len(requests)} CLIP PLACEHOLDERS...")
        for req in requests:
            filename = f"{req.shot_id}.mp4"
            filepath = os.path.join(self.assets_dir, filename)
            
            with open(filepath, 'wb') as f:
                 f.write(b'\x00\x00\x00\x20ftypmp42\x00\x00\x00\x00mp42mp41\x00\x00\x00\x00')
            
            generated_files.append(filename)
            print(f"Generated Clip: {filename}")
        return generated_files

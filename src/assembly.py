import os
import subprocess
import json
from typing import List
from .models import Manifest, ShotSpec

class VideoAssembler:
    def __init__(self, output_dir: str, width: int = 1920, height: int = 1080, fps: int = 30):
        self.output_dir = output_dir
        self.assets_dir = os.path.join(output_dir, "assets")
        self.staging_dir = os.path.join(output_dir, "assembly_staging")
        os.makedirs(self.staging_dir, exist_ok=True)
        
        self.width = width
        self.height = height
        self.fps = fps

    def assemble(self, shot_specs: List[ShotSpec], audio_path: str) -> str:
        """
        Assembles the video. Returns path to final output.
        """
        print(f"Starting Assembly of {len(shot_specs)} shots...")
        
        concat_list_path = os.path.join(self.staging_dir, "concat_list.txt")
        chunks = []

        # 1. Pre-process Chunks
        for i, shot in enumerate(shot_specs):
            # Identify Source
            # Try .mp4 first, then .png (fallback or static)
            mp4_path = os.path.join(self.assets_dir, f"{shot.id}.mp4")
            # If not using ID, maybe using role convention? 
            # Current generator uses {shot_id}.mp4 or {shot_id}_ref.png
            # We'll check standard names.
            
            source_path = None
            is_video = False
            
            if os.path.exists(mp4_path):
                source_path = mp4_path
                is_video = True
            else:
                 # Fallback to image
                 png_path = os.path.join(self.assets_dir, f"{shot.id}_start.png") # Try strict first
                 if not os.path.exists(png_path):
                     # Try loose convention logic or just skip/fail?
                     # Robustness: Try finding any file starting with shot_id?
                     # MVP: strict name
                     pass
                 
                 if os.path.exists(png_path):
                     source_path = png_path
                     is_video = False
            
            if not source_path:
                print(f"WARNING: No asset for {shot.id}. Generating Black Frame.")
                # We will handle black frame in ffmpeg generation
                source_path = "BLACK"

            chunk_filename = f"chunk_{i:04d}_{shot.id}.mp4"
            chunk_path = os.path.join(self.staging_dir, chunk_filename)
            
            # Exact duration required
            duration = shot.duration_s
            
            self._render_chunk(source_path, chunk_path, duration, is_video)
            chunks.append(chunk_path)
            print(f"Rendered Chunk {i+1}/{len(shot_specs)}: {chunk_filename}")

        # 2. Write Concat List
        with open(concat_list_path, "w") as f:
            for chunk in chunks:
                # escape paths usually not needed if simple names, but careful with backslashes on win
                # ffmpeg requires forward slashes or escaped backslashes
                safe_path = chunk.replace("\\", "/")
                f.write(f"file '{safe_path}'\n")

        # 3. Concatenate & Mux Audio
        output_filename = "final_render.mp4"
        output_path = os.path.join(self.output_dir, output_filename)
        
        # ffmpeg -f concat -safe 0 -i list.txt -i audio.mp3 -c:v copy -map 0:v -map 1:a -shortest out.mp4
        # Note: We re-encoded chunks to be identical, so copy is safe and fast.
        
        cmd = [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", concat_list_path,
            "-i", audio_path,
            "-c:v", "copy",
            "-c:a", "aac",
            "-shortest", # Stop when video ends (or audio ends? usually video drives visual)
            # Actually, script determines duration. Audio might be slightly longer/shorter due to silence/trim.
            # We want ensuring sync.
            output_path
        ]
        
        print(f"Running Final Concat: {' '.join(cmd)}")
        subprocess.check_call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
        
        return output_path

    def _render_chunk(self, source, output, duration, is_video):
        """
        Normalizes any input to exactly:
        - 1920x1080
        - 30 fps
        - yuv420p
        - Fixed Duration
        """
        # Base filters
        # scale=-1:1080 helps keep aspect ratio, but we want strict 1920x1080. 
        # force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2
        filter_str = f"scale={self.width}:{self.height}:force_original_aspect_ratio=decrease,pad={self.width}:{self.height}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={self.fps},format=yuv420p"
        
        cmd = ["ffmpeg", "-y"]
        
        if source == "BLACK":
            # Generate black video
            # -f lavfi -i color=c=black:s=1920x1080:r=30 -t duration
            cmd.extend([
                "-f", "lavfi",
                "-i", f"color=c=black:s={self.width}x{self.height}:r={self.fps}",
                "-t", str(duration)
            ])
            # Filter usually not strictly needed for black if generated correct, but good to be safe on pixel format
            cmd.extend(["-vf", "format=yuv420p"])
            
        else:
            if not is_video:
                # Loop image
                cmd.extend([
                    "-loop", "1",
                    "-i", source,
                    "-t", str(duration)
                ])
                cmd.extend(["-vf", filter_str])
            else:
                # Video: Input -> Trim/Pad -> Filter
                # We need to ensure it fills duration. 
                # If too short? -stream_loop? But that repeats.
                # Ideally Veo gives enough. If not, we try to freeze frame?
                # For MVP: simple -t strict
                cmd.extend([
                    "-i", source,
                    "-t", str(duration) # This cuts if long. If short, it stops early? ffmpeg standard behavior varies.
                    # To fix "too short", we usually create a complex filter to hold last frame, but that's complex.
                    # We assume Veo/Mock provides coverage.
                ])
                cmd.extend(["-vf", filter_str])

        # Encoding speed/quality
        cmd.extend([
            "-c:v", "libx264",
            "-preset", "ultrafast", # assembly speed important
            "-crf", "23",
            output
        ])
        
        try:
            # DEBUG: capture output to see error
            subprocess.check_call(cmd)
        except subprocess.CalledProcessError as e:
            print(f"Error rendering chunk {output} from {source}")
            raise e

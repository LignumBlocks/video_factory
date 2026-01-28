from src.orchestrator import Pipeline

import argparse
import sys
import os
import json
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def get_export_dir_from_manifest(pipeline, run_id, version):
    """
    Resolve export_dir by reading manifest.json (no timestamp_hash discovery).
    Contract: planning stage creates manifest.json with export_dir field.
    """
    search_root = pipeline.export_root
    if not os.path.exists(search_root):
        raise FileNotFoundError(f"Export root not found: {search_root}")
        
    for date_folder in os.listdir(search_root):
        manifest_path = os.path.join(search_root, date_folder, f"run_{run_id}", 
                                     f"v{version}", "manifest.json")
        if os.path.exists(manifest_path):
            with open(manifest_path, 'r', encoding='utf-8') as f:
                manifest_data = json.load(f)
                export_dir = manifest_data.get('export_dir')
                if export_dir:
                    return export_dir
    
    raise FileNotFoundError(f"No manifest.json found for {run_id} v{version}")

def main():
    parser = argparse.ArgumentParser(description="HL Video Factory Pipeline")
    parser.add_argument("--run_id", type=str, required=True, help="Unique Run ID")
    parser.add_argument("--version", type=int, required=True, help="Version number")
    parser.add_argument("--project_id", type=str, default="PROJ_FIN", help="Project ID")
    parser.add_argument("--video_id", type=str, default="VID_001", help="Video ID")
    parser.add_argument("--stage", type=str, required=True, choices=["planning", "prompts", "images", "clips", "assembly"], help="Pipeline Stage")
    parser.add_argument("--mode", type=str, choices=["simulation", "real"], default="simulation", help="Generation Mode")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of items to process (e.g. max images)")
    
    args = parser.parse_args()
    
    print(f"DEBUG: main.py received run_id={args.run_id}, version={args.version}, stage={args.stage}")
    
    pipeline = Pipeline(
        run_id=args.run_id, 
        version=args.version,
        project_id=args.project_id,
        video_id=args.video_id
    )
    
    try:
        if args.stage == "planning":
            pipeline.run()
        elif args.stage == "prompts":
            export_dir = get_export_dir_from_manifest(pipeline, args.run_id, args.version)
            pipeline.run_prompts(export_dir, limit=args.limit)
        elif args.stage == "images":
            export_dir = get_export_dir_from_manifest(pipeline, args.run_id, args.version)
            from src.models import GenerationMode
            gen_mode = GenerationMode.REAL if args.mode == "real" else GenerationMode.SIMULATION
            pipeline.run_images(export_dir, mode=gen_mode, limit=args.limit)
        elif args.stage == "clips":
            export_dir = get_export_dir_from_manifest(pipeline, args.run_id, args.version)
            from src.models import GenerationMode
            gen_mode = GenerationMode.REAL if args.mode == "real" else GenerationMode.SIMULATION
            pipeline.run_clips(export_dir, mode=gen_mode, limit=args.limit)
        elif args.stage == "assembly":
            export_dir = get_export_dir_from_manifest(pipeline, args.run_id, args.version)
            pipeline.run_assembly(export_dir)
            
        print(f"SUCCESS: Pipeline Stage '{args.stage}' executed.")
    except Exception as e:
        print(f"FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()

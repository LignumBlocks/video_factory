import argparse
import sys
import os
from dotenv import load_dotenv
from src.orchestrator import RunOrchestrator

# Load environment variables
load_dotenv()

def main():
    parser = argparse.ArgumentParser(description="FinanceVideoPlatform CLI Runner")
    
    # Run Identity
    parser.add_argument("--run_id", type=str, help="Resume specific Run ID")
    parser.add_argument("--video_id", type=str, default="VID_001", help="Video ID")
    
    # Inputs (Required for new run)
    parser.add_argument("--script", type=str, help="Path to script.txt")
    parser.add_argument("--audio", type=str, help="Path to voiceover.mp3")
    parser.add_argument("--bible", type=str, help="Path to style_bible.md")
    
    # Execution Control
    parser.add_argument("--stage", type=str, choices=["ingest", "planning", "prompts", "generation", "assembly"], default="ingest")
    
    args = parser.parse_args()
    
    try:
        # Check if we are starting new or resuming
        if args.run_id:
            print(f"Resuming Run: {args.run_id}")
            orchestrator = RunOrchestrator(run_id=args.run_id, video_id=args.video_id)
        else:
            print("Starting New Run")
            orchestrator = RunOrchestrator(video_id=args.video_id)
            
        if args.stage == "ingest":
            if not (args.script and args.audio and args.bible):
                print("Error: --script, --audio, and --bible are required for ingest phase.")
                sys.exit(1)
            orchestrator.ingest(args.script, args.audio, args.bible)
        
        else:
            # Future stages
            orchestrator.run_stage(args.stage)

    except Exception as e:
        print(f"FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()

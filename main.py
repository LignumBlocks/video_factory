import argparse
import sys
import os
import logging
from dotenv import load_dotenv
from src.orchestrator import RunOrchestrator

# Load environment variables
load_dotenv()

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("logs/cli.log", mode='a')
    ]
)
logger = logging.getLogger("CLI")
os.makedirs("logs", exist_ok=True)

def handle_create_run(args):
    try:
        logger.info("Command: create-run")
        orchestrator = RunOrchestrator(video_id=args.video_id)
        
        # Initialize (Run Validation + Manifest + Folder Structure)
        orchestrator.initialize_run(args.script, args.voiceover, args.bible)
        
        # If we succeeded, orchestrator.run_id is set
        # Check if preflight failed? initialize_run handles it internally 
        # but we might want to check manifest status here to be explicit in CLI output.
        if orchestrator.manifest.status == "FAILED_PREFLIGHT":
             print(f"Run Created but FAILED PREFLIGHT: {orchestrator.run_id}")
             print("Check preflight_report.json in run folder.")
             sys.exit(1)
        
        print(f"Run Created Successfully.")
        print(f"Run ID: {orchestrator.run_id}")
        print(f"Artifacts Path: {orchestrator.run_dir}")
        
    except Exception as e:
        logger.error(f"Create Run Failed: {e}")
        sys.exit(1)

def handle_execute_run(args):
    try:
        logger.info(f"Command: execute-run --run-id {args.run_id}")
        orchestrator = RunOrchestrator(run_id=args.run_id)
        orchestrator.run()
        print("Execution Finished.")
    except Exception as e:
        logger.error(f"Execute Run Failed: {e}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="FinanceVideoPlatform CLI Runner")
    subparsers = parser.add_subparsers(dest="command", required=True, help="Command to execute")

    # Command: create-run
    create_parser = subparsers.add_parser("create-run", help="Create and Initialize a new Run")
    create_parser.add_argument("--script", required=True, help="Path to script.txt")
    create_parser.add_argument("--voiceover", required=True, help="Path to voiceover.mp3")
    create_parser.add_argument("--bible", required=True, help="Path to style_bible.md")
    create_parser.add_argument("--video_id", default="VID_001", help="Video ID assignment")
    create_parser.set_defaults(func=handle_create_run)

    # Command: execute-run
    execute_parser = subparsers.add_parser("execute-run", help="Execute an existing Run")
    execute_parser.add_argument("--run-id", required=True, help="Run ID to execute")
    execute_parser.set_defaults(func=handle_execute_run)

    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()

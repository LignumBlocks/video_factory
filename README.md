# HL Video Factory Pipeline (Hintsly Lab)

Automated Pipeline for High-Quality Educational Video Generation.
Includes Operator Console (Next.js + FastAPI) and Alignment Gateway.

## Structure
- `src/`: Core Pipeline Logic (Orchestrator, AudioEngine).
- `console/`: 
  - `frontend/`: Next.js Operator Dashboard.
  - `backend/`: FastAPI Control Plane.
  - `deployment/`: Systemd services and Caddy configurations.
- `alignment_gateway/`: Microservice for Audio/Text Alignment.
- `main.py`: Command Line Interface.

## Deployment
See `RUNBOOK_CONSOLE_VPS.md` for VPS deployment instructions.

## Development
1. Install dependencies: `pip install -r requirements.txt`.
2. Run Pipeline: `python main.py ...`
3. Run Console: `cd console/frontend && npm run dev`
Proyecto 1 esta en: "Project-1-TheCleanScoreJump", alli esta el voiceover, el script del VO, la biblia de estilos y los assets.


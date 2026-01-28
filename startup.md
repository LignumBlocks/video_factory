# Startup & Restart Instructions

Follow these steps to restart the services and apply the latest fixes (Environment Variables & Database Schema).

## 1. Activate Virtual Environment
Ensure you are using the project's virtual environment.
```bash
if [ -d "venv" ]; then source venv/bin/activate; fi
```

## 2. Restart Main Backend Server
This service orchestrates the pipeline AND handles audio alignment internally.

```bash
# Stop existing process
pkill -f "python -m src.server.app"

# Start service (Port 8000)
python -m src.server.app
```

## 3. Run Frontend (GUI)
If not already running:

```bash
cd src/gui
yarn dev
```

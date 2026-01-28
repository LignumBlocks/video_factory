#!/bin/bash
set -e

# Video Finance Platform - VPS Repair Script
# Usage: sudo ./fix_vps_deployment.sh

LOG_FILE="/var/log/finance_repair.log"
exec > >(tee -a $LOG_FILE) 2>&1

echo ">>> STARTING VPS REPAIR $(date) <<<"

# 1. BACKEND REPAIR
echo "[1] Fixing Backend Service..."

# Ensure venv exists
VENV_PATH="/opt/finance_console/venv"
if [ ! -d "$VENV_PATH" ]; then
    echo "Creating virtualenv..."
    python3 -m venv $VENV_PATH
fi

# Install dependencies (Uvicorn missing!)
echo "Installing dependencies..."
$VENV_PATH/bin/pip install uvicorn fastapi python-dotenv pydantic

# Fix Service File (Ensure binding to 127.0.0.1:8090)
SERVICE_FILE="/etc/systemd/system/finance-console.service"
if grep -q "0.0.0.0" $SERVICE_FILE; then
    echo "Binding to localhost only for security..."
    sed -i 's/0.0.0.0/127.0.0.1/g' $SERVICE_FILE
fi

# Restart Service
systemctl daemon-reload
systemctl restart finance-console
systemctl enable finance-console

# Verify Port
sleep 2
if ss -ltnp | grep -q ":8090"; then
    echo "SUCCESS: Backend listening on 8090."
else
    echo "ERROR: Backend failed to start. Checking logs..."
    journalctl -u finance-console -n 20 --no-pager
    exit 1
fi

# 2. CADDY REPAIR
echo "[2] Verifying Caddy..."
# Assumption: Caddyfile exists at /etc/caddy/Caddyfile
if ! systemctl is-active --quiet caddy; then
    echo "Starting Caddy..."
    systemctl start caddy
fi

# 3. STORAGE REPAIR
echo "[3] Checking Google Drive Mount..."
MOUNT_POINT="/mnt/gdrive"
DATA_DIR="$MOUNT_POINT/finance_video_factory"

if ! mountpoint -q $MOUNT_POINT; then
    echo "Mounting GDrive..."
    systemctl restart rclone-gdrive
    sleep 5
fi

if [ -d "$DATA_DIR" ]; then
    echo "SUCCESS: Canon path exists: $DATA_DIR"
else
    echo "WARNING: Canon path $DATA_DIR not found. Listing mount root:"
    ls -la $MOUNT_POINT
fi

echo ">>> REPAIR COMPLETE <<<"
echo "Run verification commands manually if needed."

#!/bin/bash

# FinanceVideoPlatform - VPS Setup Script for Ubuntu
# Run with: sudo bash setup_vps.sh

set -e

echo "🚀 Starting FinanceVideoPlatform VPS Setup..."

# 1. System Updates & Python 3.10 PPA
echo "📦 Updating system packages..."
apt update && apt upgrade -y
apt install -y software-properties-common
add-apt-repository -y ppa:deadsnakes/ppa
apt update

apt install -y python3.10 python3.10-venv python3-pip git curl wget ffmpeg sqlite3 build-essential libssl-dev

# 2. Node.js Installation
echo "🟢 Installing Node.js 20..."
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
apt install -y nodejs

# 3. Environment Setup (Root dir of the project)
PROJECT_ROOT=$(pwd)
echo "📂 Project Root: $PROJECT_ROOT"

# 4. Python Backend Setup
echo "🐍 Setting up Python Virtual Environment..."
python3.10 -m venv venv
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.txt

# 5. Frontend Setup & Build
echo "🎨 Building Frontend..."
cd src/gui
npm install
npm run build
cd ../..

# 6. Database Migration
echo "🗄️ Initializing Database..."
./venv/bin/python migrate_db.py || echo "Warning: migrate_db.py failed or not found, skipping."

# 7. Systemd Services
echo "⚙️ Creating systemd services..."

# Backend Service (Port 8001)
cat <<EOF > /etc/systemd/system/cockpit-backend.service
[Unit]
Description=Finance Video Platform Backend (Cockpit)
After=network.target

[Service]
User=$USER
WorkingDirectory=$PROJECT_ROOT
Environment="PATH=$PROJECT_ROOT/venv/bin"
Environment="PORT=8001"
ExecStart=$PROJECT_ROOT/venv/bin/python -m src.server.app
Restart=always

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable cockpit-backend

echo "✅ Script setup complete!"
echo "⚠️  ADVERTENCIA: No se instaló Nginx porque usas Caddy."
echo "⚠️  IMPORTANTE: Crea tu archivo .env en $PROJECT_ROOT"
echo "Asegúrate de incluir 'PORT=8001' en tu .env"
echo ""
echo "🔥 Agrega este bloque a tu /etc/caddy/Caddyfile:"
echo "------------------------------------------------"
echo "cockpit.orquix.com {"
echo "    encode zstd gzip"
echo ""
echo "    # Backend API"
echo "    handle /api/* {"
echo "        reverse_proxy 127.0.0.1:8001"
echo "    }"
echo ""
echo "    # Assets generados (Imágenes/Videos)"
echo "    handle /exports/* {"
echo "        root * $PROJECT_ROOT"
echo "        file_server"
echo "    }"
echo ""
echo "    # Frontend UI (SPA)"
echo "    handle {"
echo "        root * $PROJECT_ROOT/src/gui/dist"
echo "        try_files {path} /index.html"
echo "        file_server"
echo "    }"
echo "}"
echo "------------------------------------------------"

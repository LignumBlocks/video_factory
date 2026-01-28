# Operator Console v1 - VPS Deployment Runbook (Full Stack)

Target: Ubuntu 24.04 VPS
Domain: `console.orquix.com`

## 1. Prerequisites (VPS)

Ensure Node.js 18+ and Python 3.10+ are installed.

```bash
# Install Node.js
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs
```

## 2. Deploy Code

Copy `finance_video_factory` to `/srv/finance_video_factory_console`.

## 3. Backend Setup

```bash
cd /srv/finance_video_factory_console
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -r console/backend/requirements.txt
pip install "uvicorn[standard]"
```

## 4. Frontend Setup

```bash
cd /srv/finance_video_factory_console/console/frontend
npm install
npm run build
```

## 5. Systemd Services

### Backend Service (`finance_backend`)
Runs Uvicorn on port 8090.

```bash
cp ../deployment/finance_backend.service /etc/systemd/system/
systemctl enable finance_backend
systemctl start finance_backend
```

### Frontend Service (`finance_frontend`)
Runs Next.js on port 3000.

```bash
cp ../deployment/finance_frontend.service /etc/systemd/system/
systemctl enable finance_frontend
systemctl start finance_frontend
```

## 6. Reverse Proxy (Caddy)

Configure `/etc/caddy/Caddyfile` with the snippet from `console/deployment/Caddyfile.snippet`.

```caddy
console.orquix.com {
    handle /api/* { reverse_proxy 127.0.0.1:8090 }
    handle { reverse_proxy 127.0.0.1:3000 }
}
```

Reload Caddy: `systemctl reload caddy`.

## 7. Verification

Visit `https://console.orquix.com`.
- **UI**: Should load Next.js App.
- **API**: Check network tab for calls to `/api/...`.

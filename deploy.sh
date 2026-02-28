#!/usr/bin/env bash
# ============================================================
# deploy.sh — Set up Dynamic QR Links on a GCE e2-micro
# Run on a fresh Debian 12 / Ubuntu 22+ instance:
#   chmod +x deploy.sh && sudo ./deploy.sh
# ============================================================
set -euo pipefail

APP_USER="qrlinks"
APP_DIR="/opt/qrlinks"
REPO_URL="https://github.com/aakashbohara/dynamicqrlinks.git"   # <-- CHANGE THIS
DB_NAME="qrlinks"
DB_USER="qrlinks"
DB_PASS="$(openssl rand -base64 24)"  # auto-generate strong password

echo "=========================================="
echo " Dynamic QR Links — GCE Deployment"
echo "=========================================="

# ---------- 1. System packages ----------
echo "[1/7] Installing system packages..."
apt-get update -qq
apt-get install -y -qq \
  python3 python3-venv python3-pip python3-dev \
  postgresql postgresql-contrib \
  nginx certbot python3-certbot-nginx \
  git build-essential libpq-dev

# ---------- 2. PostgreSQL ----------
echo "[2/7] Setting up PostgreSQL..."
systemctl enable postgresql
systemctl start postgresql

# Create DB user and database
sudo -u postgres psql -tc "SELECT 1 FROM pg_roles WHERE rolname='${DB_USER}'" | grep -q 1 || \
  sudo -u postgres psql -c "CREATE USER ${DB_USER} WITH PASSWORD '${DB_PASS}';"
sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='${DB_NAME}'" | grep -q 1 || \
  sudo -u postgres psql -c "CREATE DATABASE ${DB_NAME} OWNER ${DB_USER};"

echo "  ✓ DB: ${DB_NAME}  User: ${DB_USER}"
echo "  ✓ DB Password: ${DB_PASS}  (save this!)"

# ---------- 3. App user & code ----------
echo "[3/7] Setting up application..."
id -u ${APP_USER} &>/dev/null || useradd -r -m -s /bin/bash ${APP_USER}

if [ -d "${APP_DIR}" ]; then
  echo "  → Pulling latest code..."
  cd ${APP_DIR} && git pull
else
  echo "  → Cloning repo..."
  git clone ${REPO_URL} ${APP_DIR}
fi
chown -R ${APP_USER}:${APP_USER} ${APP_DIR}

# ---------- 4. Python venv + deps ----------
echo "[4/7] Installing Python dependencies..."
cd ${APP_DIR}
sudo -u ${APP_USER} python3 -m venv venv
sudo -u ${APP_USER} ./venv/bin/pip install --quiet --upgrade pip
sudo -u ${APP_USER} ./venv/bin/pip install --quiet -r requirements.txt

# ---------- 5. .env ----------
echo "[5/7] Configuring environment..."
if [ ! -f "${APP_DIR}/.env" ]; then
  SECRET_KEY=$(openssl rand -base64 64 | tr -d '\n')
  cat > ${APP_DIR}/.env <<ENVFILE
ENVIRONMENT=prod
DATABASE_URL=postgresql+psycopg2://${DB_USER}:${DB_PASS}@localhost:5432/${DB_NAME}
SECRET_KEY=${SECRET_KEY}
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
ADMIN_USERNAME=admin
ADMIN_PASSWORD=$(openssl rand -base64 16 | tr -d '\n')
PUBLIC_BASE_URL=http://$(curl -s ifconfig.me)
ENVFILE
  chown ${APP_USER}:${APP_USER} ${APP_DIR}/.env
  chmod 600 ${APP_DIR}/.env
  echo "  ✓ .env created (review & update PUBLIC_BASE_URL and ADMIN creds)"
  echo ""
  echo "  ╔══════════════════════════════════════════╗"
  echo "  ║  IMPORTANT — Save these credentials!     ║"
  echo "  ╚══════════════════════════════════════════╝"
  cat ${APP_DIR}/.env
  echo ""
else
  echo "  → .env already exists, skipping"
fi

# ---------- 6. systemd service ----------
echo "[6/7] Creating systemd service..."
cat > /etc/systemd/system/qrlinks.service <<SERVICE
[Unit]
Description=Dynamic QR Links (FastAPI)
After=network.target postgresql.service
Requires=postgresql.service

[Service]
User=${APP_USER}
Group=${APP_USER}
WorkingDirectory=${APP_DIR}/app
EnvironmentFile=${APP_DIR}/.env
ExecStart=${APP_DIR}/venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000 --workers 2
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
SERVICE

systemctl daemon-reload
systemctl enable qrlinks
systemctl restart qrlinks
echo "  ✓ qrlinks.service started"

# ---------- 7. Nginx ----------
echo "[7/7] Configuring Nginx..."
cp ${APP_DIR}/nginx/qrlinks.conf /etc/nginx/sites-available/qrlinks
ln -sf /etc/nginx/sites-available/qrlinks /etc/nginx/sites-enabled/qrlinks
rm -f /etc/nginx/sites-enabled/default
mkdir -p /var/www/certbot
nginx -t && systemctl reload nginx
echo "  ✓ Nginx configured"

# ---------- Done ----------
EXTERNAL_IP=$(curl -s ifconfig.me)
echo ""
echo "=========================================="
echo " ✅ Deployment complete!"
echo "=========================================="
echo ""
echo " App running at: http://${EXTERNAL_IP}"
echo " Health check:   http://${EXTERNAL_IP}/health"
echo ""
echo " Next steps:"
echo "   1. Review credentials:  cat ${APP_DIR}/.env"
echo "   2. Point your domain DNS A record → ${EXTERNAL_IP}"
echo "   3. Get HTTPS:  sudo certbot --nginx -d YOUR_DOMAIN"
echo "   4. Update PUBLIC_BASE_URL in .env to https://YOUR_DOMAIN"
echo "   5. Restart:  sudo systemctl restart qrlinks"
echo ""
echo " Useful commands:"
echo "   sudo systemctl status qrlinks     # check app status"
echo "   sudo journalctl -u qrlinks -f     # live logs"
echo "   sudo systemctl restart qrlinks    # restart app"
echo ""

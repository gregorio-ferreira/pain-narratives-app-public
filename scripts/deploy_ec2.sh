#!/usr/bin/env bash
# Setup AINarratives Streamlit app on AWS EC2 with HTTPS

# git config --global user.email "ferreiradesajg@gmail.com"
# git config --global user.name "gregorio"


# curl -LsSf https://astral.sh/uv/install.sh | sh
# echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc && source ~/.bashrc

# uv --version

# sudo apt install make
# make install

# Usage: sudo ./scripts/deploy_ec2.sh <domain> [email]
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
  echo "Please run this script with sudo or as root" >&2
  exit 1
fi

DOMAIN="${1:-}"
EMAIL="${2:-}"  # Optional email for Certbot

if [[ -z "$DOMAIN" ]]; then
  echo "Usage: sudo $0 <domain> [email]"
  exit 1
fi

APP_DIR="$(cd "$(dirname "$0")"/.. && pwd)"
APP_USER="${SUDO_USER:-$USER}"


# Install Nginx and OpenSSL (for self-signed cert)
apt update
apt install -y nginx openssl


# Generate self-signed SSL certificate
SSL_DIR="/etc/ssl/pain-narratives"
mkdir -p "$SSL_DIR"
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout "$SSL_DIR/selfsigned.key" \
  -out "$SSL_DIR/selfsigned.crt" \
  -subj "/CN=$DOMAIN"

# Configure Nginx
cat <<NGINX | tee /etc/nginx/sites-available/streamlit
server {
    listen 80;
    server_name $DOMAIN;
    return 301 https://$DOMAIN\$request_uri;
}

server {
    listen 443 ssl;
    server_name $DOMAIN;

    ssl_certificate $SSL_DIR/selfsigned.crt;
    ssl_certificate_key $SSL_DIR/selfsigned.key;

    location / {
        proxy_pass http://localhost:8501;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
NGINX


ln -sf /etc/nginx/sites-available/streamlit /etc/nginx/sites-enabled/streamlit
nginx -t
systemctl reload nginx


# Create systemd service for Streamlit
cat <<EOF | tee /etc/systemd/system/pain-narratives.service
[Unit]
Description=AINarratives Streamlit App
After=network.target

[Service]
Type=simple
User=$APP_USER
WorkingDirectory=$APP_DIR
ExecStart=$APP_DIR/.venv/bin/uv run streamlit run scripts/run_app.py --server.address localhost --server.port 8501
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable pain-narratives.service
systemctl start pain-narratives.service

# Ensure Nginx is enabled on boot
systemctl enable nginx

cat <<END
Deployment complete!
The app will be accessible at: https://$DOMAIN
Note: Your browser will show a warning because this is a self-signed certificate.
END

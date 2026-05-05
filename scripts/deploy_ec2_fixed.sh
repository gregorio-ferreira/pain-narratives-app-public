#!/usr/bin/env bash
# Setup Pain Narratives Streamlit app on AWS EC2 with HTTPS (FIXED VERSION)
# This version includes proper static file handling and WebSocket support

# Usage: sudo ./scripts/deploy_ec2_fixed.sh <domain> [email]
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

echo "🚀 Deploying Pain Narratives Application"
echo "Domain: $DOMAIN"
echo "App Directory: $APP_DIR"
echo "App User: $APP_USER"
echo ""

# Install Nginx and OpenSSL (for self-signed cert)
echo "📦 Installing Nginx and OpenSSL..."
apt update
apt install -y nginx openssl

# Generate self-signed SSL certificate
echo "🔐 Generating SSL certificate..."
SSL_DIR="/etc/ssl/pain-narratives"
mkdir -p "$SSL_DIR"
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout "$SSL_DIR/selfsigned.key" \
  -out "$SSL_DIR/selfsigned.crt" \
  -subj "/CN=$DOMAIN"

# Configure Nginx with improved static file handling
echo "⚙️  Configuring Nginx reverse proxy..."
cat <<'NGINX' | tee /etc/nginx/sites-available/streamlit
server {
    listen 80;
    server_name DOMAIN_PLACEHOLDER;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name DOMAIN_PLACEHOLDER;

    ssl_certificate SSL_DIR_PLACEHOLDER/selfsigned.crt;
    ssl_certificate_key SSL_DIR_PLACEHOLDER/selfsigned.key;

    # SSL optimizations
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # Increase max body size for file uploads
    client_max_body_size 100M;

    # Logging
    access_log /var/log/nginx/streamlit-access.log;
    error_log /var/log/nginx/streamlit-error.log;

    # WebSocket and streaming endpoint (critical for Streamlit)
    location /_stcore/stream {
        proxy_pass http://localhost:8501/_stcore/stream;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400;
        proxy_buffering off;
    }

    # Static assets (CSS, JS, images) - FIX for CSS preload error
    location /static/ {
        proxy_pass http://localhost:8501/static/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Cache control for static assets
        proxy_cache_valid 200 1d;
        add_header Cache-Control "public, max-age=86400";
        
        # CORS headers for static files
        add_header Access-Control-Allow-Origin *;
        add_header Access-Control-Allow-Methods "GET, OPTIONS";
        add_header Access-Control-Allow-Headers "Content-Type";
    }

    # Health check endpoint
    location /healthz {
        proxy_pass http://localhost:8501/healthz;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        access_log off;
    }

    # Main application
    location / {
        proxy_pass http://localhost:8501;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $host;
        proxy_set_header X-Forwarded-Port $server_port;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 86400;
        proxy_cache_bypass $http_upgrade;
        proxy_buffering off;
    }
}
NGINX

# Replace placeholders
sed -i "s|DOMAIN_PLACEHOLDER|$DOMAIN|g" /etc/nginx/sites-available/streamlit
sed -i "s|SSL_DIR_PLACEHOLDER|$SSL_DIR|g" /etc/nginx/sites-available/streamlit

# Enable site and test configuration
ln -sf /etc/nginx/sites-available/streamlit /etc/nginx/sites-enabled/streamlit
nginx -t
systemctl reload nginx

# Create .streamlit directory and config
echo "📝 Creating Streamlit configuration..."
mkdir -p "$APP_DIR/.streamlit"
cat <<STREAMLIT_CONFIG | tee "$APP_DIR/.streamlit/config.toml"
[server]
# Server configuration
port = 8501
address = "localhost"
baseUrlPath = ""
enableCORS = false
enableXsrfProtection = true

# Enable static file serving (FIX for CSS preload error)
enableStaticServing = true

# WebSocket configuration
maxUploadSize = 200
maxMessageSize = 200

# Performance
runOnSave = false
allowRunOnSave = false

[browser]
# Prevent automatic opening
gatherUsageStats = false
serverAddress = "$DOMAIN"
serverPort = 443

[client]
# Client configuration
showErrorDetails = true
toolbarMode = "minimal"

[theme]
# Default theme
primaryColor = "#FF4B4B"
backgroundColor = "#FFFFFF"
secondaryBackgroundColor = "#F0F2F6"
textColor = "#262730"
font = "sans serif"
STREAMLIT_CONFIG

chown $APP_USER:$APP_USER "$APP_DIR/.streamlit/config.toml"

# Create systemd service for Streamlit
echo "🔧 Creating systemd service..."
cat <<EOF | tee /etc/systemd/system/pain-narratives.service
[Unit]
Description=Pain Narratives Streamlit App
After=network.target

[Service]
Type=simple
User=$APP_USER
WorkingDirectory=$APP_DIR
Environment="PATH=/home/ubuntu/.local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
Environment="STREAMLIT_SERVER_ENABLE_STATIC_SERVING=true"
Environment="STREAMLIT_SERVER_ENABLE_CORS=false"
Environment="STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION=true"
ExecStart=/home/ubuntu/.local/bin/uv run streamlit run scripts/run_app.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable pain-narratives.service
systemctl restart pain-narratives.service

# Ensure Nginx is enabled on boot
systemctl enable nginx

# Wait for service to start
echo "⏳ Waiting for application to start..."
sleep 5

# Check service status
echo ""
echo "📊 Service Status:"
systemctl status pain-narratives.service --no-pager | head -15

echo ""
echo "✅ Deployment complete!"
echo ""
echo "📍 Application URL: https://$DOMAIN"
echo "🔐 Note: Your browser will show a warning for self-signed certificates"
echo ""
echo "📋 Useful commands:"
echo "  - Check app status:    sudo systemctl status pain-narratives.service"
echo "  - View app logs:       sudo journalctl -u pain-narratives.service -f"
echo "  - Check Nginx logs:    sudo tail -f /var/log/nginx/streamlit-error.log"
echo "  - Restart app:         sudo systemctl restart pain-narratives.service"
echo "  - Restart Nginx:       sudo systemctl reload nginx"
echo ""
echo "🔒 To use Let's Encrypt instead of self-signed certificate:"
echo "  sudo apt install certbot python3-certbot-nginx"
echo "  sudo certbot --nginx -d $DOMAIN"
echo ""

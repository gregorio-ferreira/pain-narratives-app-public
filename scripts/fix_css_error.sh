#!/usr/bin/env bash
# Quick fix script for CSS preload error
# Run this on the existing server without redeploying

set -euo pipefail

if [[ $EUID -ne 0 ]]; then
  echo "❌ Please run this script with sudo or as root" >&2
  exit 1
fi

APP_DIR="/home/ubuntu/pain-narratives-app"
DOMAIN="ec2-63-176-147-227.eu-central-1.compute.amazonaws.com"
APP_USER="ubuntu"

echo "🔧 Quick Fix for CSS Preload Error"
echo "=================================="
echo ""

# Backup existing configurations
echo "📦 Creating backups..."
cp /etc/nginx/sites-available/streamlit /etc/nginx/sites-available/streamlit.backup.$(date +%Y%m%d_%H%M%S)
cp /etc/systemd/system/pain-narratives.service /etc/systemd/system/pain-narratives.service.backup.$(date +%Y%m%d_%H%M%S)

# Update Nginx configuration
echo "⚙️  Updating Nginx configuration..."
cat <<'NGINX' | tee /etc/nginx/sites-available/streamlit
server {
    listen 80;
    server_name ec2-63-176-147-227.eu-central-1.compute.amazonaws.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name ec2-63-176-147-227.eu-central-1.compute.amazonaws.com;

    ssl_certificate /etc/ssl/pain-narratives/selfsigned.crt;
    ssl_certificate_key /etc/ssl/pain-narratives/selfsigned.key;

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

# Test Nginx configuration
echo "🧪 Testing Nginx configuration..."
if nginx -t; then
    echo "✅ Nginx configuration is valid"
else
    echo "❌ Nginx configuration test failed!"
    echo "Restoring backup..."
    cp /etc/nginx/sites-available/streamlit.backup.* /etc/nginx/sites-available/streamlit
    exit 1
fi

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

# Update systemd service
echo "🔧 Updating systemd service..."
cat <<EOF | tee /etc/systemd/system/pain-narratives.service
[Unit]
Description=AINarratives Streamlit App
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

# Reload and restart services
echo "🔄 Reloading services..."
systemctl daemon-reload
systemctl reload nginx
systemctl restart pain-narratives.service

# Wait for service to start
echo "⏳ Waiting for application to restart..."
sleep 5

# Check service status
echo ""
echo "📊 Service Status:"
systemctl status pain-narratives.service --no-pager | head -15

echo ""
echo "✅ Quick fix applied successfully!"
echo ""
echo "🧪 Testing:"
echo "  1. Open your browser to: https://$DOMAIN"
echo "  2. Open browser DevTools (F12) -> Console tab"
echo "  3. Check for CSS preload errors (should be gone)"
echo "  4. Check Network tab -> Filter by 'css' -> Verify 200 status codes"
echo ""
echo "📋 Verify the fix:"
echo "  - Monitor Nginx logs:  sudo tail -f /var/log/nginx/streamlit-error.log"
echo "  - Monitor app logs:    sudo journalctl -u pain-narratives.service -f"
echo "  - Test static files:   curl -I https://$DOMAIN/static/"
echo ""
echo "🔙 Rollback if needed:"
echo "  sudo cp /etc/nginx/sites-available/streamlit.backup.* /etc/nginx/sites-available/streamlit"
echo "  sudo cp /etc/systemd/system/pain-narratives.service.backup.* /etc/systemd/system/pain-narratives.service"
echo "  sudo systemctl daemon-reload && sudo systemctl reload nginx && sudo systemctl restart pain-narratives.service"
echo ""

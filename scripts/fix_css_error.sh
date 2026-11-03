#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' 'This legacy nginx/uv installer has been retired.' 'Use docs/deployment.md and deploy/docker-compose.prod.yml for Docker/Caddy deployment.' >&2
exit 2

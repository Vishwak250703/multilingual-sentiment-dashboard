#!/bin/bash
# init-letsencrypt.sh
# Obtains an initial Let's Encrypt certificate for your domain.
# Run ONCE on a fresh server AFTER pointing your DNS A record to this server.
#
# Usage:
#   chmod +x scripts/init-letsencrypt.sh
#   ./scripts/init-letsencrypt.sh yourdomain.com you@example.com
#
# What it does:
#   1. Starts nginx with a temporary self-signed cert so it can serve ACME challenges
#   2. Runs certbot in webroot mode to obtain real Let's Encrypt certs
#   3. Reloads nginx to pick up the real certs
#   4. After this, certbot in docker-compose renews automatically every 12h

set -euo pipefail

DOMAIN="${1:?Usage: $0 <domain> <email>}"
EMAIL="${2:?Usage: $0 <domain> <email>}"
COMPOSE="docker compose -f docker-compose.prod.yml"

echo ""
echo "========================================="
echo " Let's Encrypt Init — $DOMAIN"
echo "========================================="
echo ""

# ── 1. Create dummy cert so nginx can start without a real cert ──
echo "[1/5] Creating temporary self-signed certificate..."
mkdir -p ./docker_volumes/certbot/conf/live/"$DOMAIN"
docker run --rm --entrypoint openssl \
  -v "$(pwd)/docker_volumes/certbot/conf:/etc/letsencrypt" \
  certbot/certbot \
  req -x509 -nodes -newkey rsa:4096 -days 1 \
  -keyout /etc/letsencrypt/live/"$DOMAIN"/privkey.pem \
  -out /etc/letsencrypt/live/"$DOMAIN"/fullchain.pem \
  -subj "/CN=localhost" 2>/dev/null

# ── 2. Download recommended TLS parameters ───────────────────────
echo "[2/5] Downloading recommended TLS params..."
DHPARAM_PATH="./docker_volumes/certbot/conf/ssl-dhparams.pem"
if [ ! -f "$DHPARAM_PATH" ]; then
  curl -s https://raw.githubusercontent.com/certbot/certbot/master/certbot-nginx/certbot_nginx/_internal/tls_configs/options-ssl-nginx.conf \
    -o ./docker_volumes/certbot/conf/options-ssl-nginx.conf
  curl -s https://raw.githubusercontent.com/certbot/certbot/master/certbot/certbot/ssl-dhparams.pem \
    -o "$DHPARAM_PATH"
fi

# ── 3. Patch nginx.ssl.conf with the real domain ─────────────────
echo "[3/5] Patching nginx.ssl.conf with domain $DOMAIN..."
sed -i "s/YOUR_DOMAIN_HERE/$DOMAIN/g" nginx/nginx.ssl.conf

# ── 4. Start nginx (it can now boot with the dummy cert) ─────────
echo "[4/5] Starting nginx..."
$COMPOSE up -d nginx

# Small wait for nginx to be ready
sleep 3

# ── 5. Obtain real certificate ───────────────────────────────────
echo "[5/5] Requesting certificate from Let's Encrypt..."
$COMPOSE run --rm certbot certonly \
  --webroot \
  --webroot-path=/var/www/certbot \
  --email "$EMAIL" \
  --agree-tos \
  --no-eff-email \
  -d "$DOMAIN"

# Reload nginx to use real cert
echo "Reloading nginx..."
$COMPOSE exec nginx nginx -s reload

echo ""
echo "========================================="
echo " Done! Certificate obtained for $DOMAIN"
echo " Certbot will auto-renew every 12 hours."
echo "========================================="
echo ""
echo "Next steps:"
echo "  1. Start all remaining services:  make prod-up"
echo "  2. Verify HTTPS:  curl -I https://$DOMAIN/health"

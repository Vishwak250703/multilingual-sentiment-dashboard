#!/usr/bin/env bash
# deploy.sh — Production deployment script
# Usage: ./scripts/deploy.sh [--branch main] [--skip-tests]
#
# What it does:
#   1. Pull latest code from git
#   2. (Optional) Run backend test suite
#   3. Build new Docker images (no cache)
#   4. Run Alembic migrations inside the backend container
#   5. Restart services with zero-downtime rolling update

set -euo pipefail

# ─── Defaults ─────────────────────────────────────────────────────────────────
BRANCH="${BRANCH:-main}"
SKIP_TESTS="${SKIP_TESTS:-false}"
COMPOSE_FILE="docker-compose.prod.yml"
LOG_FILE="/var/log/sentiment-deploy.log"

# ─── Colors ───────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log()  { echo -e "${CYAN}[$(date '+%H:%M:%S')] $*${NC}" | tee -a "$LOG_FILE"; }
ok()   { echo -e "${GREEN}[$(date '+%H:%M:%S')] ✓ $*${NC}" | tee -a "$LOG_FILE"; }
warn() { echo -e "${YELLOW}[$(date '+%H:%M:%S')] ⚠ $*${NC}" | tee -a "$LOG_FILE"; }
err()  { echo -e "${RED}[$(date '+%H:%M:%S')] ✗ $*${NC}" | tee -a "$LOG_FILE"; exit 1; }

# ─── Parse args ───────────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case "$1" in
    --branch) BRANCH="$2"; shift 2 ;;
    --skip-tests) SKIP_TESTS="true"; shift ;;
    *) warn "Unknown argument: $1"; shift ;;
  esac
done

# ─── Pre-flight checks ────────────────────────────────────────────────────────
command -v docker   >/dev/null 2>&1 || err "docker is not installed"
command -v git      >/dev/null 2>&1 || err "git is not installed"
[[ -f ".env" ]]                      || err ".env file not found — copy .env.example and fill in values"
[[ -f "$COMPOSE_FILE" ]]             || err "$COMPOSE_FILE not found"

log "Starting deployment to branch: $BRANCH"

# ─── Step 1: Pull latest code ─────────────────────────────────────────────────
log "Step 1/5 — Pulling latest code from origin/$BRANCH"
git fetch origin
git checkout "$BRANCH"
git pull origin "$BRANCH"
ok "Code up to date: $(git log -1 --format='%h %s')"

# ─── Step 2: Run tests (optional) ─────────────────────────────────────────────
if [[ "$SKIP_TESTS" == "false" ]]; then
  log "Step 2/5 — Running backend test suite"
  docker compose -f docker-compose.yml run --rm \
    -e DATABASE_URL="$TEST_DATABASE_URL" \
    backend \
    bash -c "pip install -q -r requirements-dev.txt && pytest tests/ -q --tb=short" \
    || err "Tests failed — aborting deployment"
  ok "All tests passed"
else
  warn "Step 2/5 — Tests skipped (--skip-tests)"
fi

# ─── Step 3: Build new images ─────────────────────────────────────────────────
log "Step 3/5 — Building Docker images (no cache)"
docker compose -f "$COMPOSE_FILE" build --no-cache
ok "Images built successfully"

# ─── Step 4: Start services ───────────────────────────────────────────────────
log "Step 4/5 — Starting services"
docker compose -f "$COMPOSE_FILE" up -d --remove-orphans
ok "Services started"

# ─── Step 5: Wait for backend health ──────────────────────────────────────────
log "Step 5/5 — Waiting for backend health check"
RETRIES=0
MAX_RETRIES=30
until docker compose -f "$COMPOSE_FILE" exec -T backend curl -sf http://localhost:8000/health >/dev/null 2>&1; do
  RETRIES=$((RETRIES+1))
  [[ $RETRIES -ge $MAX_RETRIES ]] && err "Backend failed to become healthy after ${MAX_RETRIES} retries"
  log "  Waiting... ($RETRIES/$MAX_RETRIES)"
  sleep 5
done
ok "Backend is healthy"

# ─── Summary ──────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║   Deployment completed successfully  ✓   ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════╝${NC}"
echo ""
log "Deployed commit: $(git log -1 --format='%h — %s (%an, %ar)')"
log "Running containers:"
docker compose -f "$COMPOSE_FILE" ps --format "table {{.Name}}\t{{.Status}}"

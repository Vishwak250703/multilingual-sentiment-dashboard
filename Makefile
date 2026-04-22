# Multilingual Sentiment Dashboard — Developer shortcuts

.PHONY: up down build logs shell-backend shell-db migrate seed seed-demo restart clean \
        prod-up prod-down prod-build prod-logs prod-shell status \
        test test-cov test-watch ssl-init deploy

## Start all services
up:
	docker-compose up -d

## Start with logs streaming
up-logs:
	docker-compose up

## Stop all services
down:
	docker-compose down

## Rebuild images (use after code changes to backend/frontend)
build:
	docker-compose build --no-cache

## Rebuild and restart
rebuild: down build up

## Stream logs (all services)
logs:
	docker-compose logs -f

## Backend logs only
logs-backend:
	docker-compose logs -f backend

## Worker logs only
logs-worker:
	docker-compose logs -f worker

## Shell into backend container
shell-backend:
	docker-compose exec backend bash

## Shell into postgres
shell-db:
	docker-compose exec postgres psql -U sentimentuser -d sentimentdb

## Run Alembic migrations manually
migrate:
	docker-compose exec backend alembic upgrade head

## Seed admin user manually
seed:
	docker-compose exec backend python -m app.scripts.seed_admin

## Seed 150 demo reviews (run once after first boot)
seed-demo:
	docker-compose exec backend python -m app.scripts.seed_demo_data

## Restart only the backend
restart-backend:
	docker-compose restart backend

## Remove all volumes (DANGER: deletes all data)
clean:
	docker-compose down -v

## Show service status
status:
	docker-compose ps

# ─── Production targets ───────────────────────────────────────

## Start production services (build images, detached)
prod-up:
	docker-compose -f docker-compose.prod.yml up -d --build

## Stop production services
prod-down:
	docker-compose -f docker-compose.prod.yml down

## Rebuild production images (no cache)
prod-build:
	docker-compose -f docker-compose.prod.yml build --no-cache

## Stream production logs
prod-logs:
	docker-compose -f docker-compose.prod.yml logs -f

## Shell into production backend container
prod-shell:
	docker-compose -f docker-compose.prod.yml exec backend bash

## Show production container status
prod-status:
	docker-compose -f docker-compose.prod.yml ps

# ─── Testing ──────────────────────────────────────────────────

## Run backend test suite (requires sentimentdb_test to exist)
test:
	docker-compose run --rm \
	  -e TEST_DATABASE_URL=postgresql+asyncpg://sentimentuser:sentimentpass@postgres:5432/sentimentdb_test \
	  backend bash -c "pip install -q -r requirements-dev.txt && pytest tests/ -v --tb=short"

## Run tests with coverage report
test-cov:
	docker-compose run --rm \
	  -e TEST_DATABASE_URL=postgresql+asyncpg://sentimentuser:sentimentpass@postgres:5432/sentimentdb_test \
	  backend bash -c "pip install -q -r requirements-dev.txt && pytest tests/ --cov=app --cov-report=term-missing -v"

## Run tests locally (outside Docker — requires local venv with dev deps)
test-local:
	cd backend && pytest tests/ -v --tb=short

## Run tests locally with coverage
test-cov-local:
	cd backend && pytest tests/ --cov=app --cov-report=term-missing --cov-report=html:htmlcov -v

# ─── SSL ──────────────────────────────────────────────────────

## Initialize Let's Encrypt certificates (first-time setup)
## Usage: make ssl-init DOMAIN=yourdomain.com EMAIL=admin@yourdomain.com
ssl-init:
	@[[ -n "$(DOMAIN)" ]] || (echo "ERROR: DOMAIN is required  →  make ssl-init DOMAIN=example.com EMAIL=admin@example.com" && exit 1)
	@[[ -n "$(EMAIL)" ]]  || (echo "ERROR: EMAIL is required   →  make ssl-init DOMAIN=example.com EMAIL=admin@example.com" && exit 1)
	DOMAIN=$(DOMAIN) EMAIL=$(EMAIL) bash scripts/init-letsencrypt.sh

# ─── Deploy ───────────────────────────────────────────────────

## Deploy latest code to production (runs on server)
## Usage: make deploy  (from the server, or via SSH)
deploy:
	bash scripts/deploy.sh

## Deploy without running tests
deploy-fast:
	SKIP_TESTS=true bash scripts/deploy.sh

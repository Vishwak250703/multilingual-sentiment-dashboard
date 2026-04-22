# 🌐 Multilingual Sentiment Dashboard

> A production-grade, multi-tenant SaaS platform that ingests customer reviews in any language, runs a full NLP pipeline (detect → translate → analyse → embed), and surfaces actionable sentiment intelligence through a real-time dashboard — with an AI chat interface powered by Claude + RAG.

Built as a portfolio project to demonstrate production-ready Gen AI engineering skills including async pipelines, multi-tenant architecture, vector search, LLM integration, WebSocket streaming, and full-stack deployment.

---

## 🎯 Problem Statement

Businesses operating across multiple markets receive customer feedback in dozens of languages — app store reviews in German, support tickets in Arabic, social comments in French. Manually reading and categorising this feedback at scale is impossible.

**Multilingual Sentiment Dashboard** lets teams upload any CSV of reviews (or stream them via API), and within seconds every review is language-detected, translated, sentiment-scored, aspect-tagged, and keyword-extracted — surfaced in a live dashboard that answers the question *"how do customers feel, right now, and why?"*

---

## 🏗️ Architecture

```
Browser
      │
      ▼
┌─────────────────────┐
│   Nginx :80 / :443  │   ← Reverse proxy + SSL termination
└──────────┬──────────┘
           │
     ┌─────┴──────┐
     ▼            ▼
┌─────────┐  ┌──────────────────────────────────────┐
│  React  │  │         FastAPI :8000                │
│  SPA    │  │  Auth · Reviews · Dashboard · Chat   │
│ (Vite)  │  │  Alerts · Insights · Admin · Ingest  │
└─────────┘  └──────────────┬───────────────────────┘
                            │
              ┌─────────────┼─────────────┐
              ▼             ▼             ▼
         ┌─────────┐  ┌─────────┐  ┌──────────────┐
         │  Redis  │  │Postgres │  │   ChromaDB   │
         │ pub/sub │  │   15    │  │ Vector Store │
         └────┬────┘  └─────────┘  └──────────────┘
              │
    ┌─────────┴────────────┐
    ▼                      ▼
┌──────────────┐   ┌──────────────┐
│ Celery Worker│   │ Celery Beat  │
│  NLP · Embed │   │ Alert Checks │
│  per-review  │   │  every 5 min │
└──────────────┘   └──────────────┘
```

**Flow:**
1. Review arrives via CSV upload or webhook POST
2. Celery worker detects language, translates to English, runs Claude sentiment analysis
3. Aspect extraction + keyword tagging stored in PostgreSQL
4. Sentence-transformer embeds the review into ChromaDB for semantic search
5. Dashboard aggregations are served directly from PostgreSQL via async SQLAlchemy
6. Chat Q&A retrieves the top-k similar reviews from ChromaDB and sends them to Claude with the user's question
7. WebSocket (Redis pub/sub) pushes live events (job progress, new alerts, dashboard updates) to all connected browsers

---

## 🛠️ Tech Stack

| Component | Technology | Why |
|---|---|---|
| Language | Python 3.11 | Best ecosystem for async + AI/ML |
| API Framework | FastAPI + Uvicorn | Async-first, auto OpenAPI docs, fast |
| LLM | Claude Opus 4 via Anthropic API | Best-in-class reasoning for nuanced sentiment |
| Embeddings | sentence-transformers (MiniLM-L12-v2) | Multilingual, runs locally, no API cost |
| Vector DB | ChromaDB | Local persistent store, no infra cost |
| Translation | deep-translator (Google Translate) | 100+ languages, free tier sufficient |
| Language Detection | langdetect | Lightweight, works offline |
| Task Queue | Celery 5 + Redis | Async NLP without blocking the API |
| Database | PostgreSQL 15 + SQLAlchemy 2 async | ACID guarantees for multi-tenant data |
| Cache / Pub-Sub | Redis 7 | WebSocket fan-out + Celery broker |
| Migrations | Alembic | Safe schema evolution |
| Frontend | React 18 + TypeScript + Vite | Type-safe, fast HMR during dev |
| State | TanStack Query v5 + Zustand | Server cache + lightweight client state |
| Charts | Recharts | Composable, React-native charts |
| Styling | Tailwind CSS | Glassmorphism design system |
| Animations | Framer Motion | Smooth transitions for data updates |
| Email Alerts | smtplib (stdlib) | Zero dependencies, STARTTLS |
| Slack Alerts | requests + Block Kit | Rich formatted alert cards |
| PDF Export | reportlab | Server-side PDF, no headless browser |
| Reverse Proxy | Nginx | Static serving + WebSocket upgrade |
| SSL | Let's Encrypt + Certbot | Free, auto-renewing certificates |
| Containers | Docker + Docker Compose | Dev/prod parity |
| CI / CD | GitHub Actions | Test on PR, deploy on main |

---

## 📁 Project Structure

```
multilingual-sentiment-dashboard/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── routes/
│   │   │   │   ├── auth.py          # Login, refresh, logout, /me
│   │   │   │   ├── reviews.py       # CRUD, CSV export, PDF export
│   │   │   │   ├── dashboard.py     # KPIs, trend, language/source charts
│   │   │   │   ├── alerts.py        # List + resolve alerts
│   │   │   │   ├── insights.py      # AI-generated insights + aspects
│   │   │   │   ├── chat.py          # RAG Q&A with Claude
│   │   │   │   ├── ingest.py        # CSV upload + webhook
│   │   │   │   └── admin.py         # User CRUD + audit logs
│   │   │   └── websocket.py         # Real-time event stream
│   │   ├── core/
│   │   │   ├── config.py            # Pydantic settings (env-driven)
│   │   │   ├── database.py          # Async SQLAlchemy engine
│   │   │   ├── auth.py              # JWT + RBAC helpers
│   │   │   └── redis.py             # Redis client + pub/sub
│   │   ├── models/                  # SQLAlchemy ORM models
│   │   │   ├── tenant.py
│   │   │   ├── user.py
│   │   │   ├── review.py
│   │   │   ├── alert.py
│   │   │   ├── audit_log.py
│   │   │   └── human_review.py
│   │   ├── schemas/                 # Pydantic request/response schemas
│   │   ├── services/
│   │   │   ├── nlp/                 # Language detect, translate, sentiment, embed
│   │   │   ├── chat/                # RAG pipeline (ChromaDB + Claude)
│   │   │   └── notifications/       # Email + Slack alert services
│   │   ├── tasks/                   # Celery tasks
│   │   │   ├── celery_app.py
│   │   │   ├── process_review.py    # Full NLP pipeline per review
│   │   │   └── run_alerts.py        # Scheduled alert checker
│   │   └── scripts/
│   │       ├── seed_admin.py        # Creates first admin user
│   │       └── seed_demo_data.py    # 150 multilingual demo reviews
│   ├── alembic/                     # Database migration files
│   ├── tests/
│   │   ├── conftest.py              # Fixtures: DB, client, users, tokens
│   │   ├── test_auth.py             # Login, /me, refresh, logout
│   │   ├── test_reviews.py          # List, filter, export, RBAC
│   │   ├── test_dashboard.py        # KPIs, trend, tenant isolation
│   │   ├── test_alerts.py           # List + resolve alerts
│   │   └── test_admin.py            # User CRUD + audit logs
│   ├── requirements.txt
│   ├── requirements-dev.txt         # pytest, pytest-asyncio, pytest-cov
│   ├── pytest.ini
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── Dashboard.tsx        # KPI cards + charts overview
│   │   │   ├── Reviews.tsx          # Filterable table + CSV/PDF export
│   │   │   ├── Chat.tsx             # Full-page AI Q&A with suggestions
│   │   │   ├── Insights.tsx         # AI insight cards + aspect score bars
│   │   │   ├── Alerts.tsx           # Alert list + resolve
│   │   │   ├── Upload.tsx           # Drag-drop with live progress
│   │   │   ├── Admin.tsx            # User management
│   │   │   └── Login.tsx
│   │   ├── components/              # Shared UI components
│   │   ├── api/                     # Axios client + typed endpoints
│   │   ├── store/                   # Zustand global state
│   │   └── hooks/                   # useWebSocket, useDashboardStore
│   ├── Dockerfile
│   └── package.json
├── nginx/
│   ├── nginx.conf                   # Dev reverse proxy config
│   └── nginx.ssl.conf               # Production HTTPS config
├── scripts/
│   ├── deploy.sh                    # Production deploy (pull → build → migrate → up)
│   └── init-letsencrypt.sh          # First-run SSL certificate initialisation
├── .github/
│   └── workflows/
│       └── ci.yml                   # Test → Build → Deploy pipeline
├── docker-compose.yml               # Development (hot-reload, ports exposed)
├── docker-compose.prod.yml          # Production (no mounts, restart: always, certbot)
├── Makefile                         # Developer shortcuts
├── .env.example                     # Template for all environment variables
└── README.md
```

---

## ⚡ Quickstart

### Prerequisites
- Docker + Docker Compose
- An Anthropic API key ([console.anthropic.com](https://console.anthropic.com))

### 1. Clone and configure

```bash
git clone https://github.com/Vishwak250703/multilingual-sentiment-dashboard.git
cd multilingual-sentiment-dashboard
cp .env.example .env
```

Edit `.env` and set at minimum:
```env
ANTHROPIC_API_KEY=sk-ant-...
SECRET_KEY=<run: python3 -c "import secrets; print(secrets.token_hex(32))">
```

### 2. Start all services

```bash
docker compose up -d
# or: make up
```

On first boot the backend runs Alembic migrations and seeds the admin user automatically (~30s).

### 3. Seed demo data (recommended)

```bash
docker compose exec backend python -m app.scripts.seed_demo_data
# or: make seed-demo
```

Inserts ~150 pre-analysed reviews across 6 languages so the dashboard has real data to visualise immediately.

### 4. Open the app

| URL | Service |
|---|---|
| http://localhost | Dashboard (via nginx) |
| http://localhost:8000/docs | FastAPI Swagger UI |
| http://localhost:8000/redoc | FastAPI ReDoc |

**Default credentials:**
- Email: `admin@sentiment.ai`
- Password: `Admin@123456`

> Change the password immediately after first login via **Admin → Users**.

---

## 📸 Screenshots

### Dashboard — Live KPI cards and sentiment trend
![Dashboard](screenshots/01_dashboard.png)

### Reviews — Filterable table with CSV and PDF export
![Reviews](screenshots/02_reviews.png)

### Chat with Data — Ask questions, get AI answers with inline charts
![Chat](screenshots/03_chat.png)

### AI Insights — Spike detection and aspect sentiment bars
![Insights](screenshots/04_insights.png)

### Upload — Drag-drop CSV with real-time progress
![Upload](screenshots/05_upload.png)

### Alerts — Sentiment drop and complaint spike notifications
![Alerts](screenshots/06_alerts.png)

---

## 💬 Sample Prompts to Try in Chat

```
Which product has the most complaints this month?
Compare sentiment between English and German reviews.
What are customers saying about delivery times?
Show me the top 5 negative keywords from last week.
What percentage of reviews mention price as an issue?
Summarise the main themes from negative reviews.
```

---

## 🤖 How RAG Powers "Chat with Data"

Traditional LLMs can only answer from training data — they know nothing about *your* customers' reviews. 

**The Chat feature solves this with a three-step RAG pipeline:**

1. **Retrieval** — The user's question is encoded into a 384-dimensional vector. ChromaDB performs a cosine similarity search across all embedded reviews for this tenant, returning the top-k most semantically relevant ones.

2. **Augmentation** — The retrieved reviews are formatted as grounded context and injected into the Claude prompt alongside the conversation history. Claude is explicitly instructed to answer *only* from this context, not from prior knowledge.

3. **Generation** — Claude synthesises a natural-language answer, cites specific reviews, and where appropriate returns structured chart data for inline visualisation.

This means every answer is grounded in actual customer feedback, with supporting review excerpts the user can inspect — not hallucinated generalisations.

---

## ⚙️ Key Design Decisions

**Why multi-tenant from day one?**
Real SaaS products serve multiple companies from one deployment. Tenant isolation is enforced at every query (`WHERE tenant_id = :current_tenant`) so one organisation's data can never appear in another's dashboard, even under misconfiguration.

**Why Celery for NLP, not async FastAPI tasks?**
Claude API calls and sentence-transformer inference can take 2–8 seconds per review. Running them in an async endpoint would hold HTTP connections open and starve the event loop. Celery offloads them to worker processes — the API returns immediately with a job ID, and the browser polls via WebSocket events.

**Why WebSocket over polling?**
Upload progress updates every 5 rows. At 1,000 rows that's 200 events. HTTP polling at 1s intervals would mean 200 wasted round-trips from every connected browser. WebSocket keeps one persistent connection and pushes events only when something changes.

**Why ChromaDB over Pinecone/Weaviate?**
For a self-hosted deployment, local ChromaDB eliminates a third-party API dependency, reduces latency, and keeps customer data on-premise — important for enterprise buyers. The trade-off is that ChromaDB doesn't scale horizontally, but that's acceptable for single-tenant or small SaaS deployments.

**Why per-test DB rollback instead of truncation?**
Rolling back a transaction is an order of magnitude faster than truncating tables and re-seeding. With 50+ tests across 5 test files, this makes the full test suite run in seconds rather than minutes.

**Why Claude for sentiment over a fine-tuned model?**
Aspect-based sentiment on short, multilingual, domain-specific text is genuinely hard. Fine-tuned models (e.g. cardiffnlp/twitter-roberta) perform well on simple positive/negative but struggle with nuance ("delivery was fast but packaging was damaged"). Claude's reasoning produces richer aspect breakdowns and more defensible scores.

---

## 🌍 CSV Format Guide

The ingestion pipeline auto-detects column names. Supported aliases:

| Data | Accepted column names |
|---|---|
| Review text | `text`, `review`, `comment`, `body`, `content`, `feedback`, `message` |
| Date | `date`, `created_at`, `review_date`, `timestamp` |
| Product | `product`, `product_id`, `product_name`, `item`, `sku` |
| Branch / Store | `branch`, `branch_id`, `location`, `store`, `outlet` |
| Source | `source`, `channel`, `platform` |

**Minimal valid CSV:**
```csv
text
"Great product, fast shipping!"
"Terrible customer service, waited 3 days."
"Das Produkt ist ausgezeichnet, sehr empfehlenswert."
```

Supported formats: `.csv`, `.xls`, `.xlsx` — max 50 MB.

---

## 🔑 Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `SECRET_KEY` | ✅ | — | JWT signing key |
| `ANTHROPIC_API_KEY` | ✅ | — | Claude API key |
| `DATABASE_URL` | ✅ | — | Async PostgreSQL URL |
| `REDIS_URL` | | `redis://redis:6379/0` | Redis for pub/sub |
| `CELERY_BROKER_URL` | | `redis://redis:6379/1` | Celery broker |
| `CHROMA_HOST` | | `chromadb` | ChromaDB hostname |
| `CLAUDE_MODEL` | | `claude-opus-4-6` | Claude model ID |
| `ENVIRONMENT` | | `development` | `development` or `production` |
| `SMTP_HOST` | | — | SMTP server for email alerts |
| `SMTP_USER` | | — | SMTP username |
| `SMTP_PASSWORD` | | — | SMTP password / app password |
| `ALERT_EMAIL_RECIPIENTS` | | — | Comma-separated fallback alert emails |
| `SLACK_WEBHOOK_URL` | | — | Slack incoming webhook URL |
| `SENTIMENT_DROP_THRESHOLD` | | `0.2` | Fraction drop to trigger alert |
| `FIRST_ADMIN_EMAIL` | | `admin@sentiment.ai` | Auto-created admin email |
| `FIRST_ADMIN_PASSWORD` | | `Admin@123456` | Auto-created admin password |

---

## 🚀 Production Deployment

A full walkthrough is available in [scripts/deploy.sh](scripts/deploy.sh). Quick summary:

```bash
# 1. On your VPS — install Docker, clone repo, create .env
# 2. Initialise SSL (one time)
DOMAIN=yourdomain.com EMAIL=admin@yourdomain.com bash scripts/init-letsencrypt.sh

# 3. Start all services
docker compose -f docker-compose.prod.yml up -d

# 4. Verify
curl https://yourdomain.com/health
```

**GitHub Actions CI/CD** (`.github/workflows/ci.yml`) runs automatically on every push:
- Backend tests against a real Postgres service container
- Frontend type-check + production build
- Docker image smoke build (on `main` only)
- SSH deploy to your VPS after manual approval (requires `production` environment in GitHub settings)

---

## 👤 User Roles

| Role | View Reviews | Correct Sentiment | Resolve Alerts | Upload | Admin Panel |
|---|---|---|---|---|---|
| `viewer` | ✅ | ❌ | ✅ | ❌ | ❌ |
| `analyst` | ✅ | ✅ | ✅ | ✅ | ❌ |
| `admin` | ✅ | ✅ | ✅ | ✅ | ✅ Full |

---

## ⚠️ Limitations

- Sentiment analysis quality depends on Claude API availability and quota
- ChromaDB is single-node — not suitable for horizontal scaling without migration to Pinecone/Qdrant
- Translation uses Google Translate free tier — rate-limited for very large CSV files (10,000+ rows)
- PDF export renders up to 500 reviews per download
- No SSO / OAuth — only email + password authentication
- WebSocket connections are per-instance; multi-replica deployments require a Redis-backed message bus (already in place) but sticky sessions on the load balancer

---

## 🔮 Future Work

- [ ] OAuth 2.0 / SAML SSO for enterprise login
- [ ] Horizontal scaling — swap ChromaDB for Qdrant with gRPC
- [ ] Mobile app (React Native) with push notifications
- [ ] RAGAS-based evaluation pipeline to measure RAG answer quality
- [ ] Fine-tuned open-source sentiment model to reduce Claude API cost at scale
- [ ] Multi-language dashboard UI (i18n)
- [ ] Scheduled email digests (weekly sentiment summary per tenant)
- [ ] Anomaly detection using time-series ML (Prophet / LSTM)

---

## 👨‍💻 Author

**Vishwak Narayana**
BTech Graduate | MSc Big Data & AI (SRH Berlin, incoming)
Building a production Gen AI portfolio before starting my Masters in Germany.

- GitHub: [@Vishwak250703](https://github.com/Vishwak250703)
- Email: vishwak.thandra@gmail.com

---

## 📄 License

MIT License — free to use and modify.

# Carval.ai — AI-Powered Used Car Price Prediction

End-to-end web application that estimates the market value of second-hand cars
in Turkey. Users upload car photos plus a few inputs (year, mileage, fuel,
transmission, engine size, optional damage notes); the system identifies the
vehicle visually, retrieves comparable listings, and produces a numeric price
range together with a Turkish natural-language analysis.

This is a graduation project for **Konya Food and Agriculture University —
Computer Engineering Department (COMP-4901)**.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 19 (Vite), React Router, Axios, lucide-react, react-hot-toast |
| Backend | FastAPI, SQLAlchemy 2, Alembic |
| Database | PostgreSQL 16 with `pgvector` extension |
| Queue / cache | Redis 7 + Taskiq (background jobs) |
| ML / AI | Google Gemini 2.5 Flash (vision + narrative), scikit-learn `HistGradientBoostingRegressor`, sentence-transformers (MiniLM-L6-v2) for semantic retrieval |
| Scraper | httpx + BeautifulSoup, targets arabam.com |
| Infra | Docker Compose, Dokploy, Traefik, sslip.io for development domains |

---

## How the Valuation Engine Works

```
Photo + mileage + fuel + transmission + engine_size  ───┐
                                                        ▼
                    ┌──────────────────────────────────────┐
                    │  Gemini Vision (call #1)              │
                    │  → brand, model, body_type, color,    │
                    │    visible damages, condition score   │
                    └──────────────────────────────────────┘
                                       │
                                       ▼
            ┌────────────────────────────────────────────┐
            │  Retrieval (services/valuation/retrieval)   │
            │  — 5-layer SQL filter (year, mileage band,  │
            │    fuel, transmission, brand+model fallback)│
            │  — MAD-based outlier rejection              │
            │  — pgvector semantic fallback if <10 hits   │
            └────────────────────────────────────────────┘
                                       │
                                       ▼
            ┌────────────────────────────────────────────┐
            │  Statistical baseline (baseline.py)         │
            │  Mileage-adjusted linear regression on      │
            │  comparable listings; median fallback.      │
            └────────────────────────────────────────────┘
                                       │
                                       ▼
            ┌────────────────────────────────────────────┐
            │  ML model (ml_model.py)                     │
            │  HistGradientBoosting on log(price)         │
            │  features: year, mileage, engine_power_hp,  │
            │  brand, model, fuel, transmission, body     │
            │  Per-(brand,model) ±3σ outlier filter.      │
            │  R² ≈ 0.958, MAE ≈ 85 k TL on ~7 k rows.    │
            └────────────────────────────────────────────┘
                                       │
                                       ▼
            ┌────────────────────────────────────────────┐
            │  Blender (pipeline.py)                      │
            │  weighted(ml=0.6, stats=0.4) · condition    │
            │  multiplier from visual score (±10%).       │
            └────────────────────────────────────────────┘
                                       │
                                       ▼
            ┌────────────────────────────────────────────┐
            │  Gemini narrative (call #2, llm.py)         │
            │  Asked only to justify the already-          │
            │  computed price in 3-5 Turkish sentences.   │
            └────────────────────────────────────────────┘
                                       │
                                       ▼
                       { predicted_price, price_min, price_max,
                         condition_score, analysis, sources }
```

The LLM never invents the price. The number is purely numeric (ML +
statistical baseline blended), so two identical inputs always yield the same
output. Gemini is responsible only for vision and the human-readable
explanation.

---

## Repository Layout

```
.
├── backend/
│   ├── app/
│   │   ├── api/              # FastAPI routers (auth, valuation, admin, subscription, scraper)
│   │   ├── core/             # config, database, security, broker, deps
│   │   ├── models/           # SQLAlchemy ORM (User, Subscription, Valuation, ScrapedCar...)
│   │   ├── schemas/          # Pydantic request/response models
│   │   ├── scraper/          # arabam.com scraper
│   │   ├── services/
│   │   │   ├── gemini_service.py        # Gemini vision call
│   │   │   ├── subscription_service.py  # tier / usage logic
│   │   │   ├── anon_quota.py            # Redis-backed anonymous trial limit
│   │   │   └── valuation/               # the engine (this turn's refactor)
│   │   │       ├── retrieval.py
│   │   │       ├── baseline.py
│   │   │       ├── ml_model.py
│   │   │       ├── embedding.py
│   │   │       ├── llm.py
│   │   │       ├── pipeline.py
│   │   │       └── schemas.py
│   │   └── tasks/            # Taskiq background tasks (scrape, train, embed-backfill)
│   ├── alembic/              # migrations
│   ├── models_bundled/       # committed ML model (.pkl) used as initial deploy seed
│   └── Dockerfile            # multi-stage: builds frontend, serves dist from FastAPI
├── frontend/
│   └── src/
│       ├── api/              # axios clients per resource
│       ├── pages/            # Landing, Login, Register, Dashboard, Valuation, Admin
│       ├── components/       # Navbar, AiThinking, ValuationResult, admin/*
│       ├── context/          # AuthContext
│       ├── hooks/            # usePollingStatus
│       └── lib/              # error helpers
├── docker-compose.yml        # production-ready (Dokploy)
├── docker-compose.dev.yml    # local development (host port bindings, bind mounts, dev secrets)
└── .env                      # POSTGRES_*, SECRET_KEY, GEMINI_API_KEY, …
```

---

## Local Development

### Prerequisites

- Docker Desktop
- A Gemini API key from [https://aistudio.google.com/apikey](https://aistudio.google.com/apikey)

### `.env`

Create `.env` in the repo root:

```ini
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=car_valuation

SECRET_KEY=<a strong random string>
REFRESH_SECRET_KEY=<another strong random string>
GEMINI_API_KEY=AIzaSy...
```

### Run

```powershell
docker compose -f docker-compose.dev.yml up -d --build
```

This starts six services: `db`, `redis`, `backend`, `taskiq-worker`,
`taskiq-scheduler`. Frontend is built into the backend image and served at the
same origin.

| Service | URL |
|---|---|
| App (frontend + API) | http://localhost:8000 |
| API docs | http://localhost:8000/docs |
| Postgres | localhost:5434 |
| Redis | localhost:6379 |

Alembic migrations run automatically on backend startup.

### Frontend hot reload

For HMR during development, run Vite separately while the backend stack is up:

```powershell
npm --prefix frontend run dev
```

Vite proxies `/api/*` to `http://localhost:8000`, so cookies and CORS work
transparently. The dev server runs at http://localhost:5173.

---

## Admin Operations

A user must be promoted manually via SQL (no UI for it on purpose):

```sql
UPDATE users SET is_admin = true WHERE email = 'you@example.com';
```

After re-login, the navbar shows **Admin**. From the panel:

| Action | What it does |
|---|---|
| **Scrape Başlat** | Background job: ~500 listings per (brand, model) pair from `TOP_MODELS` (50 pairs). |
| **Embedding Üret** | Computes sentence-transformer vectors for every scraped car. Required for semantic retrieval fallback. |
| **Eğitimi Başlat** | Trains the HGB price model on current `scraped_cars`, writes to the `models` volume, hot-reloads. |

The trained `.pkl` can be promoted to `backend/models_bundled/` and committed
so a fresh deploy starts with a working model.

---

## Deployment (Dokploy)

The production `docker-compose.yml` is Dokploy-ready: no host port bindings,
all secrets required from the environment, restart policies, named volumes for
`pgdata`, `redisdata`, and `models`.

1. Create a **Compose** service in Dokploy and connect this repo (branch
   `main`, compose path `./docker-compose.yml`).
2. Fill **Environment** with `POSTGRES_USER/PASSWORD/DB`, `SECRET_KEY`,
   `REFRESH_SECRET_KEY`, `GEMINI_API_KEY`, `CORS_ORIGINS`.
3. Add a domain pointing to service `backend`, container port `8000`, HTTPS
   on. The backend serves both the SPA and the API on the same origin, so no
   separate frontend domain is needed.
4. Deploy. Backend's startup command runs `alembic upgrade head` before
   starting Uvicorn, so the schema always lands first.

---

## Pricing & Quota Model

| Tier | Trial limit | Mechanism |
|---|---|---|
| Anonymous | 3 valuations total | Redis key keyed by `X-Client-Id` (browser-generated UUID) with IP-hash fallback, 30-day TTL |
| Free (registered) | 10 valuations / month | `valuation_usage` table (one row per user / period) |
| Pro | Unlimited | `subscriptions.tier = 'pro'` with optional `expires_at`. Test-mode `POST /api/v1/subscription/upgrade` skips payment. |

---

## License

Educational project, no formal license.

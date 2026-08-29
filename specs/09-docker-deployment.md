# Spec 09: Docker Deployment

**Version**: 1.0
**Date**: 29 Agustus 2026
**Related PRD**: Section 7 (Reliabilitas Demo)

---

## Tujuan

Mengemas seluruh komponen AI Guard ke dalam container Docker dan mengorkestrasinya dengan Docker Compose agar dapat dijalankan secara konsisten selama presentasi demo.

---

## Komponen Container

| Service | Image | Port | Volume |
|---------|-------|------|--------|
| website | ai-guard/website | :5000 | - |
| inference-api | ai-guard/inference-api | :8000 | models/, data/ |
| dashboard | ai-guard/dashboard | :8080 | data/ |
| sqlite-db | postgres:15 (atau volume SQLite) | :5432 | db-data/ |
| telegram-notifier | ai-guard/notifier | - | - |

---

## Dockerfile per Service

### 1. Inference API

```dockerfile
# Dockerfile.inference-api
FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements-inference.txt .
RUN pip install --no-cache-dir -r requirements-inference.txt

# Copy source code
COPY src/ ./src/
COPY models/ ./models/

# Healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import requests; r = requests.get('http://localhost:8000/health'); exit(0 if r.status_code == 200 else 1)"

EXPOSE 8000

CMD ["gunicorn", "src.api.main:app", \
     "-w", "4", \
     "-k", "uvicorn.workers.GunicornUVicornWorker", \
     "--bind", "0.0.0.0:8000", \
     "--timeout", "120"]
```

### 2. Website (Prototipe)

```dockerfile
# Dockerfile.website
FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-website.txt .
RUN pip install --no-cache-dir -r requirements-website.txt

COPY src/ ./src/
COPY frontend/ ./frontend/

EXPOSE 5000

CMD ["gunicorn", "src.website:app", \
     "-w", "2", \
     "-k", "gthread", \
     "--bind", "0.0.0.0:5000"]
```

### 3. Dashboard

```dockerfile
# Dockerfile.dashboard
FROM nginx:alpine

COPY frontend/dashboard/ /usr/share/nginx/html/
COPY nginx-dashboard.conf /etc/nginx/conf.d/default.conf

EXPOSE 8080

CMD ["nginx", "-g", "daemon off;"]
```

### 4. Telegram Notifier

```dockerfile
# Dockerfile.notifier
FROM python:3.10-slim

WORKDIR /app

COPY requirements-notifier.txt .
RUN pip install --no-cache-dir -r requirements-notifier.txt

COPY src/ ./src/

CMD ["python", "-u", "src/notifier/run_notifier.py"]
```

---

## docker-compose.yml

```yaml
version: '3.8'

services:
  # Database
  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: ai_guard
      POSTGRES_USER: guard_user
      POSTGRES_PASSWORD: guard_pass
    volumes:
      - db-data:/var/lib/postgresql/data
      - ./database/init.sql:/docker-entrypoint-initdb.d/init.sql
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U guard_user"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Inference API
  inference-api:
    build:
      context: .
      dockerfile: Dockerfile.inference-api
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql://guard_user:guard_pass@db:5432/ai_guard
      MODEL_PATH: /app/models/xgboost_model.pkl
    depends_on:
      db:
        condition: service_healthy
    volumes:
      - models-data:/app/models
    restart: unless-stopped

  # Prototipe Website
  website:
    build:
      context: .
      dockerfile: Dockerfile.website
    ports:
      - "5000:5000"
    environment:
      DATABASE_URL: postgresql://guard_user:guard_pass@db:5432/ai_guard
      INFERENCE_API_URL: http://inference-api:8000/predict
      MIDDLEWARE_ENABLED: "true"
      BLOCK_THRESHOLD: "0.7"
    depends_on:
      - inference-api
    restart: unless-stopped

  # Dashboard
  dashboard:
    build:
      context: .
      dockerfile: Dockerfile.dashboard
    ports:
      - "8080:8080"
    environment:
      API_BASE_URL: http://inference-api:8000
      WEBSITE_API_URL: http://website:5000
    depends_on:
      - website
    restart: unless-stopped

  # Telegram Notifier
  notifier:
    build:
      context: .
      dockerfile: Dockerfile.notifier
    environment:
      DATABASE_URL: postgresql://guard_user:guard_pass@db:5432/ai_guard
      TELEGRAM_BOT_TOKEN: ${TELEGRAM_BOT_TOKEN:-}
      TELEGRAM_CHAT_ID: ${TELEGRAM_CHAT_ID:-}
      NOTIFICATION_ENABLED: "true"
    depends_on:
      - db
    restart: unless-stopped

volumes:
  db-data:
  models-data:

networks:
  default:
    name: ai-guard-network
```

---

## Environment Variables (.env)

```bash
# Create .env from .env.example
cp .env.example .env

# Database
DATABASE_URL=postgresql://guard_user:guard_pass@db:5432/ai_guard

# Telegram
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here

# Middleware
BLOCK_THRESHOLD=0.7
MIDDLEWARE_ENABLED=true
INFERENCE_TIMEOUT_MS=100

# Notification
NOTIFICATION_ENABLED=true
AGGREGATION_WINDOW_SEC=60
MAX_NOTIFICATIONS_PER_HOUR=20
```

---

## Build & Run Commands

### Setup

```bash
# Clone & setup
cd kompres

# Build all images
docker-compose build

# Or build specific service
docker-compose build inference-api

# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Restart a service
docker-compose restart website

# Stop all services
docker-compose down

# Stop and clean up volumes
docker-compose down -v
```

### Demo Mode (Quick Start)

```bash
#!/bin/bash
# scripts/demo-start.sh

echo "🚀 Starting AI Guard Demo Environment..."

# Set default values if not in .env
export TELEGRAM_BOT_TOKEN="${TELEGRAM_BOT_TOKEN:-}"
export TELEGRAM_CHAT_ID="${TELEGRAM_CHAT_ID:-}"

# Pull latest images
docker-compose pull

# Start services
docker-compose up -d

# Wait for services to be healthy
echo "⏳ Waiting for services to start..."
sleep 15

# Check status
docker-compose ps

echo ""
echo "✅ AI Guard is running!"
echo "   Website:    http://localhost:5000"
echo "   Dashboard:  http://localhost:8080"
echo "   Inference:  http://localhost:8000"
echo "   Health:     http://localhost:8000/health"
```

---

## Data Persistence

| Data | Location | Persisted? |
|------|----------|------------|
| SQLite DB / Postgres | `db-data/` volume | ✅ Yes |
| Models | `models-data/` volume | ✅ Yes |
| Logs | Docker logging driver | Temporary |
| Notification logs | In database | ✅ Yes |

---

## Pre-Demo Checklist

- [ ] `docker-compose up -d` berjalan tanpa error
- [ ] Semua container status `healthy`
- [ ] `/health` endpoint responsive
- [ ] Dashboard accessible di port 8080
- [ ] Model loaded (cek log inference-api)
- [ ] Database connected
- [ ] Telegram bot configured (optional untuk demo)
- [ ] Attack simulation tool dapat mengirim request
- [ ] Anomalous traffic muncul di dashboard
- [ ] Notifikasi terkirim jika Telegram configured

---

## Acceptance Criteria

- [ ] `docker-compose up -d` menjalankan semua 5 services
- [ ] Semua services dapat communicate antar-container via Docker network
- [ ] Model persisted di volume sehingga tidak perlu re-download
- [ ] Database data persisted di volume
- [ ] Healthcheck memastikan services ready sebelum dependents start
- [ ] `.env.example` tersedia dengan semua variabel yang diperlukan
- [ ] Demo start script (`scripts/demo-start.sh`) berjalan tanpa intervensi manual
- [ ] Log dapat di akses dengan `docker-compose logs -f`

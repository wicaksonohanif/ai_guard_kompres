# Spec 03: Inference API

**Version**: 1.1 (Updated for 32 features + shared parser from Spec 01)
**Date**: 31 Agustus 2026
**Related PRD**: FR-4

---

## Tujuan

Menyediakan REST API stateless menggunakan FastAPI untuk melakukan inferensi klasifikasi traffic HTTP secara real-time dengan latensi < 100ms per request.

---

## Endpoint

### POST /predict

Klasifikasi satu request HTTP tunggal.

**Request:**

```json
{
    "method": "POST",
    "url": "/search?q=test%27+OR+1%3D1--",
    "headers": {
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": "Mozilla/5.0",
        "Referer": ""
    },
    "body": "username=admin'%20OR%201%3D1--&password=anything"
}
```

**Response (200 OK):**

```json
{
    "label": "anomalous",
    "confidence": 0.97,
    "attack_class": "sql_injection",
    "features_used": 32,
    "processing_time_ms": 3.2
}
```

**Response untuk normal:**

```json
{
    "label": "normal",
    "confidence": 0.99,
    "attack_class": null,
    "features_used": 32,
    "processing_time_ms": 2.8
}
```

### POST /predict-batch

Klasifikasi multiple requests sekaligus.

**Request:**

```json
{
    "requests": [
        {
            "method": "GET",
            "url": "/home",
            "headers": {"User-Agent": "Mozilla/5.0"},
            "body": ""
        },
        {
            "method": "POST",
            "url": "/login",
            "headers": {"Content-Type": "application/x-www-form-urlencoded"},
            "body": "user=admin'+UNION+SELECT+*+FROM+users--"
        }
    ]
}
```

**Response (200 OK):**

```json
{
    "results": [
        {
            "index": 0,
            "label": "normal",
            "confidence": 0.98,
            "attack_class": null
        },
        {
            "index": 1,
            "label": "anomalous",
            "confidence": 0.95,
            "attack_class": "sql_injection"
        }
    ],
    "total_processed": 2
}
```

### GET /health

Health check endpoint.

**Response (200 OK):**

```json
{
    "status": "healthy",
    "model_loaded": true,
    "model_version": "1.0.0",
    "uptime_seconds": 3600
}
```

### GET /metrics

Model performance metrics summary.

**Response (200 OK):**

```json
{
    "accuracy": 0.965,
    "precision": 0.952,
    "recall": 0.941,
    "f1_score": 0.946,
    "total_predictions": 15420,
    "normal_count": 12300,
    "anomalous_count": 3120,
    "average_latency_ms": 3.5
}
```

---

## Implementasi

### Lokasi File

```
src/
├── api/
│   ├── __init__.py
│   ├── main.py              # FastAPI app entry point
│   ├── routes.py             # Endpoint definitions
│   ├── schemas.py            # Pydantic models for request/response
│   ├── dependencies.py       # Model loading dependency
│   └── middleware.py         # CORS, logging middleware
```

### Schemas (Pydantic)

```python
from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum

class HttpMethod(str, Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"

class SingleRequest(BaseModel):
    """Raw HTTP request input (same format as CSIC 2010 parsed structure)."""
    method: HttpMethod
    url: str
    headers: dict = {}
    body: str = ""

class PredictionResponse(BaseModel):
    label: str = Field(..., description="'normal' atau 'anomalous'")
    confidence: float = Field(..., ge=0.0, le=1.0)
    attack_class: Optional[str] = None
    features_used: int = 32
    processing_time_ms: float

class BatchRequest(BaseModel):
    requests: List[SingleRequest]

class BatchResponse(BaseModel):
    results: List[PredictionResponse]
    total_processed: int

class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    model_version: str
    uptime_seconds: float
```

### Main Application

```python
import time
import uvicorn
from fastapi import FastAPI, Depends, HTTPException
from contextlib import asynccontextmanager
import joblib
import json

from .routes import router
from .schemas import SingleRequest, PredictionResponse
from ..feature_extraction.parser import HTTPRequestParser
from ..feature_extraction.extractor import FeatureExtractor

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load model on startup."""
    # Load XGBoost model
    app.state.model = joblib.load("models/xgboost_model.pkl")
    
    # Load metadata
    with open("models/xgboost_metadata.json") as f:
        app.state.metadata = json.load(f)
    
    # Initialize feature extractor & parser (shared from Spec 01)
    app.state.feature_extractor = FeatureExtractor()
    app.state.http_parser = HTTPRequestParser()
    
    app.state.start_time = time.time()
    yield
    
    # Cleanup on shutdown
    app.state.model = None

app = FastAPI(
    title="AI Guard - Inference API",
    description="Real-time HTTP traffic classification service",
    version="1.0.0",
    lifespan=lifespan
)

app.include_router(router)

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "model_loaded": app.state.model is not None,
        "model_version": app.state.metadata.get("version", "unknown"),
        "uptime_seconds": time.time() - app.state.start_time
    }

@app.post("/predict", response_model=PredictionResponse)
async def predict(request: SingleRequest):
    start = time.time()
    
    # Parse raw HTTP request using shared parser (Spec 01)
    # Input already in structured format, so we pass directly to extractor
    parsed_request = {
        'method': request.method.value if hasattr(request.method, 'value') else request.method,
        'full_url': request.url,
        'url': request.url,
        'path': request.url.split('?')[0] if '?' in request.url else request.url,
        'query_string': request.url.split('?', 1)[1] if '?' in request.url else '',
        'query_params': {},
        'headers': {k.lower(): v for k, v in request.headers.items()},
        'body': request.body,
        'content_length': len(request.body)
    }
    
    # Extract 32 features using shared FeatureExtractor (Spec 01)
    features = app.state.feature_extractor.extract(parsed_request)
    
    # Predict
    prediction = app.state.model.predict([features])[0]
    probabilities = app.state.model.predict_proba([features])[0]
    
    confidence = max(probabilities)
    label = "anomalous" if prediction == 1 else "normal"
    
    processing_time = (time.time() - start) * 1000
    
    return PredictionResponse(
        label=label,
        confidence=round(confidence, 4),
        attack_class=None if label == "normal" else "sql_injection",  # Placeholder
        features_used=len(features),
        processing_time_ms=round(processing_time, 2)
    )
```

### Model Dependency

```python
from fastapi import HTTPException

async def get_app_state():
    """Dependency to ensure model is loaded."""
    from .main import app
    if app.state.model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    return app.state
```

---

## Performance Requirements

| Metric | Target |
|--------|--------|
| Latency p50 | < 5ms (feature extraction + inference) |
| Latency p99 | < 50ms |
| Throughput | >= 1000 req/s per instance |
| Memory footprint | < 200MB (model + overhead) |

---

## Deployment

```bash
# Development
uvicorn src.api.main:app --reload --port 8000

# Production
gunicorn api.main:app \
    -w 4 \
    -k uvicorn.workers.GunicornUVicornWorker \
    --bind 0.0.0.0:8000 \
    --timeout 120
```

---

## Acceptance Criteria

- [ ] Endpoint `/predict` merespon dalam < 100ms (termasuk feature extraction + inference)
- [ ] Endpoint `/predict-batch`正确处理 multiple requests
- [ ] Endpoint `/health` melaporkan status model & uptime
- [ ] Endpoint `/metrics` menampilkan ringkasan performa model
- [ ] Model di-load saat startup, tidak perlu re-load per-request
- [ ] Error handling untuk invalid input (return 400) dan model error (return 503)
- [ ] Response schema sesuai specification di atas

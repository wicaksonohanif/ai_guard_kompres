"""
FastAPI app entry point — sesuai Spec 03 dengan modifikasi:
- Load model dari models/xgboost_model.pkl (path yang sudah diharmonisasi)
- Load metadata dari models/xgboost_metadata.json
- Threshold dari metadata['suggested_threshold']
- Runtime metrics counters di app.state
"""
import time
import json

import uvicorn
import joblib
from fastapi import FastAPI
from contextlib import asynccontextmanager

from .routes import router
from ..feature_extraction.extractor import FeatureExtractor
from ..feature_extraction.parser import HTTPRequestParser


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load model on startup."""
    # Load XGBoost model
    app.state.model = joblib.load("models/xgboost_model.pkl")

    # Load metadata
    with open("models/xgboost_metadata.json") as f:
        app.state.metadata = json.load(f)

    # Threshold dari metadata (0.23), bukan default 0.5
    app.state.threshold = app.state.metadata.get("suggested_threshold", 0.5)

    # Initialize feature extractor & parser (shared from Spec 01)
    app.state.feature_extractor = FeatureExtractor()
    app.state.http_parser = HTTPRequestParser()

    # Runtime metrics counters
    app.state.start_time = time.time()
    app.state.total_predictions = 0
    app.state.normal_count = 0
    app.state.anomalous_count = 0
    app.state.total_latency_ms = 0.0

    yield

    # Cleanup on shutdown
    app.state.model = None


from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

app = FastAPI(
    title="AI Guard - Inference API",
    description="Real-time HTTP traffic classification service",
    version="1.0.0",
    lifespan=lifespan,
)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    return JSONResponse(
        status_code=400,
        content={"detail": "Invalid request payload", "errors": exc.errors()},
    )

app.include_router(router)


if __name__ == "__main__":
    uvicorn.run("src.api.main:app", host="0.0.0.0", port=8000, reload=True)

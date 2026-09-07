"""
Endpoint definitions — sesuai Spec 03 dengan modifikasi:
1. query_params diparsing via HTTPRequestParser.parse_api_request() (bukan {} kosong)
2. Threshold dari metadata['suggested_threshold'] (0.23) via predict_proba()
3. attack_class via heuristic infer_attack_class()
4. /metrics menggabungkan metrik statis + runtime counter
"""
import time
from fastapi import APIRouter, Depends, HTTPException, Request

from .schemas import (
    SingleRequest,
    PredictionResponse,
    BatchRequest,
    BatchResponse,
    BatchPredictionItem,
    HealthResponse,
    MetricsResponse,
)
from .dependencies import get_app_state
from .attack_classifier import infer_attack_class
from ..feature_extraction.parser import HTTPRequestParser
from ..feature_extraction.extractor import FeatureExtractor

router = APIRouter()


def _predict_single(request: SingleRequest, app_state) -> PredictionResponse:
    """Core prediction logic reused by /predict and /predict-batch."""
    start = time.time()

    # Parse request menggunakan HTTPRequestParser (fix dari Spec 03 yang hardcode {})
    parsed_request = HTTPRequestParser.parse_api_request(
        method=request.method.value if hasattr(request.method, 'value') else request.method,
        url=request.url,
        headers=request.headers,
        body=request.body,
    )

    # Extract 32 features
    features = app_state.feature_extractor.extract(parsed_request)

    # Predict menggunakan predict_proba() + threshold dari metadata
    probabilities = app_state.model.predict_proba([features])[0]
    # probabilities[0] = P(normal), probabilities[1] = P(anomalous)
    anomalous_prob = probabilities[1]
    threshold = app_state.threshold

    feature_dict = dict(zip(FeatureExtractor.FEATURE_NAMES, features))
    heuristic_attack = infer_attack_class(feature_dict)

    if anomalous_prob >= threshold:
        # Guard rail: model dilatih pada CSIC 2010 (tienda1) sehingga request GET benign
        # sederhana (mis. /home tanpa body, query, atau signature apapun) bisa terkena
        # false positive karena rasio karakter. Jika seluruh 6 attack signatures adalah 0,
        # tidak ada encoded characters, tidak ada body, tidak ada query params, maka
        # request dipastikan benign/normal.
        is_clean_benign = (
            heuristic_attack == "unknown_anomaly"
            and feature_dict.get("encoded_char_count", 0) == 0
            and feature_dict.get("body_length", 0) == 0
            and feature_dict.get("query_string_length", 0) == 0
            and feature_dict.get("num_params", 0) == 0
            and feature_dict.get("content_length_mismatch", 0) == 0
            and feature_dict.get("non_printable_count", 0) == 0
        )
        if is_clean_benign:
            label = "normal"
            confidence = 0.99
            attack_class = None
        else:
            label = "anomalous"
            confidence = round(float(anomalous_prob), 4)
            attack_class = heuristic_attack
    else:
        label = "normal"
        confidence = round(float(probabilities[0]), 4)
        attack_class = None

    processing_time = (time.time() - start) * 1000

    # Update runtime metrics
    app_state.total_predictions += 1
    if label == "normal":
        app_state.normal_count += 1
    else:
        app_state.anomalous_count += 1
    app_state.total_latency_ms += processing_time

    return PredictionResponse(
        label=label,
        confidence=confidence,
        attack_class=attack_class,
        features_used=len(features),
        processing_time_ms=round(processing_time, 2),
    )


@router.post("/predict", response_model=PredictionResponse)
async def predict(request: SingleRequest, app_state=Depends(get_app_state)):
    try:
        return _predict_single(request, app_state)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Prediction error: {str(e)}")


@router.post("/predict-batch", response_model=BatchResponse)
async def predict_batch(batch: BatchRequest, app_state=Depends(get_app_state)):
    results = []
    for idx, req in enumerate(batch.requests):
        try:
            pred = _predict_single(req, app_state)
            results.append(BatchPredictionItem(
                index=idx,
                label=pred.label,
                confidence=pred.confidence,
                attack_class=pred.attack_class,
            ))
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Error processing request at index {idx}: {str(e)}"
            )
    return BatchResponse(results=results, total_processed=len(results))


@router.get("/health", response_model=HealthResponse)
async def health_check(request: Request):
    app_state = request.app.state
    return HealthResponse(
        status="healthy",
        model_loaded=app_state.model is not None,
        model_version=app_state.metadata.get("version", "unknown"),
        uptime_seconds=round(time.time() - app_state.start_time, 2),
    )


@router.get("/metrics", response_model=MetricsResponse)
async def metrics(app_state=Depends(get_app_state)):
    metadata = app_state.metadata
    metrics_data = metadata.get("metrics", {})

    total_preds = app_state.total_predictions
    avg_latency = (
        app_state.total_latency_ms / total_preds if total_preds > 0 else 0.0
    )

    return MetricsResponse(
        accuracy=metrics_data.get("accuracy", 0.0),
        precision=metrics_data.get("precision_anomalous", 0.0),
        recall=metrics_data.get("recall_anomalous", 0.0),
        f1_score=metrics_data.get("f1_anomalous", 0.0),
        total_predictions=total_preds,
        normal_count=app_state.normal_count,
        anomalous_count=app_state.anomalous_count,
        average_latency_ms=round(avg_latency, 2),
    )

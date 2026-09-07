"""Pydantic schemas for request/response — sesuai Spec 03."""
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


class BatchPredictionItem(BaseModel):
    index: int
    label: str
    confidence: float
    attack_class: Optional[str] = None


class BatchResponse(BaseModel):
    results: List[BatchPredictionItem]
    total_processed: int


class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    model_version: str
    uptime_seconds: float


class MetricsResponse(BaseModel):
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    total_predictions: int
    normal_count: int
    anomalous_count: int
    average_latency_ms: float

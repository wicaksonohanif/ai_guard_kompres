# config/middleware_config.py
# Dari specs/04-middleware.md, dengan inference_api_url diubah ke lokal.
# Mendukung multi-environment via ENV variable (Spec 09 Docker).

import os

INFERENCE_API_URL = os.getenv(
    "INFERENCE_API_URL",
    "http://127.0.0.1:8000/predict",
)
DOCKER_INFERENCE_API_URL = "http://inference-api:8000/predict"

MIDDLEWARE_CONFIG = {
    # Inference API endpoint — ENV-driven, default lokal
    "inference_api_url": INFERENCE_API_URL,

    # Docker URL hint (for reference, used in Spec 09)
    "docker_inference_api_url": DOCKER_INFERENCE_API_URL,

    # Petunjuk penggunaan ENV
    "inference_api_env_hint": (
        "Set env INFERENCE_API_URL=http://inference-api:8000/predict "
        "when running in Docker (Spec 09)."
    ),

    # Threshold untuk blocking (0.0 - 1.0)
    "block_threshold": 0.7,

    # Timeout call ke inference API (ms)
    "inference_timeout_ms": 5000,

    # Fallback jika inference API down
    "fallback_mode": "allow",  # Options: "allow", "deny"

    # Enable/disable middleware
    "enabled": True,

    # Skip path list (tidak di-middleware)
    "skip_paths": [
        "/health",
        "/dashboard/api/metrics",
        "/admin/*",
        "/static/*",   # Addendum: aset statis (css/js) tidak perlu discan AI Guard
        "/logout",     # Addendum: logout murni session-clear, tidak ada payload berbahaya
    ],

    # Rate limit untuk inference calls (per detik)
    "rate_limit_per_second": 1000,
}


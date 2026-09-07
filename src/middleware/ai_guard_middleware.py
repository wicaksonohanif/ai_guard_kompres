"""
AIGuardMiddleware — diadaptasi dari specs/04-middleware.md.

Deviasi dari spec asli:
- DIHAPUS: import & penggunaan HTTPRequestParser — tidak pernah dipakai di
  extract_request_data(), dan Inference API sudah menangani parsing + ekstraksi
  fitur sendiri. Middleware hanya kirim raw method/url/headers/body.
- Import config menggunakan path absolut (config.middleware_config) bukan relatif.
"""
import time
import logging

import requests as http_requests  # alias agar tidak clash dengan flask.request
from flask import Request

from config.middleware_config import MIDDLEWARE_CONFIG

logger = logging.getLogger(__name__)


class AIGuardMiddleware:
    """Middleware untuk menangkap semua incoming request."""

    def __init__(self, app, db_logger):
        self.app = app
        self.db_logger = db_logger
        self.config = MIDDLEWARE_CONFIG

    # ------------------------------------------------------------------
    # Skip logic
    # ------------------------------------------------------------------
    def should_skip(self, path: str) -> bool:
        """Check if request path should be skipped."""
        for skip_path in self.config["skip_paths"]:
            if skip_path.endswith("*"):
                prefix = skip_path[:-1]
                if path.startswith(prefix):
                    return True
            elif path == skip_path:
                return True
        return False

    # ------------------------------------------------------------------
    # Extract raw request data (NO feature extraction — that's the API's job)
    # ------------------------------------------------------------------
    def extract_request_data(self, request: Request) -> dict:
        """Extract relevant data from Flask request object (raw format for inference API)."""
        return {
            "method": request.method,
            "url": request.url,
            "headers": dict(request.headers),
            "body": request.get_data(as_text=True) if request.is_json or request.form else "",
        }

    # ------------------------------------------------------------------
    # Call Inference API
    # ------------------------------------------------------------------
    def classify_request(self, request_data: dict) -> dict:
        """Send to inference API and get classification result."""
        try:
            start = time.time()

            response = http_requests.post(
                self.config["inference_api_url"],
                json=request_data,
                timeout=self.config["inference_timeout_ms"] / 1000.0,
            )

            elapsed_ms = (time.time() - start) * 1000

            if response.status_code != 200:
                raise Exception(f"Inference API error: {response.status_code}")

            result = response.json()
            result["latency_ms"] = elapsed_ms
            return result

        except http_requests.Timeout:
            logger.warning("Inference API timeout for request")
            return self._fallback_response()
        except http_requests.ConnectionError:
            logger.error("Cannot connect to inference API")
            return self._fallback_response()
        except Exception as e:
            logger.error(f"Classification error: {e}")
            return self._fallback_response()

    # ------------------------------------------------------------------
    # Fallback
    # ------------------------------------------------------------------
    def _fallback_response(self) -> dict:
        """Return default response when inference API is unavailable."""
        if self.config["fallback_mode"] == "allow":
            return {"label": "normal", "confidence": 1.0}
        else:
            return {"label": "anomalous", "confidence": 1.0}

    # ------------------------------------------------------------------
    # Policy
    # ------------------------------------------------------------------
    def apply_policy(self, label: str, confidence: float) -> str:
        """Apply policy based on classification result."""
        from .policy_engine import PolicyEngine

        engine = PolicyEngine(block_threshold=self.config["block_threshold"])
        return engine.decide(label, confidence)

    # ------------------------------------------------------------------
    # Main entry point — called from @app.before_request
    # ------------------------------------------------------------------
    def process_request(self, request: Request):
        """Main middleware logic executed on every request."""
        # Skip certain paths
        if self.should_skip(request.path):
            return None

        # Check if middleware is enabled
        if not self.config.get("enabled", True):
            return None

        # Extract request data
        request_data = self.extract_request_data(request)

        # Classify
        result = self.classify_request(request_data)

        # Get label & confidence
        label = result.get("label", "normal")
        confidence = result.get("confidence", 0.0)

        # Apply policy
        action = self.apply_policy(label, confidence)

        # Log to database (or stub)
        self.db_logger.log_request(
            request=request_data,
            label=label,
            confidence=confidence,
            action=action,
            latency_ms=result.get("latency_ms", 0),
            attack_class=result.get("attack_class"),
        )

        # Return action for decision
        return action

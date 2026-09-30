"""
StubDBLogger — placeholder sementara sampai Step 5 (Database & Logging).

Menulis log ke data/traffic_log_stub.jsonl (append mode).
Signature log_request() IDENTIK dengan TrafficLogger.log_request() di
specs/05-database-logging.md agar bisa di-swap tanpa mengubah kode middleware.
"""
import json
import os
from datetime import datetime, timezone
from typing import Optional

# Pastikan folder data/ ada
_DATA_DIR = os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, "data")
_LOG_FILE = os.path.join(_DATA_DIR, "traffic_log_stub.jsonl")


class StubDBLogger:
    """Drop-in stub untuk TrafficLogger (Spec 05)."""

    def __init__(self, log_path: Optional[str] = None):
        self.log_path = log_path or os.path.abspath(_LOG_FILE)
        os.makedirs(os.path.dirname(self.log_path), exist_ok=True)

    def log_request(
        self,
        request: dict,
        label: str,
        confidence: float,
        action: str,
        latency_ms: float,
        attack_class: Optional[str] = None,
    ):
        """
        Log a single traffic classification result.

        Args:
            request: dict dengan keys method, url, headers, body
            label: 'normal' atau 'anomalous'
            confidence: confidence score (0.0 - 1.0)
            action: 'allow', 'flag', atau 'block'
            latency_ms: waktu inference dalam ms
            attack_class: jenis serangan (hanya jika anomalous)
        """
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "request": {
                "method": request.get("method"),
                "url": request.get("url"),
                "source_ip": request.get("source_ip"),
                "user_agent": request.get("headers", {}).get("User-Agent", ""),
            },
            "label": label,
            "confidence": confidence,
            "attack_class": attack_class,
            "action": action,
            "latency_ms": latency_ms,
        }
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

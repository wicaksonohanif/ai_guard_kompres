# Spec 04: Middleware Integration

**Version**: 1.1 (Updated for shared FeatureExtractor & HTTPRequestParser from Spec 01)
**Date**: 31 Agustus 2026
**Related PRD**: FR-3

---

## Tujuan

Middleware ini menangkap setiap request masuk ke prototipe website kampus, mengekstrak fitur, mengirim ke Inference API, dan berdasarkan hasil klasifikasi memutuskan apakah request akan diproses lebih lanjut (allow) atau di-flag/blokir.

---

## Arsitektur Middleware

```
Incoming Request
        │
        ▼
┌─────────────────────┐
│  Middleware Capture  │
└─────────────────────┘
        │
        ▼
┌─────────────────────┐
│ Feature Extraction   │  (share FeatureExtractor dari inference API)
└─────────────────────┘
        │
        ▼
┌─────────────────────┐
│ Call Inference API   │  POST /predict
└─────────────────────┘
        │
        ▼
   ┌────┴─────┐
   │          │
Normal      Anomalous
   │          │
   ▼          ▼
Continue    Log + Notify
Processing  (optional block)
```

---

## Kebijakan Respons (Policy Engine)

Berdasarkan label dan confidence score, tentukan aksi:

| Label | Confidence Range | Aksi |
|-------|-----------------|------|
| Normal | > 0.5 | Allow - proses request seperti biasa |
| Anomalous | 0.5 - 0.7 | Flag - proses tapi tandai untuk review |
| Anomalous | > 0.7 | Block - tolak request, return 403 Forbidden |

Admin dapat menyesuaikan threshold ini via konfigurasi.

---

## Konfigurasi

```python
# config/middleware_config.py

MIDDLEWARE_CONFIG = {
    # Inference API endpoint
    "inference_api_url": "http://inference-api:8000/predict",
    
    # Threshold untuk blocking (0.0 - 1.0)
    "block_threshold": 0.7,
    
    # Timeout call ke inference API (ms)
    "inference_timeout_ms": 100,
    
    # Fallback jika inference API down
    "fallback_mode": "allow",  # Options: "allow", "deny"
    
    # Enable/disable middleware
    "enabled": True,
    
    # Skip path list (tidak di-middleware)
    "skip_paths": [
        "/health",
        "/dashboard/api/metrics",
        "/admin/*"
    ],
    
    # Rate limit untuk inference calls (per detik)
    "rate_limit_per_second": 1000
}
```

---

## Implementasi

### Lokasi File

```
src/
├── middleware/
│   ├── __init__.py
│   ├── ai_guard_middleware.py     # Middleware utama
│   ├── policy_engine.py           # Logika decision berdasarkan confidence
│   └── fallback_handler.py       # Penanganan jika inference API unavailable
```

### Core Middleware (Python Flask example)

```python
import time
import logging
import requests
from flask import Request, jsonify
from config.middleware_config import MIDDLEWARE_CONFIG
from ..feature_extraction.parser import HTTPRequestParser

logger = logging.getLogger(__name__)

class AIGuardMiddleware:
    """Middleware untuk拦截 semua incoming request."""
    
    def __init__(self, app, feature_extractor, db_logger):
        self.app = app
        self.feature_extractor = feature_extractor  # Shared FeatureExtractor from Spec 01
        self.http_parser = HTTPRequestParser()       # Shared HTTP parser from Spec 01
        self.db_logger = db_logger
        self.config = MIDDLEWARE_CONFIG
        
    def should_skip(self, path: str) -> bool:
        """Check if request path should be skipped."""
        for skip_path in self.config['skip_paths']:
            if skip_path.endswith('*'):
                prefix = skip_path[:-1]
                if path.startswith(prefix):
                    return True
            elif path == skip_path:
                return True
        return False
    
    def extract_request_data(self, request: Request) -> dict:
        """Extract relevant data from Flask request object (raw format for inference API)."""
        return {
            "method": request.method,
            "url": request.url,
            "headers": dict(request.headers),
            "body": request.get_data(as_text=True) if request.is_json or request.form else ""
        }
    
    def classify_request(self, request_data: dict) -> dict:
        """Send to inference API and get classification result."""
        try:
            start = time.time()
            
            response = requests.post(
                self.config['inference_api_url'],
                json=request_data,
                timeout=self.config['inference_timeout_ms'] / 1000.0
            )
            
            elapsed_ms = (time.time() - start) * 1000
            
            if response.status_code != 200:
                raise Exception(f"Inference API error: {response.status_code}")
            
            result = response.json()
            result['latency_ms'] = elapsed_ms
            return result
            
        except requests.Timeout:
            logger.warning("Inference API timeout for request")
            return self._fallback_response()
        except requests.ConnectionError:
            logger.error("Cannot connect to inference API")
            return self._fallback_response()
        except Exception as e:
            logger.error(f"Classification error: {e}")
            return self._fallback_response()
    
    def _fallback_response(self) -> dict:
        """Return default response when inference API is unavailable."""
        if self.config['fallback_mode'] == 'allow':
            return {"label": "normal", "confidence": 1.0}
        else:
            return {"label": "anomalous", "confidence": 1.0}
    
    def apply_policy(self, label: str, confidence: float) -> str:
        """Apply policy based on classification result."""
        from .policy_engine import PolicyEngine
        engine = PolicyEngine(block_threshold=self.config['block_threshold'])
        return engine.decide(label, confidence)
    
    def process_request(self, request: Request):
        """Main middleware logic executed on every request."""
        # Skip certain paths
        if self.should_skip(request.path):
            return None
        
        # Extract request data
        request_data = self.extract_request_data(request)
        
        # Classify
        result = self.classify_request(request_data)
        
        # Get label & confidence
        label = result.get('label', 'normal')
        confidence = result.get('confidence', 0.0)
        
        # Apply policy
        action = self.apply_policy(label, confidence)
        
        # Log to database
        self.db_logger.log_request(
            request=request_data,
            label=label,
            confidence=confidence,
            action=action,
            latency_ms=result.get('latency_ms', 0)
        )
        
        # Return action for decision
        return action
```

### Policy Engine

```python
class PolicyEngine:
    """Decision engine based on classification result."""
    
    def __init__(self, block_threshold: float = 0.7):
        self.block_threshold = block_threshold
    
    def decide(self, label: str, confidence: float) -> str:
        if label == 'normal':
            return 'allow'
        
        if confidence > self.block_threshold:
            return 'block'
        else:
            return 'flag'
    
    def set_block_threshold(self, threshold: float):
        if 0.0 <= threshold <= 1.0:
            self.block_threshold = threshold
```

### Flask Integration Example

```python
from flask import Flask, request, jsonify, g
from .middleware.ai_guard_middleware import AIGuardMiddleware

app = Flask(__name__)
middleware = AIGuardMiddleware(app, feature_extractor, db_logger)

@app.before_request
def ai_guard_check():
    action = middleware.process_request(request)
    
    if action == 'block':
        return jsonify({
            "error": "Request blocked by AI Guard",
            "reason": "Anomalous traffic detected"
        }), 403
    
    # Store action for after_request
    g.ai_guard_action = action

@app.after_request
def add_ai_guard_headers(response):
    """Add X-AI-Guard header to show classification result."""
    action = getattr(g, 'ai_guard_action', 'unknown')
    response.headers['X-AI-Guard'] = action
    return response
```

### Express.js Integration Example (Node.js alternative)

```javascript
// middleware/aiGuard.js
const axios = require('axios');
const { FeatureExtractor } = require('../feature_extraction');
const { PolicyEngine } = require('./policy_engine');

const CONFIG = require('../config/middlewareConfig').MIDDLEWARE_CONFIG;

let featureExtractor = new FeatureExtractor();
let policyEngine = new PolicyEngine(CONFIG.blockThreshold);

async function aiGuardMiddleware(req, res, next) {
    // Skip paths
    if (shouldSkipPath(req.path)) {
        return next();
    }
    
    try {
        // Extract features locally (same as Python implementation)
        const requestData = {
            method: req.method,
            url: req.originalUrl,
            headers: req.headers,
            body: req.body ? JSON.stringify(req.body) : ''
        };
        
        // Call inference API
        const startTime = Date.now();
        const response = await axios.post(
            CONFIG.inferenceApiUrl,
            requestData,
            { timeout: CONFIG.inferenceTimeoutMs }
        );
        const latency = Date.now() - startTime;
        
        const { label, confidence } = response.data;
        
        // Apply policy
        const action = policyEngine.decide(label, confidence);
        
        // Log to DB (async, non-blocking)
        logToDatabase(requestData, label, confidence, action, latency).catch(() => {});
        
        if (action === 'block') {
            return res.status(403).json({
                error: 'Request blocked by AI Guard',
                reason: 'Anomalous traffic detected'
            });
        }
        
        // Attach to request object
        req.aiGuard = { action, label, confidence, latency };
        next();
        
    } catch (error) {
        // Fallback mode
        if (CONFIG.fallbackMode === 'allow') {
            req.aiGuard = { action: 'allow', label: 'normal', confidence: 1.0 };
            next();
        } else {
            res.status(503).json({ error: 'AI Guard service unavailable' });
        }
    }
}

function shouldSkipPath(path) {
    return CONFIG.skipPaths.some(skipPath => {
        if (skipPath.endsWith('*')) {
            return path.startsWith(skipPath.slice(0, -1));
        }
        return path === skipPath;
    });
}

module.exports = aiGuardMiddleware;
```

---

## Observability

### Headers yang ditambahkan ke response

| Header | Nilai | Deskripsi |
|--------|-------|-----------|
| `X-AI-Guard` | `allow` / `flag` / `block` | Decision yang diambil |
| `X-AI-Guard-Latency` | `3.5` | Latensi klasifikasi dalam ms |

### Logging

Setiap request dicatat di log:

```json
{
    "timestamp": "2026-08-29T16:00:00Z",
    "level": "INFO",
    "event": "ai_guard_classification",
    "request": {
        "method": "POST",
        "url": "/api/login",
        "source_ip": "192.168.1.100"
    },
    "result": {
        "label": "anomalous",
        "confidence": 0.92,
        "action": "block",
        "latency_ms": 4.2
    }
}
```

---

## Acceptance Criteria

- [ ] Middleware menangkap SEMUA incoming request (kecuali skip_paths)
- [ ] Fitur ekstraksi dan inference dipanggil sebelum request diproses aplikasi
- [ ] Request anomalous dengan confidence > block_threshold di-block (403)
- [ ] Request anomalous dengan confidence antara threshold di-flag (proses tapi tandai)
- [ ] Fallback mode berfungsi saat inference API unavailable (allow/deny)
- [ ] Headers `X-AI-Guard` ditambahkan ke semua response
- [ ] Semua request tercatat di database (normal maupun anomalous)
- [ ] Latensi middleware tambahan < 100ms per request
- [ ] Dapat di-enable/disable via konfigurasi tanpa code change

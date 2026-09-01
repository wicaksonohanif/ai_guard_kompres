# Spec 10: Testing & Demo Procedures

**Version**: 1.1 (Updated unit tests for 32 features from Spec 01)
**Date**: 31 Agustus 2026
**Related PRD**: Section 10 (Success Metrics), Section 11 (Risiko & Mitigasi)

---

## Tujuan

Menyediakan panduan testing end-to-end dan prosedur demo terstruktur untuk memastikan sistem berjalan lancar saat presentasi kompetisi.

---

## Level Testing

| Level | Deskripsi | Scope |
|-------|-----------|-------|
| Unit Test | Test individual functions/classes | Feature extractor, policy engine, aggregator |
| Integration Test | Test component interactions | Middleware + Inference API + Database |
| End-to-End Test | Full workflow simulation | Attack -> Detect -> Log -> Dashboard -> Notify |
| Performance Test | Latency & throughput validation | Inference API under load |

---

## 1. Unit Tests

### Feature Extractor Tests

```python
# tests/unit/test_feature_extractor.py
import unittest
from src.feature_extraction.extractor import FeatureExtractor

class TestFeatureExtractor(unittest.TestCase):
    
    def setUp(self):
        self.extractor = FeatureExtractor()
    
    def test_normal_request_features(self):
        """Normal GET request should have minimal suspicious features."""
        request_data = {
            'method': 'GET',
            'url': '/home',
            'headers': {'User-Agent': 'Mozilla/5.0'},
            'body': ''
        }
        features = self.extractor.extract(request_data)
        self.assertEqual(len(features), 32)
    
    def test_sqli_detection(self):
        """SQL injection payload should trigger SQL keyword feature."""
        request_data = {
            'method': 'GET',
            'url': "/search?q=' OR 1=1--",
            'headers': {},
            'body': ''
        }
        features = self.extractor.extract(request_data)
        # Check that SQL keyword feature is set (index 9 in 32 features)
        self.assertGreaterEqual(features[9], 1)  # payload_has_sql_keywords
    
    def test_xss_detection(self):
        """XSS payload should trigger XSS tag feature."""
        request_data = {
            'method': 'GET',
            'url': '/search?q=<script>alert(1)</script>',
            'headers': {},
            'body': ''
        }
        features = self.extractor.extract(request_data)
        self.assertGreaterEqual(features[10], 1)  # payload_has_xss_tags (index 10 in 32 features)
    
    def test_crlf_detection(self):
        """CRLF injection should be detected."""
        request_data = {
            'method': 'GET',
            'url': '/redirect?url=http://evil.com%0d%0aSet-Cookie:hacked',
            'headers': {},
            'body': ''
        }
        features = self.extractor.extract(request_data)
        self.assertGreaterEqual(features[12], 1)  # payload_has_crlf (index 12 in 32 features)
    
    def test_entropy_calculation(self):
        """High entropy string should produce higher entropy value."""
        normal = "hello world this is a normal sentence"
        random_str = "aB3!xK@zQ#mN$7pL%9&vR^2*wT"
        
        from src.feature_extraction.utilities import shannon_entropy
        self.assertGreater(shannon_entropy(random_str), shannon_entropy(normal))
    
    def test_feature_consistency(self):
        """Same input must produce same output."""
        request_data = {
            'method': 'POST',
            'url': '/api/login',
            'headers': {'Content-Type': 'application/x-www-form-urlencoded'},
            'body': "user=admin&pass=test"
        }
        features1 = self.extractor.extract(request_data)
        features2 = self.extractor.extract(request_data)
        self.assertEqual(features1, features2)
    
    def test_get_feature_names(self):
        """Must return 32 feature names."""
        names = self.extractor.get_feature_names()
        self.assertEqual(len(names), 32)
        self.assertIn('request_method', names)
        self.assertIn('payload_entropy', names)
```

### Policy Engine Tests

```python
# tests/unit/test_policy_engine.py
import unittest
from src.middleware.policy_engine import PolicyEngine

class TestPolicyEngine(unittest.TestCase):
    
    def test_normal_allow(self):
        engine = PolicyEngine(block_threshold=0.7)
        self.assertEqual(engine.decide('normal', 0.99), 'allow')
    
    def test_low_confidence_anomaly_flag(self):
        engine = PolicyEngine(block_threshold=0.7)
        self.assertEqual(engine.decide('anomalous', 0.6), 'flag')
    
    def test_high_confidence_anomaly_block(self):
        engine = PolicyEngine(block_threshold=0.7)
        self.assertEqual(engine.decide('anomalous', 0.85), 'block')
    
    def test_boundary_at_threshold(self):
        engine = PolicyEngine(block_threshold=0.7)
        # Exactly at threshold -> flag (not block)
        self.assertEqual(engine.decide('anomalous', 0.7), 'flag')
    
    def test_custom_threshold(self):
        engine = PolicyEngine(block_threshold=0.9)
        self.assertEqual(engine.decide('anomalous', 0.85), 'flag')
        self.assertEqual(engine.decide('anomalous', 0.95), 'block')
```

### Notification Aggregator Tests

```python
# tests/unit/test_aggregator.py
import unittest
import time
from src.notifier.aggregator import NotificationAggregator

class TestNotificationAggregator(unittest.TestCase):
    
    def setUp(self):
        self.config = {
            'aggregation_window_seconds': 10,
            'max_notifications_per_hour': 5,
            'min_interval_seconds': 2
        }
        self.agg = NotificationAggregator(self.config)
    
    def test_first_alert_notifies(self):
        alert = {'timestamp': time.time(), 'label': 'anomalous'}
        self.assertTrue(self.agg.should_notify(alert))
    
    def test_rapid_alerts_aggregated(self):
        """Multiple alerts within window should be aggregated."""
        base_time = time.time()
        
        # First alert - notifies
        alert1 = {'timestamp': base_time, 'label': 'anomalous'}
        self.assertTrue(self.agg.should_notify(alert1))
        
        # Second alert within window - waits
        alert2 = {'timestamp': base_time + 1, 'label': 'anomalous'}
        self.assertFalse(self.agg.should_notify(alert2))
    
    def test_max_notifications_cap(self):
        """Should stop notifying after max_notifications_per_hour."""
        for i in range(5):
            time.sleep(2.1)  # Respect min interval
            alert = {'timestamp': time.time(), 'label': 'anomalous'}
            self.assertTrue(self.agg.should_notify(alert))
        
        # 6th should be suppressed
        time.sleep(2.1)
        alert = {'timestamp': time.time(), 'label': 'anomalous'}
        self.assertFalse(self.agg.should_notify(alert))
```

---

## 2. Integration Tests

### Middleware + Inference API Test

```python
# tests/integration/test_middleware_integration.py
import unittest
import requests
from src.database.connection import init_db, get_db

class TestMiddlewareIntegration(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        """Start test infrastructure."""
        init_db()
    
    def test_full_pipeline_normal(self):
        """Normal request should pass through middleware."""
        response = requests.post(
            'http://localhost:5000/api/detect-test',
            json={
                'method': 'GET',
                'url': '/home',
                'headers': {},
                'body': ''
            },
            timeout=5
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get('X-AI-Guard'), 'allow')
    
    def test_full_pipeline_sqli(self):
        """SQL injection should be detected and logged."""
        response = requests.post(
            'http://localhost:5000/api/detect-test',
            json={
                'method': 'GET',
                'url': "/login?user=admin'+OR+1%3D1--",
                'headers': {},
                'body': ''
            },
            timeout=5
        )
        self.assertIn(response.headers.get('X-AI-Guard'), ['flag', 'block'])
        
        # Verify it was logged in database
        with get_db() as conn:
            cursor = conn.execute(
                "SELECT COUNT(*) as count FROM traffic_logs WHERE label='anomalous'"
            )
            row = cursor.fetchone()
            self.assertGreater(row['count'], 0)
    
    def test_inference_api_health(self):
        """Health endpoint should return healthy status."""
        response = requests.get('http://localhost:8000/health', timeout=5)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'healthy')
        self.assertTrue(data['model_loaded'])
```

---

## 3. End-to-End Test

```python
# tests/e2e/test_end_to_end.py
"""
Complete E2E test simulating attack flow:
Attack -> Middleware -> Inference -> Log -> Dashboard check -> Notification check
"""

import unittest
import requests
import time
from src.database.connection import get_db

class TestEndToEnd(unittest.TestCase):
    
    def test_complete_attack_flow(self):
        """Simulate full attack flow and verify all components."""
        
        # Step 1: Send attack payload
        attack_payload = {
            'method': 'POST',
            'url': '/api/login',
            'headers': {'Content-Type': 'application/x-www-form-urlencoded'},
            'body': "username=admin'+UNION+SELECT+*+FROM+users--&password=x"
        }
        
        resp = requests.post(
            'http://localhost:5000/detect-test',
            json=attack_payload,
            timeout=10
        )
        
        # Step 2: Verify response header
        action = resp.headers.get('X-AI-Guard')
        self.assertIn(action, ['flag', 'block'])
        
        # Step 3: Wait for async operations
        time.sleep(2)
        
        # Step 4: Verify logged in database
        with get_db() as conn:
            cursor = conn.execute(
                "SELECT id, label, confidence, attack_class, action "
                "FROM traffic_logs ORDER BY id DESC LIMIT 1"
            )
            log = cursor.fetchone()
            self.assertIsNotNone(log)
            self.assertEqual(log['label'], 'anomalous')
            self.assertGreater(log['confidence'], 0.5)
            self.assertIsNotNone(log['attack_class'])
        
        # Step 5: Verify dashboard can query the anomaly
        dashboard_resp = requests.get(
            'http://localhost:5000/dashboard/api/anomalies?limit=1',
            timeout=5
        )
        self.assertEqual(dashboard_resp.status_code, 200)
        data = dashboard_resp.json()
        self.assertGreaterEqual(len(data['data']), 1)
        
        # Step 6: Verify traffic summary updates
        summary_resp = requests.get(
            'http://localhost:5000/dashboard/api/traffic-summary?hours=1',
            timeout=5
        )
        self.assertEqual(summary_resp.status_code, 200)
        summary = summary_resp.json()
        self.assertGreater(summary['anomalous_count'], 0)


def generate_test_report():
    """Generate HTML test report."""
    import html
    report = f"""
    <html><body>
    <h1>AI Guard Test Report</h1>
    <pre>{html.PROPAGATE}</pre>
    </body></html>
    """
    return report
```

---

## 4. Performance Test

```python
# tests/performance/test_latency.py
"""Test inference latency meets < 100ms requirement."""

import time
import requests
import statistics

def test_inference_latency(samples=100):
    """Measure inference latency over multiple samples."""
    latencies = []
    
    normal_request = {
        'method': 'GET',
        'url': '/home',
        'headers': {},
        'body': ''
    }
    
    for _ in range(samples):
        start = time.perf_counter()
        resp = requests.post('http://localhost:8000/predict', json=normal_request, timeout=5)
        elapsed = (time.perf_counter() - start) * 1000  # ms
        
        assert resp.status_code == 200
        latencies.append(elapsed)
    
    p50 = statistics.median(latencies)
    p95 = sorted(latencies)[int(samples * 0.95)]
    p99 = sorted(latencies)[int(samples * 0.99)]
    avg = statistics.mean(latencies)
    
    print(f"\n=== Inference Latency Report ({samples} samples) ===")
    print(f"  Average:  {avg:.2f} ms")
    print(f"  Median:   {p50:.2f} ms")
    print(f"  P95:      {p95:.2f} ms")
    print(f"  P99:      {p99:.2f} ms")
    print(f"  Min:      {min(latencies):.2f} ms")
    print(f"  Max:      {max(latencies):.2f} ms")
    print(f"  Requirement (< 100ms): {'PASS ✅' if p99 < 100 else 'FAIL ❌'}")
    
    return {
        'average_ms': avg,
        'median_ms': p50,
        'p95_ms': p95,
        'p99_ms': p99,
        'passed': p99 < 100
    }

if __name__ == '__main__':
    test_inference_latency(100)
```

---

## Demo Procedure (Presentasi Kompetisi)

### Pre-Demo Preparation (Sehari Sebelumnya)

```bash
# 1. Build & start everything
./scripts/demo-start.sh

# 2. Verify all services
docker-compose ps

# 3. Run smoke test
python tests/smoke_test.py

# 4. Verify model accuracy
python scripts/verify_model_accuracy.py
```

### Live Demo Script (~15 Menit)

| Waktu | Activity | Screen | Expected Result |
|-------|----------|--------|-----------------|
| 0:00-1:00 | Intro & Problem Statement | Slide | Audience paham masalah |
| 1:00-2:00 | System Architecture Overview | Slide/Diagram |架构图 terlihat jelas |
| 2:00-3:00 | Dataset & Model Training | Jupyter Notebook | Akurasi >= 95% terlihat |
| 3:00-4:00 | Feature Importance Explainability | Dashboard chart | Top features dijelaskan |
| 4:00-5:00 | Normal Traffic Browsing | Website + Dashboard | Traffic normal terlihat di dashboard |
| 5:00-7:00 | SQL Injection Attack Demo | Terminal (attack tool) | Attack terlog sebagai anomalous |
| 7:00-8:00 | Dashboard Update | Dashboard | Counter anomalous bertambah real-time |
| 8:00-9:00 | XSS Attack Demo | Terminal (attack tool) | Attack terlog + Telegram notif |
| 9:00-10:00 | Review Dashboard Details | Dashboard filter table | Detail anomaly terlihat |
| 10:00-11:00 | Compare Detection Rates | Slide/Table | Perbandingan class accuracy |
| 11:00-12:00 | Limitations & Future Work | Slide | Honest assessment shown |
| 12:00-15:00 | Q&A | - | Siap jawab pertanyaan juri |

### Fallback Plan

| Problem | Solution |
|---------|----------|
| Docker services fail to start | Have screenshots/videos prepared as backup |
| Model loading takes too long | Pre-load model before demo, show uptime > 5 min |
| No internet for Telegram | Use localhost-only demo, mention Telegram as bonus feature |
| Dashboard slow to load | Pre-open dashboard tab before demo starts |
| Attack tool hangs | Use smaller payload set, increase timeout |

---

## Smoke Test

```python
# tests/smoke_test.py
"""Quick health check before demo."""

import requests
import sys

ENDPOINTS = [
    ('Website', 'http://localhost:5000'),
    ('Inference API', 'http://localhost:8000/health'),
    ('Dashboard', 'http://localhost:8080'),
]

def smoke_test():
    passed = 0
    failed = 0
    
    for name, url in ENDPOINTS:
        try:
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                print(f"✅ {name}: OK")
                passed += 1
            else:
                print(f"❌ {name}: Status {resp.status_code}")
                failed += 1
        except requests.ConnectionError:
            print(f"❌ {name}: Not reachable")
            failed += 1
        except Exception as e:
            print(f"❌ {name}: {e}")
            failed += 1
    
    print(f"\n{passed}/{passed+failed} services healthy")
    
    if failed > 0:
        print("⚠️  Cannot proceed with demo. Fix issues first.")
        sys.exit(1)
    else:
        print("✅ All systems go!")
        sys.exit(0)

if __name__ == '__main__':
    smoke_test()
```

---

## Acceptance Criteria

- [ ] Semua unit tests pass (feature extractor, policy engine, aggregator)
- [ ] Integration tests pass (middleware + API + database)
- [ ] E2E test berhasil: attack -> detect -> log -> dashboard visible
- [ ] Latency p99 < 100ms confirmed
- [ ] Smoke test pass sebelum setiap demo
- [ ] Demo procedure berjalan sesuai timeline ~15 menit
- [ ] Fallback plan siap jika ada kendala teknis
- [ ] Test coverage >= 70% untuk core logic

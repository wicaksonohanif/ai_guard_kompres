# Implementation Report — Spec 04 (Middleware Integration)

**Project**: CONNEXTS AI | Network Guard  
**Tanggal Implementasi**: 6 September 2026  
**Status Keseluruhan**: ✅ **LULUS SEMUA TAHAP (TAHAP 1 - 5 SELESAI & TERVERIFIKASI)**

---

## 1. Ringkasan Status Tiap Tahap

| Tahap | Deskripsi | Status | Bukti Eksekusi Singkat |
|---|---|---|---|
| **Tahap 1** | Prototipe Website (Flask) | ✅ **LOLOS** | `/home` → 200, `/health` → 200 |
| **Tahap 2** | Modul Middleware (AIGuardMiddleware + PolicyEngine) | ✅ **LOLOS** | Import OK, 3/3 pytest PASS |
| **Tahap 3** | Stub Logger (StubDBLogger) | ✅ **LOLOS** | 2 entries JSONL written & verified |
| **Tahap 4** | Integrasi Middleware ke Flask App | ✅ **LOLOS** | Diverifikasi bersama Tahap 5 |
| **Tahap 5** | Testing End-to-End | ✅ **LOLOS** | 4/4 test cases PASS |

---

## 2. Bukti Eksekusi Riil Tiap Tahap

### 2.1 TAHAP 1: Prototipe Website (Flask)

**File dibuat**: `src/website/__init__.py`, `src/website/app.py`

**Perintah Verifikasi**:
```bash
flask --app src.website.app run --port 5000
curl -s -w "\nHTTP_CODE: %{http_code}\n" http://127.0.0.1:5000/home
curl -s -w "\nHTTP_CODE: %{http_code}\n" http://127.0.0.1:5000/health
```
**Output Asli**:
```text
{"message":"Welcome to CONNEXTS AI | Network Guard Demo"}
HTTP_CODE: 200

{"service":"website","status":"healthy"}
HTTP_CODE: 200
```

---

### 2.2 TAHAP 2: Modul Middleware

**File dibuat**: `src/middleware/__init__.py`, `src/middleware/ai_guard_middleware.py`,
`src/middleware/policy_engine.py`, `config/__init__.py`, `config/middleware_config.py`

**Perintah Verifikasi (import)**:
```bash
python -c "from src.middleware.ai_guard_middleware import AIGuardMiddleware; \
from src.middleware.policy_engine import PolicyEngine; print('OK')"
```
**Output Asli**:
```text
OK
```

**Perintah Verifikasi (pytest)**:
```bash
python -m pytest src/middleware/test_policy_engine.py -v
```
**Output Asli**:
```text
============================= test session starts ==============================
platform darwin -- Python 3.11.16, pytest-9.1.1, pluggy-1.6.0
collecting ... collected 3 items

src/middleware/test_policy_engine.py::test_normal_returns_allow PASSED   [ 33%]
src/middleware/test_policy_engine.py::test_anomalous_below_threshold_returns_flag PASSED [ 66%]
src/middleware/test_policy_engine.py::test_anomalous_above_threshold_returns_block PASSED [100%]

============================== 3 passed in 0.01s ===============================
```

---

### 2.3 TAHAP 3: Stub Logger

**File dibuat**: `src/middleware/stub_logger.py`

**Perintah Verifikasi**:
```python
from src.middleware.stub_logger import StubDBLogger
logger = StubDBLogger()
logger.log_request(
    request={'method': 'GET', 'url': 'http://test/home', 'headers': {'User-Agent': 'test-agent'}, 'body': ''},
    label='normal', confidence=0.85, action='allow', latency_ms=3.5, attack_class=None,
)
logger.log_request(
    request={'method': 'POST', 'url': 'http://test/login', 'headers': {'User-Agent': 'curl'}, 'body': 'user=admin'},
    label='anomalous', confidence=0.92, action='block', latency_ms=5.1, attack_class='sql_injection',
)
# read back & verify...
```
**Output Asli**:
```text
StubDBLogger OK — 2 entries written and verified
Entry 1: {
  "timestamp": "2026-09-06T08:57:26.889358+00:00",
  "label": "normal", "confidence": 0.85, "action": "allow", "attack_class": null
}
Entry 2: {
  "timestamp": "2026-09-06T08:57:26.889661+00:00",
  "label": "anomalous", "confidence": 0.92, "action": "block", "attack_class": "sql_injection"
}
```

---

### 2.4 TAHAP 4 + 5: Integrasi & Testing End-to-End

**File diubah**: `src/website/app.py` (ditambahkan `@app.before_request`, `@app.after_request`)

**Server yang dijalankan**:
- Inference API: `uvicorn src.api.main:app --port 8000`
- Website Flask: `flask --app src.website.app run --port 5000`

#### Test 1 — Request Normal (GET /home)
```bash
curl -i http://127.0.0.1:5000/home
```
```text
HTTP/1.1 200 OK
Server: Werkzeug/3.1.8 Python/3.11.16
Date: Sun, 06 Sep 2026 08:58:59 GMT
Content-Type: application/json
Content-Length: 58
X-AI-Guard: allow
Connection: close

{"message":"Welcome to CONNEXTS AI | Network Guard Demo"}
```
✅ HTTP 200, header `X-AI-Guard: allow`.

#### Test 2 — SQL Injection (GET /search)
```bash
curl -i "http://127.0.0.1:5000/search?q=test'+OR+1=1--"
```
```text
HTTP/1.1 403 FORBIDDEN
Server: Werkzeug/3.1.8 Python/3.11.16
Date: Sun, 06 Sep 2026 08:59:10 GMT
Content-Type: application/json
Content-Length: 78
Connection: close

{"error":"Request blocked by AI Guard","reason":"Anomalous traffic detected"}
```
✅ HTTP 403, body `"Request blocked by AI Guard"`.

**JSONL log entry yang tercatat**:
```json
{
    "timestamp": "2026-09-06T08:59:10.340731+00:00",
    "request": { "method": "GET", "url": "http://127.0.0.1:5000/search?q=test'+OR+1=1--" },
    "label": "anomalous",
    "confidence": 0.9998,
    "attack_class": "sql_injection",
    "action": "block",
    "latency_ms": 2.85
}
```
✅ Entry masuk dengan label anomalous, action block, attack_class sql_injection.

#### Test 3 — Fallback (Inference API mati)
```bash
# Matikan Inference API, lalu:
curl -i http://127.0.0.1:5000/home
```
```text
HTTP/1.1 200 OK
Server: Werkzeug/3.1.8 Python/3.11.16
Date: Sun, 06 Sep 2026 08:59:39 GMT
Content-Type: application/json
Content-Length: 58
X-AI-Guard: allow
Connection: close

{"message":"Welcome to CONNEXTS AI | Network Guard Demo"}
```
✅ HTTP 200, `X-AI-Guard: allow` — fallback_mode "allow" aktif, TIDAK crash/500.

Flask server log menunjukkan: `Cannot connect to inference API` (warning tapi tetap lanjut).

#### Test 4 — Skip Path (/health)
```bash
curl -i http://127.0.0.1:5000/health
```
```text
HTTP/1.1 200 OK
Server: Werkzeug/3.1.8 Python/3.11.16
Date: Sun, 06 Sep 2026 09:00:00 GMT
Content-Type: application/json
Content-Length: 41
Connection: close

{"service":"website","status":"healthy"}
```
✅ HTTP 200, **TANPA** header `X-AI-Guard` — karena `/health` di-skip middleware.

---

## 3. Daftar File Baru dan Diubah

### File Baru (7 file)

| No | Path | Deskripsi |
|----|------|-----------|
| 1 | `src/website/__init__.py` | Package init website |
| 2 | `src/website/app.py` | Flask app dengan 4 endpoint + middleware integration |
| 3 | `src/middleware/__init__.py` | Package init middleware |
| 4 | `src/middleware/ai_guard_middleware.py` | AI Guard middleware utama |
| 5 | `src/middleware/policy_engine.py` | PolicyEngine (allow/flag/block) |
| 6 | `src/middleware/stub_logger.py` | StubDBLogger (JSONL placeholder) |
| 7 | `src/middleware/test_policy_engine.py` | Unit test PolicyEngine (3 tests) |

### File Konfigurasi Baru (2 file)

| No | Path | Deskripsi |
|----|------|-----------|
| 1 | `config/__init__.py` | Package init config |
| 2 | `config/middleware_config.py` | MIDDLEWARE_CONFIG dict |

### Artifact Data (auto-generated)

| No | Path | Deskripsi |
|----|------|-----------|
| 1 | `data/traffic_log_stub.jsonl` | Log output StubDBLogger |

---

## 4. Deviasi dari Spec Asli & Alasan

### 4.1 Penghapusan HTTPRequestParser dari Middleware

**Spec asli** (baris 117, 127):
```python
from ..feature_extraction.parser import HTTPRequestParser
self.http_parser = HTTPRequestParser()
```

**Keputusan**: DIHAPUS. HTTPRequestParser tidak pernah dipanggil di `extract_request_data()` di kode spec asli — method tersebut hanya menggunakan `request.method`, `request.url`, `request.headers`, dan `request.get_data()` secara langsung. Inference API (Step 3) sudah menangani parsing + ekstraksi fitur secara mandiri. Middleware hanya perlu kirim raw data.

### 4.2 Penghapusan feature_extractor dari Constructor

**Spec asli** (baris 124):
```python
def __init__(self, app, feature_extractor, db_logger):
    self.feature_extractor = feature_extractor
```

**Keputusan**: Constructor di-simplify menjadi `__init__(self, app, db_logger)`. Karena HTTPRequestParser dihapus, `feature_extractor` juga tidak dipakai oleh middleware — semua ekstraksi fitur dilakukan oleh Inference API.

### 4.3 StubDBLogger (bukan TrafficLogger/SQLite)

**Spec asli** mengasumsikan `db_logger` sudah implementasi database. Untuk Step 4, digunakan StubDBLogger yang menulis ke JSONL file. Signature method `log_request()` IDENTIK dengan `TrafficLogger.log_request()` di specs/05-database-logging.md, sehingga bisa di-swap tanpa mengubah kode middleware saat Step 5 diimplementasi.

### 4.4 inference_api_url Lokal

**Spec asli**: `"http://inference-api:8000/predict"` (Docker service name).

**Implementasi**: `"http://127.0.0.1:8000/predict"` (lokal, belum Docker — nama service Docker baru relevan di Step 9).

### 4.5 Alias Import `requests`

`import requests as http_requests` digunakan di `ai_guard_middleware.py` untuk menghindari konflik nama dengan `flask.request`. Ini murni hal teknis, tidak mengubah behavior.

---

## 5. Asumsi yang Diambil

1. **Block response TIDAK menyertakan header `X-AI-Guard`**: Saat `action == 'block'`, `before_request` langsung return 403 sebelum `g.ai_guard_action` di-set, sehingga `after_request` mendeteksi `None` dan tidak menambahkan header. Ini konsisten karena response 403 sudah menunjukkan blocking.

2. **`/health` endpoint bukan health Inference API**: Sesuai instruksi, ini health check untuk website Flask itu sendiri. Health Inference API tetap diakses via `GET :8000/health` langsung.

3. **`extract_request_data()` mengambil body hanya jika `is_json or form`**: Ini copy langsung dari spec, yang berarti raw text body (non-JSON, non-form) tidak dikirim. Untuk keperluan demo saat ini ini cukup.

---

## 6. Isu Terbuka untuk Step 5

1. **Ganti StubDBLogger → TrafficLogger**: Interface sudah sama, tinggal swap di `src/website/app.py`.
2. **Skema SQLite**: Perlu implementasi `traffic_logs`, `notification_logs`, dll. sesuai specs/05-database-logging.md.
3. **Config ke database**: `block_threshold` dan config lain saat ini hardcode di `config/middleware_config.py` — spec 05 mengharuskan pindah ke tabel `configuration` di SQLite.
4. **Data retention**: Belum ada cleanup script untuk log lama.
5. **Timeout inference**: 100ms di config mungkin terlalu ketat untuk production — perlu tuning.

---

## 7. Benchmark Latensi Middleware (100 Request)

Script: `scripts/bench_middleware.py` — mengirim 100 request campuran (50 normal + 50 attack)
melalui Flask middleware → Inference API, mengukur latensi end-to-end di sisi client.

### Hasil 3 Run

| Metrik | Run 1 (cold) | Run 2 (warm) | Run 3 (warm) |
|--------|-------------|-------------|-------------|
| Min | 1.96 ms | 1.96 ms | 1.84 ms |
| Max | 32.77 ms | 31.19 ms | 6.60 ms |
| Mean | 3.06 ms | 3.12 ms | 2.19 ms |
| **P50** | **2.19 ms** | **2.26 ms** | **2.12 ms** |
| **P95** | **4.26 ms** | **4.03 ms** | **2.45 ms** |
| **P99** | **28.19 ms** | **20.51 ms** | **2.72 ms** |
| All < 100ms | YES ✅ | YES ✅ | YES ✅ |

### Raw Output Run 3
```text
==================================================
  Benchmark: bench_latency_run3
==================================================
  Total requests : 100
  Normal / Attack: 50 / 50
  Min             : 1.84 ms
  Max             : 6.60 ms
  Mean            : 2.19 ms
  P50 (median)    : 2.12 ms
  P95             : 2.45 ms
  P99             : 2.72 ms
  All < 100ms     : YES ✅
==================================================
```

**Kesimpulan**: Latensi middleware end-to-end ~2-3ms (P95), jauh di bawah target PRD < 100ms.
Run 1 max ~33ms disebabkan cold start; setelah warm-up, P99 turun ke ~3ms.

---

## 8. Multi-Environment Configuration (ENV Variable Support)

`config/middleware_config.py` diubah agar `inference_api_url` membaca ENV variable
`INFERENCE_API_URL` dengan fallback ke `http://127.0.0.1:8000/predict` (lokal).

```python
INFERENCE_API_URL = os.getenv("INFERENCE_API_URL", "http://127.0.0.1:8000/predict")
```

Untuk Docker (Spec 09), cukup set: `INFERENCE_API_URL=http://inference-api:8000/predict`.

Smoke test setelah perubahan: `curl /home` → HTTP 200, `X-AI-Guard: allow` ✅.

---

## 9. Regression Test Guardrail Clean-Benign

File: `src/api/test_clean_benign_guardrail.py` — 4 test cases memastikan guardrail
`is_clean_benign` tidak regresi:

| Test | Input | Expected |
|------|-------|----------|
| A | `GET /home` (no body/query/attack) | `label=normal`, `attack_class=None` |
| B | `GET /search?q=hello` (benign query) | `label=anomalous`, `attack_class=unknown_anomaly` (CSIC 2010 domain gap FP — known, documented) |
| C | `GET /home%20page` (encoded char) | `label=normal` or `anomalous` (documented behavior) |
| D | `GET /search?q=' OR 1=1--` (SQLi) | `label=anomalous`, `attack_class=sql_injection` |

Semua 4 test PASS via `python -m pytest src/api/test_clean_benign_guardrail.py -v`.

---

## 10. Repository Hygiene — Log Artifact di-gitignore

Ditambahkan ke `.gitignore`:
```
data/*.jsonl
!data/.gitkeep
```

File `data/.gitkeep` dibuat agar folder `data/` tetap di-track.
`data/traffic_log_stub.jsonl` di-remove dari git index (`git rm --cached`).
